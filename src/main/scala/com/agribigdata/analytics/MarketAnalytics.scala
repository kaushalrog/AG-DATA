package com.agribigdata.analytics

import org.apache.spark.sql.SparkSession

object MarketAnalytics {

  def main(args: Array[String]): Unit = {

    val spark = SparkSession.builder()
      .appName("Agricultural Market Analytics")
      .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    val inputPath = "hdfs://namenode:9000/agri-market/processed/daily_market_prices"
    val outputPath = "hdfs://namenode:9000/agri-market/analytics"

    println("=" * 70)
    println("AGRICULTURAL MARKET SPARK ANALYTICS")
    println("=" * 70)

    println("\n[1] Reading Parquet from HDFS...")
    val df = spark.read.parquet(inputPath)

    println("\n[2] Schema:")
    df.printSchema()

    println("\n[3] Number of columns:")
    println(df.columns.length)

    println("\n[4] Number of input files:")
    println(df.inputFiles.length)

    println("\n[5] Sample records:")
    df.show(10, truncate = false)

    println("\n[6] Counting records...")
    val recordCount = df.count()
    println(s"Total records = $recordCount")

    println("\n[7] Performing Analytics...")
    import org.apache.spark.sql.functions._
    val columns = df.columns.toSet

    // 1. Commodity Statistics
    if (columns.contains("commodity")) {
      println(" -> Calculating Commodity-wise Statistics...")
      val commodityStats = df.groupBy("commodity")
        .agg(count("*").alias("record_count"))
        .orderBy(desc("record_count"))
      
      println("\n========== SPARK PLAN: COMMODITY ==========")
      commodityStats.explain(true)

      commodityStats.show(5, truncate = false)
      commodityStats.write.mode("overwrite").parquet(s"$outputPath/commodity_statistics")
    }

    // 2. State Statistics
    if (columns.contains("state")) {
      println(" -> Calculating State-wise Statistics...")
      val stateStats = df.groupBy("state")
        .agg(count("*").alias("record_count"))
        .orderBy(desc("record_count"))
      
      println("\n========== SPARK PLAN: STATE ==========")
      stateStats.explain(true)

      stateStats.show(5, truncate = false)
      stateStats.write.mode("overwrite").parquet(s"$outputPath/state_statistics")
    }

    // 3. Yearly Statistics
    if (columns.contains("arrival_date")) {
      println(" -> Calculating Yearly Statistics...")
      // Extract year from date. Date might be string or DateType.
      // If it's a date or timestamp, year() works. If string like YYYY-MM-DD, year() might work or substring.
      // We will try year(to_date(col("arrival_date"))) to be safe if it's string.
      val yearlyStats = df.withColumn("year", year(to_date(col("arrival_date"))))
        .groupBy("year")
        .agg(count("*").alias("record_count"))
        .orderBy(asc("year"))

      println("\n========== SPARK PLAN: YEARLY ==========")
      yearlyStats.explain(true)

      yearlyStats.show(5, truncate = false)
      yearlyStats.write.mode("overwrite").parquet(s"$outputPath/yearly_statistics")
    }

    // 4. Price Statistics
    val priceCols = Seq("modal_price", "min_price", "max_price").filter(columns.contains)
    if (columns.contains("commodity") && priceCols.nonEmpty) {
      println(" -> Calculating Price Statistics by Commodity...")
      val aggExprs = priceCols.flatMap(c => Seq(
        avg(col(c)).alias(s"avg_$c"),
        min(col(c)).alias(s"min_$c"),
        max(col(c)).alias(s"max_$c")
      ))

      val priceStats = df.groupBy("commodity")
        .agg(aggExprs.head, aggExprs.tail: _*)
        .orderBy("commodity")

      println("\n========== SPARK PLAN: PRICE ==========")
      priceStats.explain(true)

      priceStats.show(5, truncate = false)
      priceStats.write.mode("overwrite").parquet(s"$outputPath/price_statistics")
    }

    println("\n[8] Spark analytics completed successfully.")

    spark.stop()
  }
}
