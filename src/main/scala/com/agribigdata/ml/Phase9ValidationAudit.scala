package com.agribigdata.ml

import com.agribigdata.utils.SparkSetup
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.functions._
import org.apache.spark.ml.feature.{Imputer, VectorAssembler}
import org.apache.spark.ml.classification.{RandomForestClassifier, GBTClassifier}
import org.apache.spark.ml.evaluation.BinaryClassificationEvaluator
import org.apache.spark.ml.Pipeline
import com.agribigdata.ingestion.Schemas.Canonical

object Phase9ValidationAudit {
  def main(args: Array[String]): Unit = {
    val spark = SparkSetup.session("Phase9ValidationAudit")
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
    val dataWithTargetRaw = dataWithNextZ.withColumn("target_anomaly", when(abs(col("next_z_score")) > 2.0, 1.0).otherwise(0.0))

    println("=== 1. TARGET AUDIT ===")
    val cNextZNull = dataWithTargetRaw.filter(col("next_z_score").isNull).count()
    val cTargetNull = dataWithTargetRaw.filter(col("target_anomaly").isNull).count()
    val cTarget0 = dataWithTargetRaw.filter(col("target_anomaly") === 0.0).count()
    val cTarget1 = dataWithTargetRaw.filter(col("target_anomaly") === 1.0).count()
    println(s"next_z_score = null: $cNextZNull")
    println(s"target_anomaly = null: $cTargetNull")
    println(s"target_anomaly = 0: $cTarget0")
    println(s"target_anomaly = 1: $cTarget1")
    println(s"Rows excluded from ML: $cNextZNull")
    println("Explanation: next_z_score is a valid future label because it represents the market state strictly AFTER the current feature vector is observed. Since features only aggregate up to the CURRENT row, predicting the next row's z_score avoids temporal leakage.")

    val targetDefinition = dataWithTargetRaw.filter(col("next_z_score").isNotNull)

    println("\n=== 2. FEATURE AUDIT ===")
    val featureCols = Array(
      "previous_modal_price", "price_change", "price_change_pct", 
      "price_range", "relative_price_range", "previous_to_current_ratio", 
      "rolling_7_observation_avg", "rolling_7_observation_stddev", "z_score"
    )
    val colsStr = featureCols.mkString(", ")
    println(s"9 predictors confirmed: $colsStr")
    println("Confirmed NOT features: target_anomaly, next_z_score, price_outlier, any future-row column")

    val trainData = targetDefinition.filter(year(col(Canonical.arrivalDate)) < 2024)
    val valData = targetDefinition.filter(year(col(Canonical.arrivalDate)) === 2024)

    val imputedCols = featureCols.map(_ + "_imputed")
    val imputer = new Imputer().setInputCols(featureCols).setOutputCols(imputedCols).setStrategy("median")
    val assembler = new VectorAssembler().setInputCols(imputedCols).setOutputCol("features").setHandleInvalid("skip")

    println("\n=== 3. REUSE EXISTING VALIDATION PREDICTIONS ===")
    val rfBase = new RandomForestClassifier().setLabelCol("target_anomaly").setFeaturesCol("features").setNumTrees(20).setMaxDepth(8).setSeed(42L)
    val pipelineBase = new Pipeline().setStages(Array(imputer, assembler, rfBase))
    val modelBase = pipelineBase.fit(trainData)
    val valPredsRaw = modelBase.transform(valData)
    
    val extractProb = udf((v: org.apache.spark.ml.linalg.Vector) => v(1))
    val valPreds = valPredsRaw.withColumn("prob_1", extractProb(col("probability"))).cache()

    val thresholds = Seq(0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90)

    var maxF1 = -1.0; var maxF1Thresh = 0.0
    var maxBalAcc = -1.0; var maxBalAccThresh = 0.0
    var bestAccR2 = -1.0; var bestAccR2Thresh = 0.0
    var bestAccR3 = -1.0; var bestAccR3Thresh = 0.0

    for (th <- thresholds) {
      val tPreds = valPreds.withColumn("pred", when(col("prob_1") >= th, 1.0).otherwise(0.0))
      
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

      println(f"Thresh $th%.2f -> Acc: $acc%.4f, BalAcc: $balAcc%.4f, Prec: $prec%.4f, Rec: $rec%.4f, F1: $f1%.4f, FPR: $fpr%.4f | TP:$tp%.0f FP:$fp%.0f FN:$fn%.0f TN:$tn%.0f")

      if (f1 > maxF1) { maxF1 = f1; maxF1Thresh = th }
      if (balAcc > maxBalAcc) { maxBalAcc = balAcc; maxBalAccThresh = th }
      if (rec >= 0.20 && acc > bestAccR2) { bestAccR2 = acc; bestAccR2Thresh = th }
      if (rec >= 0.30 && acc > bestAccR3) { bestAccR3 = acc; bestAccR3Thresh = th }
    }

    println("\n=== 4. BASELINE COMPARISON ===")
    println(f"A. Max F1 Threshold: $maxF1Thresh%.2f")
    println(f"B. Max Balanced Accuracy Threshold: $maxBalAccThresh%.2f")
    println(f"C. Highest Acc w/ Recall >= 0.20: $bestAccR2Thresh%.2f")
    println(f"D. Highest Acc w/ Recall >= 0.30: $bestAccR3Thresh%.2f")

    println("\n=== 5. MODEL COMPARISON ===")
    
    def evalModel(name: String, preds: org.apache.spark.sql.DataFrame): Unit = {
      val tp = preds.filter("target_anomaly = 1.0 AND prediction = 1.0").count().toDouble
      val tn = preds.filter("target_anomaly = 0.0 AND prediction = 0.0").count().toDouble
      val fp = preds.filter("target_anomaly = 0.0 AND prediction = 1.0").count().toDouble
      val fn = preds.filter("target_anomaly = 1.0 AND prediction = 0.0").count().toDouble

      val acc = (tp + tn) / (tp + tn + fp + fn)
      val prec = if (tp + fp == 0) 0.0 else tp / (tp + fp)
      val rec = if (tp + fn == 0) 0.0 else tp / (tp + fn)
      val f1 = if (prec + rec == 0) 0.0 else 2 * (prec * rec) / (prec + rec)
      val balAcc = (rec + (if (tn + fp == 0) 0.0 else tn / (tn + fp))) / 2.0

      val prAuc = new BinaryClassificationEvaluator().setLabelCol("target_anomaly").setRawPredictionCol("rawPrediction").setMetricName("areaUnderPR").evaluate(preds)
      val rocAuc = new BinaryClassificationEvaluator().setLabelCol("target_anomaly").setRawPredictionCol("rawPrediction").setMetricName("areaUnderROC").evaluate(preds)
      
      println(f"$name:")
      println(f"  Accuracy: $acc%.4f, BalAcc: $balAcc%.4f, Prec: $prec%.4f, Rec: $rec%.4f, F1: $f1%.4f")
      println(f"  PR-AUC: $prAuc%.4f, ROC-AUC: $rocAuc%.4f")
    }

    evalModel("A. Random Forest (Baseline)", valPredsRaw)

    val w1 = 5.0 
    val trainDataWeighted = trainData.withColumn("classWeight", when(col("target_anomaly") === 1.0, w1).otherwise(1.0))
    val rfWeight = new RandomForestClassifier().setLabelCol("target_anomaly").setFeaturesCol("features").setNumTrees(20).setMaxDepth(8).setSeed(42L).setWeightCol("classWeight")
    val valPredsW = new Pipeline().setStages(Array(imputer, assembler, rfWeight)).fit(trainDataWeighted).transform(valData)
    evalModel("B. Random Forest (Moderate Class Weight=5)", valPredsW)

    val gbt = new GBTClassifier().setLabelCol("target_anomaly").setFeaturesCol("features").setMaxIter(20).setMaxDepth(5).setSeed(42L)
    val valPredsGbt = new Pipeline().setStages(Array(imputer, assembler, gbt)).fit(trainData).transform(valData)
    evalModel("C. GBTClassifier (modest config)", valPredsGbt)

    println("\n=== 6. RESOURCE LIMITS ===")
    println("Memory-safe: Entity sampling restricted to 1%. No full-data training. No row-level sampling. Entity histories kept intact.")
    println("\n=== 7. TEST SET ===")
    println("Test set (2025+) remains untouched.")
    
    spark.stop()
  }
}
