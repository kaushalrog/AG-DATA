package com.agribigdata.profiling

import com.agribigdata.utils.SparkSetup
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._
import com.agribigdata.ingestion.Schemas.Canonical

object PriceUnitCheck {
  def main(args: Array[String]): Unit = {
    val spark = SparkSetup.session("PriceUnitCheck")
    spark.sparkContext.setLogLevel("WARN")

    import spark.implicits._

    println("Loading processed datasets from local data/processed/...")
    
    val s1 = spark.read.parquet("data/processed/daily_market_prices")
      .filter(col(Canonical.qualityFlag) === "VALID")
      .select(
        col(Canonical.state),
        col(Canonical.district),
        col(Canonical.market),
        col(Canonical.commodity),
        col(Canonical.variety),
        col(Canonical.arrivalDate),
        col(Canonical.modalPrice).alias("modal_s1")
      )

    val s2 = spark.read.parquet("data/processed/india_mandi")
      .filter(col(Canonical.qualityFlag) === "VALID")
      .select(
        col(Canonical.state),
        col(Canonical.district),
        col(Canonical.market),
        col(Canonical.commodity),
        col(Canonical.variety),
        col(Canonical.arrivalDate),
        col(Canonical.modalPrice).alias("modal_s2")
      )

    println("Computing inner join on business keys...")
    val joinCols = Seq(
      Canonical.state, Canonical.district, Canonical.market, 
      Canonical.commodity, Canonical.variety, Canonical.arrivalDate
    )

    val joined = s1.join(s2, joinCols, "inner")
      .withColumn("ratio", col("modal_s1") / col("modal_s2"))

    val count = joined.count()
    println(s"Overlapping records: $count")

    if (count > 0) {
      println("Stats for overlapping records:")
      joined.select(
        expr("percentile_approx(modal_s1, 0.5)").alias("median_s1"),
        expr("percentile_approx(modal_s2, 0.5)").alias("median_s2"),
        mean("modal_s1").alias("mean_s1"),
        mean("modal_s2").alias("mean_s2"),
        min("modal_s1").alias("min_s1"),
        max("modal_s1").alias("max_s1"),
        min("modal_s2").alias("min_s2"),
        max("modal_s2").alias("max_s2")
      ).show(false)

      println("Distribution of ratios (s1 / s2):")
      val buckets = joined.withColumn("ratio_bucket", 
        when($"ratio".between(0.8, 1.2), "Near 1x")
        .when($"ratio".between(8.0, 12.0), "Near 10x")
        .when($"ratio".between(80.0, 120.0), "Near 100x")
        .when($"ratio".between(800.0, 1200.0), "Near 1000x")
        .otherwise("Other")
      )

      buckets.groupBy("ratio_bucket").count()
        .withColumn("percentage", round(col("count") / count * 100, 2))
        .orderBy("ratio_bucket")
        .show(false)

      println("Representative concrete examples (Near 10x):")
      buckets.filter($"ratio_bucket" === "Near 10x").show(5, false)

      println("Representative concrete examples (Near 1x):")
      buckets.filter($"ratio_bucket" === "Near 1x").show(5, false)
      
      println("Representative concrete examples (Near 100x):")
      buckets.filter($"ratio_bucket" === "Near 100x").show(5, false)
    }

    spark.stop()
  }
}
