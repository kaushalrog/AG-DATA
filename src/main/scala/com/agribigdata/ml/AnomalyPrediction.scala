package com.agribigdata.ml

import org.apache.spark.ml.Pipeline
import org.apache.spark.ml.classification.{RandomForestClassificationModel, RandomForestClassifier}
import org.apache.spark.ml.evaluation.{BinaryClassificationEvaluator, MulticlassClassificationEvaluator}
import org.apache.spark.ml.feature.{Imputer, VectorAssembler}
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types.DoubleType

object AnomalyPrediction {

  def main(args: Array[String]): Unit = {
    val spark = SparkSession.builder()
      .appName("Agricultural Market ML Anomaly Prediction")
      .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    val inputPath = "hdfs://namenode:9000/agri-market/analytics/features"
    val predictionsOutputPath = "hdfs://namenode:9000/agri-market/analytics/anomaly_predictions"
    val modelOutputPath = "hdfs://namenode:9000/agri-market/models/anomaly_prediction_rf"

    println("=" * 70)
    println("AGRICULTURAL MARKET SPARK MLLIB - ANOMALY PREDICTION")
    println("=" * 70)

    println("\n[1] Reading Feature Dataset...")
    val df = spark.read.parquet(inputPath)

    println("\n[1.5] Applying Entity-Level Downsampling to prevent OOM...")
    // Sample roughly 0.1% of entities (hash modulo 1000) to preserve full time-series history per entity
    val sampleFraction = 0.001
    val sampledDf = df.filter(abs(hash(col("state"), col("district"), col("commodity"), col("market"), col("variety"))) % 1000 === 0).cache()
    val entityCount = sampledDf.select("state", "district", "commodity", "market", "variety").distinct().count()
    val recordCount = sampledDf.count()
    println(s"Entities retained: $entityCount")
    println(s"Records retained: $recordCount")

    println("\n[2] Constructing Future Anomaly Label...")
    val windowSpec = Window.partitionBy("state", "district", "commodity", "market", "variety")
      .orderBy("arrival_date")

    // Target variable: the actual anomaly flag of the NEXT observation
    val withLabelDf = sampledDf.withColumn("next_price_outlier", lead("price_outlier", 1).over(windowSpec))
      .withColumn("label", col("next_price_outlier").cast(DoubleType))
      .filter(col("label").isNotNull)

    val inputCols = Array(
      "previous_modal_price",
      "price_change",
      "price_change_pct",
      "rolling_7_observation_avg",
      "rolling_7_observation_stddev",
      "min_price",
      "max_price",
      "modal_price"
    )
    val imputedCols = inputCols.map(c => c + "_imputed")

    println("\n[3] Splitting Data (Temporal: train < 2025, test >= 2025)...")
    val trainDfRaw = withLabelDf.filter(col("year") < 2025).cache()
    val testDf = withLabelDf.filter(col("year") >= 2025).cache()
    
    val trainCount = trainDfRaw.count()
    val testCount = testDf.count()
    
    println(s"\nFinal Training Count: $trainCount")
    println(s"Final Test Count: $testCount")
    
    println("\nClass Distribution (Training):")
    trainDfRaw.groupBy("label").count().show()
    
    val trainPositiveCount = trainDfRaw.filter(col("label") === 1.0).count()
    val trainNegativeCount = trainCount - trainPositiveCount
    val trainPositiveRate = (trainPositiveCount.toDouble / trainCount) * 100.0
    println(f"Training Positive Rate: $trainPositiveRate%.2f%%")

    val testPositiveCount = testDf.filter(col("label") === 1.0).count()
    val testPositiveRate = (testPositiveCount.toDouble / testCount) * 100.0
    println(f"Test Positive Rate (Prevalence): $testPositiveRate%.2f%%")

    // Establish Trivial Majority-Class Baseline
    // Majority class is 0.0. 
    println("\n[3.5] Majority-Class Baseline on Test Set")
    val baselineCorrect = testCount - testPositiveCount
    val baselineAccuracy = baselineCorrect.toDouble / testCount
    println(f"Trivial Baseline Accuracy (predicting all 0.0): ${baselineAccuracy * 100}%.2f%%")
    println("Trivial Baseline Positive-Class Precision: 0.0000")
    println("Trivial Baseline Positive-Class Recall:    0.0000")
    println("Trivial Baseline Positive-Class F1 Score:  0.0000")

    // Create Class Weights for Training
    val w0 = trainCount.toDouble / (2.0 * trainNegativeCount)
    val w1 = trainCount.toDouble / (2.0 * trainPositiveCount)
    val trainDf = trainDfRaw.withColumn("classWeight", when(col("label") === 0.0, lit(w0)).otherwise(lit(w1)))

    println("\n[4] Building MLlib Pipelines...")
    val imputer = new Imputer()
      .setInputCols(inputCols)
      .setOutputCols(imputedCols)
      .setStrategy("median")

    val assembler = new VectorAssembler()
      .setInputCols(imputedCols)
      .setOutputCol("features")

    // Base RF (Unweighted)
    val rfBase = new RandomForestClassifier()
      .setLabelCol("label")
      .setFeaturesCol("features")
      .setNumTrees(20)
      .setMaxDepth(8)
      .setSeed(42L)

    // Revised RF (Class Weighted)
    val rfWeighted = new RandomForestClassifier()
      .setLabelCol("label")
      .setFeaturesCol("features")
      .setWeightCol("classWeight")
      .setNumTrees(20)
      .setMaxDepth(8)
      .setSeed(42L)

    val pipelineBase = new Pipeline().setStages(Array(imputer, assembler, rfBase))
    val pipelineWeighted = new Pipeline().setStages(Array(imputer, assembler, rfWeighted))

    println("\n[5] Training PipelineModels...")
    val modelBase = pipelineBase.fit(trainDf)
    val modelWeighted = pipelineWeighted.fit(trainDf)

    println("\n[6] Evaluating on Test Data...")
    val predictionsBase = modelBase.transform(testDf).cache()
    val predictionsWeighted = modelWeighted.transform(testDf).cache()

    val multiEvaluator = new MulticlassClassificationEvaluator()
      .setLabelCol("label")
      .setPredictionCol("prediction")
      .setMetricLabel(1.0)

    val binaryEvaluator = new BinaryClassificationEvaluator()
      .setLabelCol("label")
      .setRawPredictionCol("rawPrediction")
      .setMetricName("areaUnderPR")

    def evaluateModel(name: String, preds: org.apache.spark.sql.DataFrame): Unit = {
      val precision = multiEvaluator.setMetricName("precisionByLabel").evaluate(preds)
      val recall = multiEvaluator.setMetricName("recallByLabel").evaluate(preds)
      val f1 = multiEvaluator.setMetricName("fMeasureByLabel").evaluate(preds)
      val prAuc = binaryEvaluator.evaluate(preds)

      println(s"\n--- $name ---")
      println(f"Positive-Class Precision: $precision%.4f")
      println(f"Positive-Class Recall:    $recall%.4f")
      println(f"Positive-Class F1 Score:  $f1%.4f")
      println(f"PR-AUC:                   $prAuc%.4f")

      println("Confusion Matrix:")
      preds.groupBy("label", "prediction").count().orderBy("label", "prediction").show()
    }

    evaluateModel("Unweighted Model (Current)", predictionsBase)
    evaluateModel("Class-Weighted Model (Revised)", predictionsWeighted)

    println("\n[7] Feature Importances (Revised Model):")
    val rfModel = modelWeighted.stages.last.asInstanceOf[RandomForestClassificationModel]
    val importances = rfModel.featureImportances.toArray
    val featureImportances = inputCols.zip(importances).sortBy(-_._2)
    featureImportances.foreach { case (feature, importance) =>
      println(f"$feature%-30s: $importance%.4f")
    }

    println("\n[8] Saving Predictions to HDFS (Revised Model)...")
    predictionsWeighted.drop("classWeight").write.mode("overwrite").parquet(predictionsOutputPath)

    println("\n[9] Saving PipelineModel to HDFS (Revised Model)...")
    modelWeighted.write.overwrite().save(modelOutputPath)

    println("\n[10] MLlib Pipeline evaluation completed successfully.")
    spark.stop()
  }
}
