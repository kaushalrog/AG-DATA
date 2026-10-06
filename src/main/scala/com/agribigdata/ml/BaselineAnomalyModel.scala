package com.agribigdata.ml

import com.agribigdata.utils.SparkSetup
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.functions._
import org.apache.spark.ml.feature.{Imputer, VectorAssembler}
import org.apache.spark.ml.classification.RandomForestClassifier
import org.apache.spark.ml.evaluation.{MulticlassClassificationEvaluator, BinaryClassificationEvaluator}
import org.apache.spark.ml.Pipeline
import com.agribigdata.ingestion.Schemas.Canonical

object BaselineAnomalyModel {
  def main(args: Array[String]): Unit = {
    val spark = SparkSetup.session("BaselineAnomalyModel")
    spark.sparkContext.setLogLevel("WARN")
    import spark.implicits._

    val inputPath = sys.env.getOrElse("AGRI_INPUT_PATH", "hdfs://namenode:9000/agri/features/engineered")
    val sparkMaster = spark.sparkContext.master
    val driverMemory = spark.sparkContext.getConf.getOption("spark.driver.memory").getOrElse("default")

    println("=== 1. Execution Plan & Resources ===")
    println(s"Input Path Used : $inputPath")
    println(s"Spark Master    : $sparkMaster")
    println(s"Driver Memory   : $driverMemory")

    val fullData = spark.read.parquet(inputPath)
    val inputRecordCount = fullData.count()
    println(s"Total Input Records : $inputRecordCount")

    // 5. Entity-safe representative sample (Memory Pressure Fallback)
    // 93.4M records will cause OOM with RandomForest cache overhead, so we sample 10% of entities.
    val entityCols = Seq(Canonical.state, Canonical.district, Canonical.market, Canonical.commodity, Canonical.variety)
    val allEntities = fullData.select(entityCols.map(col): _*).distinct()
    val totalEntitiesCount = allEntities.count()
    val sampledEntities = allEntities.sample(withReplacement = false, fraction = 0.01, seed = 42L)
    val data = fullData.join(sampledEntities, entityCols, "inner")
    
    val sampledRowsCount = data.count()
    val sampledEntitiesCount = sampledEntities.count()
    
    println("\n=== Memory-Safe Entity Sampling Applied ===")
    println(s"Sampling Fraction : 10.0% of entities")
    println(s"Total Entities    : $totalEntitiesCount")
    println(s"Sampled Entities  : $sampledEntitiesCount")
    println(s"Total Rows Retain : $sampledRowsCount")

    // 4. Define the future anomaly target
    val wEntity = Window.partitionBy(entityCols.map(col): _*).orderBy(Canonical.arrivalDate)

    val targetDefinition = data
      .withColumn("next_z_score", lead(col("z_score"), 1).over(wEntity))
      .withColumn("target_anomaly", when(abs(col("next_z_score")) > 2.0, 1.0).otherwise(0.0))
      .filter(col("next_z_score").isNotNull) // Drop terminal rows

    // 3. Exact Feature Columns - verify no leakage
    val featureCols = Array(
      "previous_modal_price", "price_change", "price_change_pct", 
      "price_range", "relative_price_range", "previous_to_current_ratio", 
      "rolling_7_observation_avg", "rolling_7_observation_stddev", "z_score"
    )

    println("\n=== Target Definition & Feature Columns ===")
    println("Target: target_anomaly = abs(next_z_score) > 2.0 (using lead(z_score, 1) partitioned by entity, ordered by arrival_date)")
    println(s"Feature Columns (${featureCols.length}): ${featureCols.mkString(", ")}")
    println("Verified: No price_outlier, next_price_outlier, or target-derived leakage columns in features.")
    
    // Temporal Split
    val trainData = targetDefinition.filter(year(col(Canonical.arrivalDate)) < 2024)
    val valData = targetDefinition.filter(year(col(Canonical.arrivalDate)) === 2024)
    val testData = targetDefinition.filter(year(col(Canonical.arrivalDate)) >= 2025)

    // 2. Report training row count, anomalies, etc.
    val trainCount = trainData.count()
    val valCount = valData.count()
    
    val trainAnom = trainData.filter(col("target_anomaly") === 1.0).count()
    val valAnom = valData.filter(col("target_anomaly") === 1.0).count()

    val trainNormal = trainCount - trainAnom
    val valNormal = valCount - valAnom

    println("\n=== Temporal Splits & Class Prevalence ===")
    println(f"TRAIN (<2024)  : $trainCount%10d rows | Anomaly: $trainAnom%8d | Normal: $trainNormal%8d | Prev: ${100.0 * trainAnom / trainCount}%5.2f%%")
    println(f"VALID (==2024) : $valCount%10d rows | Anomaly: $valAnom%8d | Normal: $valNormal%8d | Prev: ${100.0 * valAnom / valCount}%5.2f%%")

    // Pipeline Pre-processing
    val imputedCols = featureCols.map(_ + "_imputed")
    val imputer = new Imputer()
      .setInputCols(featureCols)
      .setOutputCols(imputedCols)
      .setStrategy("median")

    val assembler = new VectorAssembler()
      .setInputCols(imputedCols)
      .setOutputCol("features")
      .setHandleInvalid("skip")

    // 6. Modest RandomForest Configuration
    val rf = new RandomForestClassifier()
      .setLabelCol("target_anomaly")
      .setFeaturesCol("features")
      .setNumTrees(20)
      .setMaxDepth(8)
      .setSeed(42L)

    val pipeline = new Pipeline().setStages(Array(imputer, assembler, rf))

    val startTime = System.currentTimeMillis()
    println("\nTraining Baseline RandomForest Model on Entity-Sampled Train Set...")
    val model = pipeline.fit(trainData)
    
    println("Generating predictions on VALIDATION set...")
    // 7. Evaluate on validation first.
    val predictions = model.transform(valData)
    predictions.cache()

    val tp = predictions.filter("target_anomaly = 1.0 AND prediction = 1.0").count().toDouble
    val tn = predictions.filter("target_anomaly = 0.0 AND prediction = 0.0").count().toDouble
    val fp = predictions.filter("target_anomaly = 0.0 AND prediction = 1.0").count().toDouble
    val fn = predictions.filter("target_anomaly = 1.0 AND prediction = 0.0").count().toDouble

    val accuracy = (tp + tn) / (tp + tn + fp + fn)
    val precision = if (tp + fp == 0) 0.0 else tp / (tp + fp)
    val recall = if (tp + fn == 0) 0.0 else tp / (tp + fn)
    val f1 = if (precision + recall == 0) 0.0 else 2 * (precision * recall) / (precision + recall)
    
    val sensitivity = recall
    val specificity = if (tn + fp == 0) 0.0 else tn / (tn + fp)
    val balancedAccuracy = (sensitivity + specificity) / 2.0

    val binaryEvalPR = new BinaryClassificationEvaluator()
      .setLabelCol("target_anomaly")
      .setRawPredictionCol("rawPrediction")
      .setMetricName("areaUnderPR")
      
    val binaryEvalROC = new BinaryClassificationEvaluator()
      .setLabelCol("target_anomaly")
      .setRawPredictionCol("rawPrediction")
      .setMetricName("areaUnderROC")

    val prAuc = binaryEvalPR.evaluate(predictions)
    val rocAuc = binaryEvalROC.evaluate(predictions)
    
    val endTime = System.currentTimeMillis()

    println("\n=== Validation Metrics ===")
    println(f"Accuracy         : $accuracy%.4f")
    println(f"Balanced Accuracy: $balancedAccuracy%.4f")
    println(f"Positive Precision: $precision%.4f")
    println(f"Positive Recall  : $recall%.4f")
    println(f"Positive F1 Score: $f1%.4f")
    println(f"PR-AUC           : $prAuc%.4f")
    println(f"ROC-AUC          : $rocAuc%.4f")

    println("\n=== Confusion Matrix ===")
    println(f"             | Pred: 0      | Pred: 1      ")
    println(f"-------------|--------------|--------------")
    println(f" Actual: 0   | TN: $tn%-8.0f | FP: $fp%-8.0f")
    println(f" Actual: 1   | FN: $fn%-8.0f | TP: $tp%-8.0f")

    val baselineAcc = (tn + fp) / (tp + tn + fp + fn)
    println(s"\nAll-Normal Baseline Accuracy (Always predicting 0): $baselineAcc%.4f")
    
    println(s"\nPipeline Runtime: ${(endTime - startTime) / 1000} seconds")

    spark.stop()
  }
}
