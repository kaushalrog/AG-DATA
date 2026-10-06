package com.agribigdata.ml

import com.agribigdata.utils.SparkSetup
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.functions._
import org.apache.spark.ml.feature.{Imputer, VectorAssembler}
import org.apache.spark.ml.classification.{RandomForestClassifier, GBTClassifier}
import org.apache.spark.ml.evaluation.BinaryClassificationEvaluator
import org.apache.spark.ml.Pipeline
import com.agribigdata.ingestion.Schemas.Canonical

object Phase9FinalComparison {
  def main(args: Array[String]): Unit = {
    val spark = SparkSetup.session("Phase9FinalComparison")
    spark.sparkContext.setLogLevel("WARN")
    import spark.implicits._

    val inputPath = sys.env.getOrElse("AGRI_INPUT_PATH", "data/features/engineered")
    val fullData = spark.read.parquet(inputPath)

    val entityCols = Seq(Canonical.state, Canonical.district, Canonical.market, Canonical.commodity, Canonical.variety)
    val allEntities = fullData.select(entityCols.map(col): _*).distinct()
    val sampledEntities = allEntities.sample(withReplacement = false, fraction = 0.01, seed = 42L)
    val data = fullData.join(sampledEntities, entityCols, "inner")

    val wEntity = Window.partitionBy(entityCols.map(col): _*).orderBy(Canonical.arrivalDate)
    val dataWithNextZ = data.withColumn("next_z_score", lead(col("z_score"), 1).over(wEntity))
    val targetDefinition = dataWithNextZ.withColumn("target_anomaly", when(abs(col("next_z_score")) > 2.0, 1.0).otherwise(0.0))
      .filter(col("next_z_score").isNotNull)

    val trainData = targetDefinition.filter(year(col(Canonical.arrivalDate)) < 2024)
    val valData = targetDefinition.filter(year(col(Canonical.arrivalDate)) === 2024)
    val testData = targetDefinition.filter(year(col(Canonical.arrivalDate)) >= 2025)

    println("=== 1. PREVALENCE REPORT ===")
    def printPrev(name: String, df: org.apache.spark.sql.DataFrame): Unit = {
      val total = df.count().toDouble
      val anom = df.filter(col("target_anomaly") === 1.0).count().toDouble
      val norm = total - anom
      val pct = if (total == 0) 0.0 else (anom / total) * 100.0
      println(f"$name%-10s | Total: $total%.0f, Normal: $norm%.0f, Anomaly: $anom%.0f | Prevalence: $pct%.2f%%")
    }
    
    printPrev("TRAIN", trainData)
    printPrev("VALIDATION", valData)
    printPrev("TEST", testData)
    printPrev("OVERALL", targetDefinition)

    println("\n=== 2. MODEL TRAINING & THRESHOLD SWEEP (VALIDATION SET ONLY) ===")
    
    val featureCols = Array(
      "previous_modal_price", "price_change", "price_change_pct", 
      "price_range", "relative_price_range", "previous_to_current_ratio", 
      "rolling_7_observation_avg", "rolling_7_observation_stddev", "z_score"
    )
    val imputedCols = featureCols.map(_ + "_imputed")
    val imputer = new Imputer().setInputCols(featureCols).setOutputCols(imputedCols).setStrategy("median")
    val assembler = new VectorAssembler().setInputCols(imputedCols).setOutputCol("features").setHandleInvalid("skip")

    // A. RF Baseline
    val rfBase = new RandomForestClassifier().setLabelCol("target_anomaly").setFeaturesCol("features").setNumTrees(20).setMaxDepth(8).setSeed(42L)
    val modelA = new Pipeline().setStages(Array(imputer, assembler, rfBase)).fit(trainData)
    
    // B. RF Class Weight
    val w1 = 5.0
    val trainDataWeighted = trainData.withColumn("classWeight", when(col("target_anomaly") === 1.0, w1).otherwise(1.0))
    val rfWeight = new RandomForestClassifier().setLabelCol("target_anomaly").setFeaturesCol("features").setNumTrees(20).setMaxDepth(8).setSeed(42L).setWeightCol("classWeight")
    val modelB = new Pipeline().setStages(Array(imputer, assembler, rfWeight)).fit(trainDataWeighted)

    // C. GBT
    val gbt = new GBTClassifier().setLabelCol("target_anomaly").setFeaturesCol("features").setMaxIter(20).setMaxDepth(5).setSeed(42L)
    val modelC = new Pipeline().setStages(Array(imputer, assembler, gbt)).fit(trainData)

    val extractProb = udf((v: org.apache.spark.ml.linalg.Vector) => v(1))
    
    val predsA_raw = modelA.transform(valData).cache()
    val predsB_raw = modelB.transform(valData).cache()
    val predsC_raw = modelC.transform(valData).cache()

    val predsA = predsA_raw.withColumn("prob_1", extractProb(col("probability")))
    val predsB = predsB_raw.withColumn("prob_1", extractProb(col("probability")))
    val predsC = predsC_raw.withColumn("prob_1", extractProb(col("probability")))

    val thresholds = Seq(0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70)

    case class ThresholdMetrics(modelName: String, threshold: Double, acc: Double, balAcc: Double, prec: Double, rec: Double, f1: Double, fpr: Double, tp: Double, fp: Double, fn: Double, tn: Double, prAuc: Double, rocAuc: Double)

    def evaluateSweep(name: String, predsRaw: org.apache.spark.sql.DataFrame, preds: org.apache.spark.sql.DataFrame): Seq[ThresholdMetrics] = {
      println(s"\n--- $name ---")
      val prAuc = new BinaryClassificationEvaluator().setLabelCol("target_anomaly").setRawPredictionCol("rawPrediction").setMetricName("areaUnderPR").evaluate(predsRaw)
      val rocAuc = new BinaryClassificationEvaluator().setLabelCol("target_anomaly").setRawPredictionCol("rawPrediction").setMetricName("areaUnderROC").evaluate(predsRaw)
      println(f"Overall PR-AUC: $prAuc%.4f, ROC-AUC: $rocAuc%.4f")
      
      var metricsList = Seq[ThresholdMetrics]()
      
      for (th <- thresholds) {
        val tPreds = preds.withColumn("pred", when(col("prob_1") >= th, 1.0).otherwise(0.0))
        val tp = tPreds.filter("target_anomaly = 1.0 AND pred = 1.0").count().toDouble
        val tn = tPreds.filter("target_anomaly = 0.0 AND pred = 0.0").count().toDouble
        val fp = tPreds.filter("target_anomaly = 0.0 AND pred = 1.0").count().toDouble
        val fn = tPreds.filter("target_anomaly = 1.0 AND pred = 0.0").count().toDouble

        val acc = (tp + tn) / (tp + tn + fp + fn)
        val prec = if (tp + fp == 0) 0.0 else tp / (tp + fp)
        val rec = if (tp + fn == 0) 0.0 else tp / (tp + fn)
        val f1 = if (prec + rec == 0) 0.0 else 2 * (prec * rec) / (prec + rec)
        val fpr = if (tn + fp == 0) 0.0 else fp / (tn + fp)
        val balAcc = (rec + (if (tn + fp == 0) 0.0 else tn / (tn + fp))) / 2.0

        println(f"Thresh $th%.2f | Acc: $acc%.4f, BalAcc: $balAcc%.4f, Prec: $prec%.4f, Rec: $rec%.4f, F1: $f1%.4f, FPR: $fpr%.4f | TP:$tp%.0f FP:$fp%.0f FN:$fn%.0f TN:$tn%.0f")
        metricsList = metricsList :+ ThresholdMetrics(name, th, acc, balAcc, prec, rec, f1, fpr, tp, fp, fn, tn, prAuc, rocAuc)
      }
      
      val bestF1 = metricsList.maxBy(_.f1)
      val bestBalAcc = metricsList.maxBy(_.balAcc)
      val validR2 = metricsList.filter(_.rec >= 0.20)
      val bestAccR2 = if (validR2.nonEmpty) validR2.maxBy(_.acc) else metricsList.head
      val validR3 = metricsList.filter(_.rec >= 0.30)
      val bestAccR3 = if (validR3.nonEmpty) validR3.maxBy(_.acc) else metricsList.head
      
      println(f"  A. Max F1: Threshold ${bestF1.threshold}%.2f (F1: ${bestF1.f1}%.4f)")
      println(f"  B. Max BalAcc: Threshold ${bestBalAcc.threshold}%.2f (BalAcc: ${bestBalAcc.balAcc}%.4f)")
      println(f"  C. Highest Acc w/ Rec>=0.2: Threshold ${bestAccR2.threshold}%.2f (Acc: ${bestAccR2.acc}%.4f)")
      println(f"  D. Highest Acc w/ Rec>=0.3: Threshold ${bestAccR3.threshold}%.2f (Acc: ${bestAccR3.acc}%.4f)")
      
      metricsList
    }

    val metricsA = evaluateSweep("A. RandomForest Baseline", predsA_raw, predsA)
    val metricsB = evaluateSweep("B. RandomForest (Class Weight=5)", predsB_raw, predsB)
    val metricsC = evaluateSweep("C. GBTClassifier", predsC_raw, predsC)

    spark.stop()
  }
}
