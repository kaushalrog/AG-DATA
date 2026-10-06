package com.agribigdata.ml

import com.agribigdata.utils.SparkSetup
import org.apache.spark.ml.PipelineModel

object Phase9HdfsVerification {
  def main(args: Array[String]): Unit = {
    val spark = SparkSetup.session("Phase9HdfsVerification")
    spark.sparkContext.setLogLevel("WARN")

    val modelPath = "hdfs://localhost:9000/agri/models/anomaly_prediction_rf"
    val predsPath = "hdfs://localhost:9000/agri/analytics/anomaly_predictions"

    try {
      println(s"Loading model from $modelPath ...")
      val loadedModel = PipelineModel.load(modelPath)
      println("HDFS MODEL LOAD TEST: PASS")
    } catch {
      case e: Exception => 
        println("HDFS MODEL LOAD TEST: FAIL")
        println(s"Error: ${e.getMessage}")
    }

    try {
      println(s"Reading predictions from $predsPath ...")
      val preds = spark.read.parquet(predsPath)
      val count = preds.count()
      println(s"Prediction Row Count: $count")
      
      val requiredCols = Seq("prediction", "target_anomaly")
      val hasCols = requiredCols.forall(preds.columns.contains)
      println(s"Prediction Columns Verified: $hasCols")
      
      if (count == 52303 && hasCols) {
        println("HDFS PREDICTION VERIFICATION: PASS")
      } else {
        println("HDFS PREDICTION VERIFICATION: FAIL")
      }
    } catch {
      case e: Exception =>
        println("HDFS PREDICTION VERIFICATION: FAIL")
        println(s"Error: ${e.getMessage}")
    }

    spark.stop()
  }
}
