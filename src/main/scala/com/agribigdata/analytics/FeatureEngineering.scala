package com.agribigdata.analytics

import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.functions._

object FeatureEngineering {

  def main(args: Array[String]): Unit = {

    val spark = SparkSession.builder()
      .appName("Agricultural Market Feature Engineering")
      .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    val inputPath = "hdfs://namenode:9000/agri-market/processed/daily_market_prices"
    val outputPath = "hdfs://namenode:9000/agri-market/analytics/features"

    println("=" * 70)
    println("AGRICULTURAL MARKET SPARK FEATURE ENGINEERING")
    println("=" * 70)

    println("\n[1] Reading Parquet from HDFS...")
    val df = spark.read.parquet(inputPath)

    val initialColCount = df.columns.length
    println(s"Initial number of columns: $initialColCount")

    println("\n[2] Applying Spark Window Functions...")
    
    // Define Window partitioned by state, district, commodity, market, variety and ordered by arrival_date
    val windowSpec = Window.partitionBy("state", "district", "commodity", "market", "variety")
      .orderBy("arrival_date")

    // Define 7-observation rolling window
    val rollingWindowSpec = windowSpec.rowsBetween(-6, 0)

    // Calculate features
    val featureDf = df
      .withColumn("previous_modal_price", lag("modal_price", 1).over(windowSpec))
      .withColumn("price_change", col("modal_price") - col("previous_modal_price"))
      .withColumn(
        "price_change_pct",
        when(col("previous_modal_price").isNull || col("previous_modal_price") === 0.0, lit(null))
          .otherwise(((col("modal_price") - col("previous_modal_price")) / col("previous_modal_price")) * 100)
      )
      .withColumn("rolling_7_observation_avg", avg("modal_price").over(rollingWindowSpec))
      .withColumn("rolling_7_observation_stddev", stddev("modal_price").over(rollingWindowSpec))

    val finalColCount = featureDf.columns.length
    println(s"Final number of columns: $finalColCount")

    println("\n[3] Writing feature dataset to HDFS as Parquet...")
    featureDf.write.mode("overwrite").parquet(outputPath)

    println("\n[4] Validating Feature Engineering Results...")
    // Read back from HDFS to avoid recomputing the entire pipeline for actions
    val savedFeatures = spark.read.parquet(outputPath)

    println("\nFeature Dataset Schema:")
    savedFeatures.printSchema()

    println("\nCounting records (from saved Parquet)...")
    val recordCount = savedFeatures.count()
    println(s"Total records processed = $recordCount")

    println("\nSample Records (Selected feature columns):")
    savedFeatures.select(
      "state",
      "district",
      "commodity",
      "market",
      "variety",
      "arrival_date",
      "modal_price",
      "previous_modal_price",
      "price_change",
      "price_change_pct",
      "rolling_7_observation_avg",
      "rolling_7_observation_stddev"
    ).show(20, truncate = false)

    println("\n[5] Feature Engineering completed successfully.")

    spark.stop()
  }
}
