package com.agribigdata.ml

import org.apache.spark.ml.Pipeline
import org.apache.spark.ml.classification.{RandomForestClassifier, GBTClassifier, RandomForestClassificationModel}
import org.apache.spark.ml.evaluation.{BinaryClassificationEvaluator, MulticlassClassificationEvaluator}
import org.apache.spark.ml.feature.{Imputer, VectorAssembler, StringIndexer, OneHotEncoder}
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types.DoubleType
import scala.collection.mutable.ArrayBuffer

object ModelTuning {
  def main(args: Array[String]): Unit = {
    val spark = SparkSession.builder()
      .appName("Agricultural Market ML - Comprehensive Model Tuning")
      .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    val inputPath = "hdfs://namenode:9000/agri-market/analytics/features"
    val predictionsOutputPath = "hdfs://namenode:9000/agri-market/analytics/anomaly_predictions"
    val modelOutputPath = "hdfs://namenode:9000/agri-market/models/anomaly_prediction_rf"

    println("=" * 70)
    println("COMPREHENSIVE MODEL TUNING & EVALUATION")
    println("=" * 70)

    val df = spark.read.parquet(inputPath)

    // 1. Sampling Stats
    println("\n[1] Evaluating Entity-Safe Temporal Sampling Fractions...")
    val fractions = Seq(0.001, 0.005, 0.010)
    for (f <- fractions) {
      val modVal = (f * 1000).toInt
      val sample = df.filter(abs(hash(col("state"), col("district"), col("commodity"), col("market"), col("variety"))) % 1000 < modVal)
      val entities = sample.select("state", "district", "commodity", "market", "variety").distinct().count()
      val records = sample.count()
      val pos = sample.filter(col("price_outlier") === true).count()
      val rate = if (records > 0) (pos.toDouble / records) * 100 else 0.0
      println(f"Fraction: $f%.3f | Entities: $entities%5d | Records: $records%8d | Positive Rate: $rate%.2f%%")
    }

    // Use 1.0% for experiment (modVal = 10)
    val chosenFraction = 0.010
    println(s"\n=> Proceeding with chosen sampling fraction: $chosenFraction")
    val sampledDf = df.filter(abs(hash(col("state"), col("district"), col("commodity"), col("market"), col("variety"))) % 1000 < 10).cache()

    // 2. Target and Feature Engineering
    println("\n[2] Engineering Target and New Features...")
    val windowSpec = Window.partitionBy("state", "district", "commodity", "market", "variety").orderBy("arrival_date")

    var enrichedDf = sampledDf
      .withColumn("next_price_outlier", lead("price_outlier", 1).over(windowSpec))
      .withColumn("label", col("next_price_outlier").cast(DoubleType))
      .filter(col("label").isNotNull)
      
    enrichedDf = enrichedDf
      .withColumn("price_range", col("max_price") - col("min_price"))
      .withColumn("relative_price_range", 
        when(col("modal_price") > 0, (col("max_price") - col("min_price")) / col("modal_price")).otherwise(0.0))
      .withColumn("previous_to_current_ratio", 
        when(col("previous_modal_price") > 0, col("modal_price") / col("previous_modal_price")).otherwise(1.0))

    // 3. Train / Validation / Test Split
    println("\n[3] Temporal Split (Train < 2024, Val == 2024, Test >= 2025)...")
    val trainRaw = enrichedDf.filter(col("year") < 2024).cache()
    val valRaw = enrichedDf.filter(col("year") === 2024).cache()
    val testRaw = enrichedDf.filter(col("year") >= 2025).cache()

    println(s"Train Rows: ${trainRaw.count()} | Val Rows: ${valRaw.count()} | Test Rows: ${testRaw.count()}")

    // 4. (Categoricals Skipped: Single-cardinality in sample causes OHE failure)
    println("\n[4] Skipping Categorical Encoders (preventing low-cardinality sample crash)...")

    // 5. Imputation & Vector Assembler
    val numericCols = Array(
      "previous_modal_price", "price_change", "price_change_pct", 
      "rolling_7_observation_avg", "rolling_7_observation_stddev", 
      "min_price", "max_price", "modal_price",
      "price_range", "relative_price_range", "previous_to_current_ratio"
    )
    val imputedCols = numericCols.map(_ + "_imp")

    val imputer = new Imputer().setInputCols(numericCols).setOutputCols(imputedCols).setStrategy("median")
    val assembler = new VectorAssembler()
      .setInputCols(imputedCols) // Removed categorical vectors
      .setOutputCol("features")

    // 6. Class Weighting Strategies
    val trainCount = trainRaw.count()
    val posCount = trainRaw.filter(col("label") === 1.0).count()
    val negCount = trainCount - posCount
    
    val invFreqW0 = trainCount.toDouble / (2.0 * negCount)
    val invFreqW1 = trainCount.toDouble / (2.0 * posCount)
    val sqrtInvFreqW1 = math.sqrt(invFreqW1 / invFreqW0)

    val trainData = trainRaw
      .withColumn("weight_none", lit(1.0))
      .withColumn("weight_inv_freq", when(col("label") === 0.0, lit(invFreqW0)).otherwise(lit(invFreqW1)))
      .withColumn("weight_sqrt", when(col("label") === 0.0, lit(1.0)).otherwise(lit(sqrtInvFreqW1)))
      .cache()
      
    // Set valEncoded and testEncoded to raw since we skip StringIndexer
    val valEncoded = valRaw
    val testEncoded = testRaw

    // 7. Grid Search
    println("\n[5] Executing Model & Threshold Grid Search on Validation Set...")
    
    case class Config(modelType: String, trees: Int, depth: Int, weightCol: String, threshold: Double)
    case class Result(config: Config, precision: Double, recall: Double, f1: Double, prAuc: Double, tp: Long, fp: Long, fn: Long, tn: Long)

    val results = ArrayBuffer[Result]()
    val weights = Seq("weight_none", "weight_sqrt", "weight_inv_freq")
    val thresholds = Seq(0.10, 0.20, 0.30, 0.40, 0.50, 0.60)

    val rfConfigs = for { w <- weights; t <- Seq(50, 100); d <- Seq(6, 8) } yield ("RF", w, t, d)
    val gbtConfigs = for { w <- weights } yield ("GBT", w, 30, 4)

    val allConfigs = rfConfigs ++ gbtConfigs

    val extractProb = udf((v: org.apache.spark.ml.linalg.Vector) => v(1))

    for ((mType, wCol, t, d) <- allConfigs) {
      val classifier = if (mType == "RF") {
        new RandomForestClassifier().setLabelCol("label").setFeaturesCol("features").setWeightCol(wCol).setNumTrees(t).setMaxDepth(d).setSeed(42L)
      } else {
        new GBTClassifier().setLabelCol("label").setFeaturesCol("features").setWeightCol(wCol).setMaxIter(t).setMaxDepth(d).setSeed(42L)
      }

      val pipeline = new Pipeline().setStages(Array(imputer, assembler, classifier))
      val model = pipeline.fit(trainData)
      val rawValPreds = model.transform(valEncoded).cache()

      val binaryEval = new BinaryClassificationEvaluator().setLabelCol("label").setRawPredictionCol("rawPrediction").setMetricName("areaUnderPR")
      val prAuc = binaryEval.evaluate(rawValPreds)

      for (thresh <- thresholds) {
        val withThresh = rawValPreds.withColumn("pred_tuned", when(extractProb(col("probability")) >= thresh, 1.0).otherwise(0.0))
        
        val tp = withThresh.filter(col("label") === 1.0 && col("pred_tuned") === 1.0).count()
        val fp = withThresh.filter(col("label") === 0.0 && col("pred_tuned") === 1.0).count()
        val fn = withThresh.filter(col("label") === 1.0 && col("pred_tuned") === 0.0).count()
        val tn = withThresh.filter(col("label") === 0.0 && col("pred_tuned") === 0.0).count()

        val precision = if (tp + fp > 0) tp.toDouble / (tp + fp) else 0.0
        val recall = if (tp + fn > 0) tp.toDouble / (tp + fn) else 0.0
        val f1 = if (precision + recall > 0) 2 * (precision * recall) / (precision + recall) else 0.0

        results += Result(Config(mType, t, d, wCol, thresh), precision, recall, f1, prAuc, tp, fp, fn, tn)
      }
      rawValPreds.unpersist()
    }

    val bestResult = results.maxBy(r => (r.f1, r.recall))
    println("\n=== TOP 5 CONFIGURATIONS ON VALIDATION ===")
    results.sortBy(r => (-r.f1, -r.recall)).take(5).foreach { r =>
      println(f"${r.config.modelType} | w:${r.config.weightCol}%15s | t:${r.config.trees}%3d | d:${r.config.depth}%2d | th:${r.config.threshold}%.2f => F1: ${r.f1}%.4f | Rec: ${r.recall}%.4f | Prec: ${r.precision}%.4f")
    }

    println(s"\n[6] SELECTED BEST CONFIGURATION:")
    println(bestResult.config)

    // 8. Final Evaluation on Untouched Test Set
    println("\n[7] FINAL EVALUATION ON UNTOUCHED TEST SET (>= 2025)...")
    
    val bestClassifier = if (bestResult.config.modelType == "RF") {
      new RandomForestClassifier().setLabelCol("label").setFeaturesCol("features").setWeightCol(bestResult.config.weightCol)
        .setNumTrees(bestResult.config.trees).setMaxDepth(bestResult.config.depth).setSeed(42L)
    } else {
      new GBTClassifier().setLabelCol("label").setFeaturesCol("features").setWeightCol(bestResult.config.weightCol)
        .setMaxIter(bestResult.config.trees).setMaxDepth(bestResult.config.depth).setSeed(42L)
    }

    val finalPipeline = new Pipeline().setStages(Array(imputer, assembler, bestClassifier))
    val finalModel = finalPipeline.fit(trainData)
    
    val testRawPreds = finalModel.transform(testEncoded)
    val testFinal = testRawPreds.withColumn("prediction", when(extractProb(col("probability")) >= bestResult.config.threshold, 1.0).otherwise(0.0)).cache()

    val tp = testFinal.filter(col("label") === 1.0 && col("prediction") === 1.0).count()
    val fp = testFinal.filter(col("label") === 0.0 && col("prediction") === 1.0).count()
    val fn = testFinal.filter(col("label") === 1.0 && col("prediction") === 0.0).count()
    val tn = testFinal.filter(col("label") === 0.0 && col("prediction") === 0.0).count()

    val precision = if (tp + fp > 0) tp.toDouble / (tp + fp) else 0.0
    val recall = if (tp + fn > 0) tp.toDouble / (tp + fn) else 0.0
    val f1 = if (precision + recall > 0) 2 * (precision * recall) / (precision + recall) else 0.0
    val accuracy = (tp + tn).toDouble / (tp + tn + fp + fn)
    
    val tpr = recall
    val tnr = if (tn + fp > 0) tn.toDouble / (tn + fp) else 0.0
    val balancedAccuracy = (tpr + tnr) / 2.0
    
    val binaryEval = new BinaryClassificationEvaluator().setLabelCol("label").setRawPredictionCol("rawPrediction")
    val prAuc = binaryEval.setMetricName("areaUnderPR").evaluate(testFinal)
    val rocAuc = binaryEval.setMetricName("areaUnderROC").evaluate(testFinal)

    println("\n=== FINAL TEST METRICS ===")
    println(f"Accuracy:           ${accuracy * 100}%.2f%%")
    println(f"Positive Precision: $precision%.4f")
    println(f"Positive Recall:    $recall%.4f")
    println(f"Positive F1:        $f1%.4f")
    println(f"Balanced Accuracy:  $balancedAccuracy%.4f")
    println(f"PR-AUC:             $prAuc%.4f")
    println(f"ROC-AUC:            $rocAuc%.4f")
    println("\nConfusion Matrix:")
    println(f"TP: $tp%5d | FP: $fp%5d")
    println(f"FN: $fn%5d | TN: $tn%5d")

    val baselineAcc = (tn + fp).toDouble / (tp + tn + fp + fn)
    println(f"\nTrivial Baseline Accuracy: ${baselineAcc * 100}%.2f%%")

    if (bestResult.config.modelType == "RF") {
      println("\nFeature Importances:")
      val rfModel = finalModel.stages.last.asInstanceOf[RandomForestClassificationModel]
      val importances = rfModel.featureImportances.toArray
      importances.zipWithIndex.sortBy(-_._1).take(10).foreach { case (imp, idx) =>
         val name = if(idx < imputedCols.length) imputedCols(idx) else s"Cat_Feat_$idx"
         println(f"$name%-30s : $imp%.4f")
      }
    }

    println("\n[8] Saving final model and predictions...")
    testFinal.write.mode("overwrite").parquet(predictionsOutputPath)
    finalModel.write.overwrite().save(modelOutputPath)

    println("\nDONE.")
    spark.stop()
  }
}
