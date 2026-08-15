package com.agribigdata.ingestion

import com.agribigdata.ingestion.Schemas.Canonical
import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions._

/**
 * Raw -> canonical readers.
 *
 * These do exactly two things: read with an explicit schema, and rename /
 * derive columns so both sources share one vocabulary. They deliberately
 * do NOT clean, filter or repair anything — cleaning is a separate,
 * auditable stage, and raw data is never modified.
 */
object Readers {

  /** Trim, collapse internal runs of whitespace, and null out empties. */
  private def norm(colName: String) = {
    val cleaned = trim(regexp_replace(col(colName), "\\s+", " "))
    when(cleaned === "" || upper(cleaned).isin("NA", "N/A", "NULL", "-"), lit(null: String))
      .otherwise(cleaned)
  }

  // =============================================================
  // SOURCE 1 — Daily Market Prices
  // =============================================================
  def dailyMarketPrices(spark: SparkSession, path: String): DataFrame = {
    spark.read
      .schema(Schemas.dailyMarketPrices)
      .option("header", "true")
      // RFC-4180 quoting: required, ~5.3k rows in 2026.csv alone have
      // commas inside quoted commodity names.
      .option("quote", "\"")
      .option("escape", "\"")
      .option("multiLine", "false")
      // PERMISSIVE: a row that does not fit the schema yields nulls
      // instead of aborting the job. Those nulls are then counted by the
      // quality stage rather than silently disappearing.
      .option("mode", "PERMISSIVE")
      .csv(path)
      .select(
        norm("State").as(Canonical.state),
        norm("District").as(Canonical.district),
        norm("Market").as(Canonical.market),
        norm("Commodity").as(Canonical.commodity),
        norm("Variety").as(Canonical.variety),
        norm("Grade").as(Canonical.grade),
        // Single ISO format confirmed across all 26 files.
        to_date(trim(col("Arrival_Date")), "yyyy-MM-dd").as(Canonical.arrivalDate),
        col("Min_Price").as(Canonical.minPrice),
        col("Max_Price").as(Canonical.maxPrice),
        col("Modal_Price").as(Canonical.modalPrice),
        // This source reports no arrival quantity. Kept as a typed null
        // so the canonical schema is identical across sources.
        lit(null).cast("double").as(Canonical.arrivalsTonnes),
        lit(null).cast("string").as(Canonical.commodityGroup),
        lit("daily_market_prices").as(Canonical.sourceDataset),
        lit("real").as(Canonical.dataSource)
      )
  }

  // =============================================================
  // SOURCE 2 — India Mandi
  // =============================================================
  def indiaMandi(spark: SparkSession, path: String): DataFrame = {
    spark.read
      .schema(Schemas.indiaMandi)   // binds by position => both header variants work
      .option("header", "true")
      .option("quote", "\"")
      .option("escape", "\"")
      .option("mode", "PERMISSIVE")
      .csv(path)
      // input_file_name() is the only place the commodity exists: this
      // source has no commodity column, one file per commodity.
      .withColumn("_src_file", input_file_name())
      .select(
        norm("State_Name").as(Canonical.state),
        norm("District_Name").as(Canonical.district),
        norm("Market_Name").as(Canonical.market),
        // "…/Arhar%20Dal(Tur%20Dal).csv" -> "Arhar Dal(Tur Dal)".
        // Spark percent-encodes spaces in input_file_name(), so decode
        // before stripping the directory and the .csv suffix.
        trim(regexp_replace(
          regexp_extract(col("_src_file"), "([^/]+)\\.csv$", 1),
          "%20", " "
        )).as(Canonical.commodity),
        norm("Variety").as(Canonical.variety),
        // No grade column in this source.
        lit(null).cast("string").as(Canonical.grade),
        // Two date formats are mixed across the 325 files, and the split
        // does not follow the header split, so both are attempted per
        // row. coalesce returns the first that parses; if neither does
        // the result is null and the quality stage flags MISSING_DATE.
        coalesce(
          to_date(trim(col("Reported_Date")), "dd MMM yyyy"),
          to_date(trim(col("Reported_Date")), "yyyy-MM-dd")
        ).as(Canonical.arrivalDate),
        col("Min_Price").as(Canonical.minPrice),
        col("Max_Price").as(Canonical.maxPrice),
        col("Modal_Price").as(Canonical.modalPrice),
        // The distinguishing feature of this source: quantity arriving
        // at the mandi. Header says Tonnes in 293 of 315 non-empty files
        // and the bare-header files carry the same magnitudes.
        col("Arrivals").as(Canonical.arrivalsTonnes),
        norm("Group").as(Canonical.commodityGroup),
        lit("india_mandi").as(Canonical.sourceDataset),
        lit("real").as(Canonical.dataSource)
      )
  }
}
