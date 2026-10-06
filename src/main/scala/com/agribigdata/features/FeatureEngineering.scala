package com.agribigdata.features

import com.agribigdata.utils.SparkSetup
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.functions._
import com.agribigdata.ingestion.Schemas.Canonical

object FeatureEngineering {
  def main(args: Array[String]): Unit = {
    val spark = SparkSetup.session("FeatureEngineering")
    spark.sparkContext.setLogLevel("WARN")
    import spark.implicits._

    val s1Path = "data/processed/daily_market_prices"
    val s2Path = "data/processed/india_mandi"
    val canonicalOutPath = "data/processed/canonical"
    val featuresOutPath = "data/features/engineered"

    println(s"Reading source data from $s1Path and $s2Path")
    val s1Raw = spark.read.parquet(s1Path).filter(col(Canonical.qualityFlag) === "VALID")
    val s2Raw = spark.read.parquet(s2Path).filter(col(Canonical.qualityFlag) === "VALID")

    val joinCols = Seq(Canonical.state, Canonical.district, Canonical.market, Canonical.commodity, Canonical.variety, Canonical.arrivalDate)

    val s1 = s1Raw.dropDuplicates(joinCols)
    val s2 = s2Raw.dropDuplicates(joinCols)

    println("Merging to canonical dataset...")
    
    val s2JoinData = s2.select((joinCols :+ Canonical.arrivalsTonnes).map(col): _*)
      .withColumn("has_s2_arrivals", lit(true))

    val s1Enriched = s1.alias("s1").join(s2JoinData.alias("s2"), joinCols, "left")
      .select(
        col("s1.*"),
        col("s2." + Canonical.arrivalsTonnes).alias("joined_arrivals"),
        col("s2.has_s2_arrivals")
      )
      .withColumn(Canonical.arrivalsTonnes, coalesce(col(Canonical.arrivalsTonnes), col("joined_arrivals")))
      .drop("joined_arrivals")
      .withColumn("price_source_dataset", lit("daily_market_prices"))
      .withColumn("arrivals_source_dataset", when(col("has_s2_arrivals").isNotNull, lit("india_mandi")).otherwise(lit(null).cast("string")))
      .drop("has_s2_arrivals")

    val s2Only = s2.join(s1.select(joinCols.map(col): _*), joinCols, "left_anti")
      .withColumn("price_source_dataset", lit("india_mandi"))
      .withColumn("arrivals_source_dataset", lit("india_mandi"))

    val canonicalData = s1Enriched.unionByName(s2Only, allowMissingColumns = true)

    println(s"Writing canonical dataset to $canonicalOutPath")
    canonicalData.write.mode("overwrite").parquet(canonicalOutPath)

    println("Validating written canonical dataset...")
    val canonicalRead = spark.read.parquet(canonicalOutPath)
    val canonicalCount = canonicalRead.count()
    val dupCount = canonicalRead.groupBy(joinCols.map(col): _*).count().filter($"count" > 1).count()
    
    println(s"Canonical row count: $canonicalCount")
    println(s"Canonical duplicate groups: $dupCount")
    
    if (dupCount > 0) {
      throw new RuntimeException("Canonical dataset has duplicate keys! Hard gate failed.")
    }

    println("Starting Phase 8 Feature Engineering...")
    
    // Use strictly historical window: -7 to -1
    val wHist7 = Window.partitionBy(
      Canonical.state, Canonical.district, Canonical.market, Canonical.commodity, Canonical.variety
    ).orderBy(Canonical.arrivalDate).rowsBetween(-7, -1)
    
    // Use lag 1 window for previous modal price
    val wLag1 = Window.partitionBy(
      Canonical.state, Canonical.district, Canonical.market, Canonical.commodity, Canonical.variety
    ).orderBy(Canonical.arrivalDate)

    val engineeredData = canonicalRead
      .withColumn("previous_modal_price", lag(col(Canonical.modalPrice), 1).over(wLag1))
      .withColumn("price_change", col(Canonical.modalPrice) - col("previous_modal_price"))
      .withColumn("price_change_pct", when(col("previous_modal_price") === 0.0, lit(null)).otherwise(col("price_change") / col("previous_modal_price")))
      .withColumn("price_range", col(Canonical.maxPrice) - col(Canonical.minPrice))
      .withColumn("relative_price_range", when(col(Canonical.modalPrice) === 0.0, lit(null)).otherwise(col("price_range") / col(Canonical.modalPrice)))
      .withColumn("previous_to_current_ratio", when(col(Canonical.modalPrice) === 0.0, lit(null)).otherwise(col("previous_modal_price") / col(Canonical.modalPrice)))
      .withColumn("rolling_7_observation_avg", avg(col(Canonical.modalPrice)).over(wHist7))
      .withColumn("rolling_7_observation_stddev", stddev(col(Canonical.modalPrice)).over(wHist7))
      .withColumn("z_score", when(col("rolling_7_observation_stddev") === 0.0, lit(null)).otherwise((col(Canonical.modalPrice) - col("rolling_7_observation_avg")) / col("rolling_7_observation_stddev")))

    println(s"Writing engineered features to $featuresOutPath")
    engineeredData.write.mode("overwrite").parquet(featuresOutPath)

    println("Validating final feature output...")
    val featuresRead = spark.read.parquet(featuresOutPath)
    
    val featureCount = featuresRead.count()
    val finalDupCount = featuresRead.groupBy(joinCols.map(col): _*).count().filter($"count" > 1).count()
    
    println(s"Final engineered row count: $featureCount")
    println(s"Final duplicate groups: $finalDupCount")
    println("\nSchema:")
    featuresRead.printSchema()

    println("\nNull rates for key features:")
    val featureCols = Seq("previous_modal_price", "price_change", "price_change_pct", "price_range", "relative_price_range", "previous_to_current_ratio", "rolling_7_observation_avg", "rolling_7_observation_stddev", "z_score")
    val nullCounts = featuresRead.select(featureCols.map(c => sum(when(col(c).isNull, 1).otherwise(0)).alias(c)): _*).head()
    for (i <- featureCols.indices) {
      val c = featureCols(i)
      val n = nullCounts.getLong(i)
      val pct = 100.0 * n / featureCount
      println(f"  $c%-30s : $n%12d ($pct%5.2f%%)")
    }

    println("\nSample rows (with z_score > 2.0 to show anomaly detection functionality):")
    featuresRead.filter(col("z_score") > 2.0)
      .select(
        Canonical.commodity, Canonical.arrivalDate,
        Canonical.modalPrice, "rolling_7_observation_avg", "rolling_7_observation_stddev", "z_score", "price_change_pct"
      ).show(10, false)

    spark.stop()
  }
}
