package com.agribigdata.ingestion

import org.apache.spark.sql.types._

/**
 * Explicit schemas for every source.
 *
 * Nothing in this project uses `inferSchema`. Inference costs a full extra
 * pass over the data (~12 GB here) and, worse, it is not stable: the 2001
 * file writes prices as `1400` and the 2025 file writes `3200.0`, so
 * inference can hand back Integer for one year and Double for another and
 * the union then fails. Declaring the schema makes the read single-pass
 * and the types identical across all 26 files.
 */
object Schemas {

  // =============================================================
  // SOURCE 1 — Daily Market Prices 2001..2026 (one CSV per year)
  //
  // Header (verified identical in all 26 files):
  //   State,District,Market,Commodity,Variety,Grade,Arrival_Date,
  //   Min_Price,Max_Price,Modal_Price,Commodity_Code
  //
  // Note: 5,307 rows in 2026.csv alone carry quoted fields with embedded
  // commas, e.g. "Sesamum (Sesame,Gingelly,Til)". Spark's CSV reader
  // handles these via RFC-4180 quoting, which is exactly why this project
  // does not split on commas by hand anywhere.
  // =============================================================
  val dailyMarketPrices: StructType = StructType(Seq(
    StructField("State",          StringType,  nullable = true),
    StructField("District",       StringType,  nullable = true),
    StructField("Market",         StringType,  nullable = true),
    StructField("Commodity",      StringType,  nullable = true),
    StructField("Variety",        StringType,  nullable = true),
    StructField("Grade",          StringType,  nullable = true),
    // Read as String, parsed explicitly later. Letting the CSV reader
    // parse the date would turn a malformed value into a whole-row drop
    // (or a job failure); we want it to survive as a null so the
    // data-quality layer can count and classify it.
    StructField("Arrival_Date",   StringType,  nullable = true),
    StructField("Min_Price",      DoubleType,  nullable = true),
    StructField("Max_Price",      DoubleType,  nullable = true),
    StructField("Modal_Price",    DoubleType,  nullable = true),
    StructField("Commodity_Code", IntegerType, nullable = true)
  ))

  // =============================================================
  // SOURCE 2 — India Mandi (one CSV per commodity, 325 files)
  //
  // This source is messier than source 1, in three ways that were
  // confirmed by inspecting all 325 files:
  //
  //  1. TWO header variants exist:
  //       293 files: "... Arrivals (Tonnes),Min Price (Rs./Quintal),..."
  //        22 files: "... Arrivals,Min Price,..."
  //     Column ORDER is identical in both. Supplying this schema with
  //     `header=true` makes Spark skip the header line and bind by
  //     POSITION, so both variants land in the same columns without any
  //     per-file branching.
  //
  //  2. TWO date formats are mixed across files (294 files use
  //     "19 Aug 2013", 21 use "2005-08-24") and the split does not line
  //     up with the header split. So the date is read as String and both
  //     formats are attempted per row — see IndiaMandiReader.
  //
  //  3. There is NO commodity column. The commodity is the file name
  //     ("Tomato.csv"), and the "Variety" column holds values like
  //     "Tomato" or "Other". The reader recovers it from the path.
  // =============================================================
  val indiaMandi: StructType = StructType(Seq(
    StructField("State_Name",    StringType, nullable = true),
    StructField("District_Name", StringType, nullable = true),
    StructField("Market_Name",   StringType, nullable = true),
    StructField("Variety",       StringType, nullable = true),
    StructField("Group",         StringType, nullable = true),
    StructField("Arrivals",      DoubleType, nullable = true),
    StructField("Min_Price",     DoubleType, nullable = true),
    StructField("Max_Price",     DoubleType, nullable = true),
    StructField("Modal_Price",   DoubleType, nullable = true),
    StructField("Reported_Date", StringType, nullable = true)
  ))

  // =============================================================
  // CANONICAL SCHEMA
  //
  // Both sources are standardised onto these column names before any
  // downstream stage touches them. The two sources are NOT concatenated
  // blindly: see docs/ for the unit-verification question that governs
  // whether their price columns may be compared at all.
  // =============================================================
  object Canonical {
    val state         = "state"
    val district      = "district"
    val market        = "market"
    val commodity     = "commodity"
    val variety       = "variety"
    val grade         = "grade"
    val arrivalDate   = "arrival_date"
    val minPrice      = "min_price"
    val maxPrice      = "max_price"
    val modalPrice    = "modal_price"
    val arrivalsTonnes= "arrivals_tonnes"
    val commodityGroup= "commodity_group"

    /** Provenance — every row carries where it came from. */
    val sourceDataset = "source_dataset"   // daily_market_prices | india_mandi
    val dataSource    = "data_source"      // real | synthetic_scaled

    /** Data-quality verdict assigned by the preprocessing stage. */
    val qualityFlag   = "quality_flag"
  }

  /**
   * Data-quality classifications.
   *
   * These describe the RECORD, not the market. A record can be perfectly
   * valid data and still describe an unusual market event, and a record
   * can be garbage without the market having done anything at all. The
   * pipeline resolves quality first and only then looks for market
   * anomalies.
   */
  object Quality {
    val Valid             = "VALID"
    val MissingDate       = "MISSING_DATE"        // date absent or unparseable
    val MissingPrice      = "MISSING_PRICE"       // modal price absent
    val ZeroMinMax        = "ZERO_MIN_MAX"        // min and max both 0, modal > 0
    val ZeroMax           = "ZERO_MAX"            // max 0 while min > 0
    val NegativePrice     = "NEGATIVE_PRICE"
    val MinGreaterThanMax = "MIN_GT_MAX"
    val ModalOutsideRange = "MODAL_OUTSIDE_RANGE"

    /** Only VALID rows are eligible for modelling. */
    val modellable: Set[String] = Set(Valid)
  }
}
