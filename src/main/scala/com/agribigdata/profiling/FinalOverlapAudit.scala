package com.agribigdata.profiling

import com.agribigdata.utils.SparkSetup
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._
import com.agribigdata.ingestion.Schemas.Canonical

object FinalOverlapAudit {
  def main(args: Array[String]): Unit = {
    val spark = SparkSetup.session("FinalOverlapAudit")
    spark.sparkContext.setLogLevel("WARN")
    import spark.implicits._

    val s1Raw = spark.read.parquet("data/processed/daily_market_prices")
      .filter(col(Canonical.qualityFlag) === "VALID")
    val s2Raw = spark.read.parquet("data/processed/india_mandi")
      .filter(col(Canonical.qualityFlag) === "VALID")

    val joinCols = Seq(Canonical.state, Canonical.district, Canonical.market, Canonical.commodity, Canonical.variety, Canonical.arrivalDate)

    // Deduplicate internally first to get unique business keys per source
    // S1 might have duplicates internally as per PROJECT_STATUS (1.55%)
    val s1 = s1Raw.dropDuplicates(joinCols)
    val s2 = s2Raw.dropDuplicates(joinCols)

    val s1Count = s1Raw.count()
    val s2Count = s2Raw.count()
    val s1Unique = s1.count()
    val s2Unique = s2.count()

    val joined = s1.alias("s1").join(s2.alias("s2"), joinCols, "inner")
    val overlapCount = joined.count()

    println("=== TASK 1: THE 27 DISCREPANCIES ===")
    val discrepant = joined
      .withColumn("modal_s1", col("s1." + Canonical.modalPrice))
      .withColumn("modal_s2", col("s2." + Canonical.modalPrice))
      .withColumn("ratio", col("modal_s1") / col("modal_s2"))
      .filter(!(col("ratio").between(0.8, 1.2)))
      
    discrepant.select(
      Canonical.state, Canonical.district, Canonical.market, Canonical.commodity, Canonical.variety, Canonical.arrivalDate,
      "modal_s1", "modal_s2", "ratio"
    ).show(30, false)

    println("=== TASK 2: DUPLICATION COUNTS ===")
    println(s"Source 1 Rows: $s1Count")
    println(s"Source 2 Rows: $s2Count")
    println(s"Source 1 Unique Keys: $s1Unique")
    println(s"Source 2 Unique Keys: $s2Unique")
    println(s"Overlapping Keys: $overlapCount")

    println("=== TASK 3: CANONICAL COMBINATION ===")
    // Policy: S1 canonical, S2 fallback. Preserve arrivals from S2.
    // We already deduplicated internally for the test.
    val s1Enriched = s1.alias("s1")
      .join(s2.alias("s2").select((joinCols :+ Canonical.arrivalsTonnes).map(col): _*), joinCols, "left")
      .select(
        col("s1.*"),
        col("s2." + Canonical.arrivalsTonnes).alias("joined_arrivals")
      )
      .withColumn(Canonical.arrivalsTonnes, coalesce(col(Canonical.arrivalsTonnes), col("joined_arrivals")))
      .drop("joined_arrivals")
      .withColumn(Canonical.sourceDataset, lit("daily_market_prices"))

    val s2Only = s2.alias("s2")
      .join(s1.alias("s1").select(joinCols.map(col): _*), joinCols, "left_anti")
      .withColumn(Canonical.sourceDataset, lit("india_mandi"))

    // Ensure columns match for union
    val finalCols = s1Enriched.columns.map(col)
    val canonicalData = s1Enriched.select(finalCols: _*).unionByName(s2Only.select(finalCols: _*), allowMissingColumns = true)

    val finalCount = canonicalData.count()
    val finalS1Contrib = s1Enriched.count()
    val finalS2Contrib = s2Only.count()

    val finalDupGroupCount = canonicalData.groupBy(joinCols.map(col): _*).count().filter($"count" > 1).count()

    println(s"Final Row Count: $finalCount")
    println(s"Rows contributed entirely by Source 1 (including overlaps resolved to S1): $finalS1Contrib")
    println(s"Rows contributed only by Source 2: $finalS2Contrib")
    println(s"Overlapping rows resolved to Source 1: $overlapCount")
    println(s"Final Duplicate Groups Count: $finalDupGroupCount")

    println("=== TASK 4: ARRIVALS_TONNES COMPATIBILITY ===")
    val overlappingArrivals = joined.select(col("s2." + Canonical.arrivalsTonnes).alias("arr"))
    
    val arrTotal = overlappingArrivals.count()
    val arrNonNull = overlappingArrivals.filter($"arr".isNotNull).count()
    val arrNullPct = 100.0 * (arrTotal - arrNonNull) / arrTotal

    println(s"Overlapping records: $arrTotal")
    println(s"Where arrivals_tonnes exists: $arrNonNull")
    println(f"Null percentage: $arrNullPct%.2f%%")

    if (arrNonNull > 0) {
      overlappingArrivals.select(
        min("arr").alias("min_arrivals"),
        max("arr").alias("max_arrivals"),
        mean("arr").alias("mean_arrivals"),
        expr("percentile_approx(arr, 0.5)").alias("median_arrivals")
      ).show(false)
    }

    val s2MultipleKeys = s2Raw.groupBy(joinCols.map(col): _*).count().filter($"count" > 1).count()
    println(s"Multiple Source 2 rows for same business key: $s2MultipleKeys")

    spark.stop()
  }
}
