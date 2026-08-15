package com.agribigdata.profiling

import com.agribigdata.ingestion.{Readers, Schemas}
import com.agribigdata.ingestion.Schemas.Canonical
import com.agribigdata.preprocessing.DataQuality
import com.agribigdata.utils.SparkSetup
import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions._

/**
 * PHASE 4 — distributed profiling of the real source data.
 *
 * Establishes, from the data itself rather than from filenames or
 * assumptions:
 *   - true record counts
 *   - true date coverage (the file called 2026.csv does NOT contain only
 *     2026 data, so filenames are not trusted anywhere)
 *   - null density per column
 *   - the data-quality breakdown
 *   - duplicate business keys
 *   - dimension cardinalities
 *
 * Every number is produced by a Spark aggregation. Nothing is collected
 * to the driver except single-row summaries.
 *
 * Run:
 *   sbt "runMain com.agribigdata.profiling.ProfileDatasets"
 *   sbt "runMain com.agribigdata.profiling.ProfileDatasets --source daily --years 2025"
 */
object ProfileDatasets {

  private val RawDaily = "data/raw/Daily_Market_Prices_2001_2026/csv"
  private val RawMandi = "data/raw/india_mandi"
  private val OutDir   = "results/profiling"

  def main(args: Array[String]): Unit = {
    val opts   = parseArgs(args)
    val source = opts.getOrElse("source", "all")
    val years  = opts.get("years")

    val spark = SparkSetup.session("AgriProfile")
    spark.sparkContext.setLogLevel("WARN")

    try {
      if (source == "all" || source == "daily") {
        val path = years match {
          case Some(y) => y.split(",").map(v => s"$RawDaily/${v.trim}.csv").mkString(",")
          case None    => s"$RawDaily/*.csv"
        }
        profile(spark, "daily_market_prices", Readers.dailyMarketPrices(spark, path))
      }

      if (source == "all" || source == "mandi") {
        profile(spark, "india_mandi", Readers.indiaMandi(spark, s"$RawMandi/*.csv"))
      }
    } finally {
      spark.stop()
    }
  }

  // -----------------------------------------------------------------
  private def profile(spark: SparkSession, name: String, rawDf: DataFrame): Unit = {
    import spark.implicits._

    println("\n" + "=" * 68)
    println(s"PROFILING: $name")
    println("=" * 68)

    val df = DataQuality.withQualityFlag(rawDf)

    // Read once, use many times. Without this the CSV would be re-parsed
    // for every aggregation below. DISK_ONLY because the parsed rows are
    // far larger than RAM at full scale and we would rather pay disk I/O
    // than evict and re-parse.
    df.persist(org.apache.spark.storage.StorageLevel.DISK_ONLY)

    // --- 1. Volume + true temporal coverage ------------------------
    // One pass produces the count and the real date range. This is the
    // authoritative answer to "what does this dataset actually cover",
    // as opposed to what the file names suggest.
    val (overview, tOverview) = SparkSetup.timed(s"$name: overview") {
      df.agg(
        count(lit(1)).as("total_records"),
        min(col(Canonical.arrivalDate)).as("min_date"),
        max(col(Canonical.arrivalDate)).as("max_date"),
        sum(when(col(Canonical.arrivalDate).isNull, 1).otherwise(0)).as("unparseable_dates")
      ).head()
    }

    val total = overview.getAs[Long]("total_records")
    println(f"  records            : $total%,d")
    println(s"  date range (actual): ${overview.get(1)}  ..  ${overview.get(2)}")
    println(f"  unparseable dates  : ${overview.getAs[Long]("unparseable_dates")}%,d")

    // --- 2. Null density per column --------------------------------
    // Built as a single agg over all columns rather than one pass each.
    val nullCols = df.columns.map { c =>
      sum(when(col(c).isNull, 1L).otherwise(0L)).as(c)
    }
    val nullRow = df.agg(nullCols.head, nullCols.tail.toIndexedSeq: _*).head()
    println("\n  NULLS BY COLUMN")
    df.columns.zipWithIndex.foreach { case (c, i) =>
      val n = Option(nullRow.get(i)).map(_.asInstanceOf[Long]).getOrElse(0L)
      val pct = if (total > 0) n * 100.0 / total else 0.0
      println(f"    $c%-18s $n%12s  ($pct%6.2f%%)")
    }

    // --- 3. Data-quality breakdown ---------------------------------
    println("\n  DATA-QUALITY CLASSIFICATION")
    val quality = df
      .groupBy(Canonical.qualityFlag)
      .agg(count(lit(1)).as("records"))
      .orderBy(desc("records"))
    // Bounded output: there are only 8 possible quality classes.
    quality.collect().foreach { r =>
      val n   = r.getAs[Long]("records")
      val pct = if (total > 0) n * 100.0 / total else 0.0
      println(f"    ${r.getString(0)}%-22s $n%12s  ($pct%6.2f%%)")
    }

    // --- 4. Duplicates, via business key (never whole-row distinct) --
    val ((distinctKeys, dupKeys, surplus), tDup) =
      SparkSetup.timed(s"$name: duplicate scan") { DataQuality.duplicateStats(df) }
    println("\n  DUPLICATES (business key: source+state+district+market+commodity+variety+date)")
    println(f"    distinct keys     : $distinctKeys%,d")
    println(f"    keys seen > once  : $dupKeys%,d")
    println(f"    surplus rows      : $surplus%,d")

    // --- 5. Dimension cardinality ----------------------------------
    // approx_count_distinct (HyperLogLog++) rather than exact: the exact
    // version needs a full shuffle per column, the approximation needs a
    // few KB of sketch per partition and is well inside 2% error.
    val dims = Seq(Canonical.state, Canonical.district, Canonical.market,
                   Canonical.commodity, Canonical.variety, Canonical.grade)
    val cardRow = df.agg(
      approx_count_distinct(col(dims.head), 0.02).as(dims.head),
      dims.tail.map(d => approx_count_distinct(col(d), 0.02).as(d)): _*
    ).head()
    println("\n  DIMENSION CARDINALITY (HLL++, ~2% error)")
    dims.zipWithIndex.foreach { case (d, i) =>
      println(f"    $d%-18s ~${cardRow.getAs[Long](i)}%,d")
    }

    // --- 6. Price statistics over VALID rows only ------------------
    // Computed on VALID rows because including zero-price partial
    // reports would drag every mean toward zero and make the statistics
    // describe the reporting process rather than the market.
    val valid = df.filter(col(Canonical.qualityFlag) === Schemas.Quality.Valid)
    val priceRow = valid.agg(
      count(lit(1)).as("valid_records"),
      round(avg(col(Canonical.modalPrice)), 2).as("mean_modal"),
      round(stddev(col(Canonical.modalPrice)), 2).as("stddev_modal"),
      min(col(Canonical.modalPrice)).as("min_modal"),
      max(col(Canonical.modalPrice)).as("max_modal")
    ).head()
    println("\n  MODAL PRICE (VALID rows only)")
    println(f"    valid records     : ${priceRow.getAs[Long]("valid_records")}%,d")
    println(s"    mean / stddev     : ${priceRow.get(1)} / ${priceRow.get(2)}")
    println(s"    min / max         : ${priceRow.get(3)} / ${priceRow.get(4)}")

    // --- 7. Records per calendar year, from the DATA ---------------
    // This is what proves the filename-vs-content mismatch and what the
    // chronological train/validation/test split will be based on.
    println("\n  RECORDS PER ACTUAL CALENDAR YEAR")
    val perYear = df
      .filter(col(Canonical.arrivalDate).isNotNull)
      .groupBy(year(col(Canonical.arrivalDate)).as("yr"))
      .agg(count(lit(1)).as("records"))
      .orderBy("yr")
    perYear.collect().foreach { r =>
      println(f"    ${r.getAs[Int]("yr")}%d  ${r.getAs[Long]("records")}%,d")
    }

    // --- persist the profile so the report is reproducible ---------
    quality.coalesce(1).write.mode("overwrite")
      .option("header", "true").csv(s"$OutDir/$name/quality_breakdown")
    perYear.coalesce(1).write.mode("overwrite")
      .option("header", "true").csv(s"$OutDir/$name/records_per_year")

    Seq((name, total, distinctKeys, dupKeys, surplus,
         overview.get(1).toString, overview.get(2).toString, tOverview, tDup))
      .toDF("dataset", "total_records", "distinct_business_keys", "duplicate_keys",
            "surplus_rows", "min_date", "max_date", "overview_seconds", "duplicate_scan_seconds")
      .coalesce(1).write.mode("overwrite")
      .option("header", "true").csv(s"$OutDir/$name/summary")

    df.unpersist()
    println(s"\n  -> written to $OutDir/$name/")
  }

  /** Minimal `--key value` parser. */
  private def parseArgs(args: Array[String]): Map[String, String] =
    args.sliding(2, 2).collect {
      case Array(k, v) if k.startsWith("--") => k.drop(2) -> v
    }.toMap
}
