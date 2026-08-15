package com.agribigdata.preprocessing

import com.agribigdata.ingestion.Readers
import com.agribigdata.ingestion.Schemas.{Canonical, Quality}
import com.agribigdata.utils.SparkSetup
import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions._

/**
 * PHASE 5–6 — preprocessing to the canonical, partitioned Parquet dataset.
 *
 *   raw CSV
 *     -> canonical schema      (Readers)
 *     -> quality classification (DataQuality)
 *     -> deduplication          (Deduplicate)
 *     -> per-commodity outlier flagging (OutlierTreatment)
 *     -> Parquet, partitioned by year
 *
 * Raw data is never modified; everything is written to data/processed/.
 *
 * Run:
 *   sbt "runMain com.agribigdata.preprocessing.PreprocessDatasets"
 *   sbt "runMain com.agribigdata.preprocessing.PreprocessDatasets --source daily --years 2025"
 *   sbt "runMain com.agribigdata.preprocessing.PreprocessDatasets --out data/processed_test"
 */
object PreprocessDatasets {

  private val RawDaily = "data/raw/Daily_Market_Prices_2001_2026/csv"
  private val RawMandi = "data/raw/india_mandi"
  private val StatsDir = "results/preprocessing"

  /** Year column is derived, not read — filenames are not trusted. */
  val YearCol = "year"

  def main(args: Array[String]): Unit = {
    val opts    = parseArgs(args)
    val source  = opts.getOrElse("source", "all")
    val outRoot = opts.getOrElse("out", "data/processed")
    val years   = opts.get("years")

    val spark = SparkSetup.session("AgriPreprocess")
    spark.sparkContext.setLogLevel("WARN")

    try {
      if (source == "all" || source == "daily") {
        val path = years match {
          case Some(y) => y.split(",").map(v => s"$RawDaily/${v.trim}.csv").mkString(",")
          case None    => s"$RawDaily/*.csv"
        }
        run(spark, "daily_market_prices", Readers.dailyMarketPrices(spark, path), outRoot)
      }

      if (source == "all" || source == "mandi") {
        run(spark, "india_mandi", Readers.indiaMandi(spark, s"$RawMandi/*.csv"), outRoot)
      }
    } finally {
      spark.stop()
    }
  }

  // -----------------------------------------------------------------
  private def run(spark: SparkSession, name: String, raw: DataFrame, outRoot: String): Unit = {
    import spark.implicits._

    println("\n" + "=" * 68)
    println(s"PREPROCESSING: $name")
    println("=" * 68)

    val outPath = s"$outRoot/$name"

    // --- 1. Quality classification ---------------------------------
    val flagged = DataQuality.withQualityFlag(raw)

    // --- 2. Learn outlier bounds -----------------------------------
    // Deliberately learned BEFORE deduplication. Bounds are a property of
    // the price distribution of a commodity, and duplicate reports do not
    // meaningfully bias a quartile (they are 0.45% and 0.34% of rows).
    // Doing it here means the (expensive) dedup shuffle is not on the
    // critical path of this aggregation.
    val (bounds, tBounds) = SparkSetup.timed(s"$name: learn outlier bounds") {
      val b = OutlierTreatment.learnBounds(flagged)
      // Small (~387 rows) and read twice — once for stats, once for the
      // broadcast join — so materialise it rather than recompute.
      b.cache()
      b.count()
      b
    }

    // --- 3. Deduplicate --------------------------------------------
    val deduped = Deduplicate.byBusinessKey(flagged)

    // --- 4. Flag outliers + derive partition column ----------------
    val processed = OutlierTreatment
      .flag(spark, deduped, bounds)
      .withColumn(YearCol, year(col(Canonical.arrivalDate)))

    // --- 5. Write partitioned Parquet ------------------------------
    // Partitioned by year because every downstream stage is time-sliced:
    // the chronological train/validation/test split, the per-year
    // scalability sweeps, and the 2026 streaming replay all become
    // partition pruning instead of a full scan.
    //
    // Rows whose date could not be parsed would land in a
    // __HIVE_DEFAULT_PARTITION__ directory and silently pollute every
    // year-filtered read, so they are routed to a separate path.
    val datedRows   = processed.filter(col(Canonical.arrivalDate).isNotNull)
    val undatedRows = processed.filter(col(Canonical.arrivalDate).isNull)

    val (_, tWrite) = SparkSetup.timed(s"$name: write parquet") {
      datedRows.write
        .mode("overwrite")
        .partitionBy(YearCol)
        .parquet(outPath)
    }

    val undatedCount = undatedRows.count()
    if (undatedCount > 0) {
      undatedRows.write.mode("overwrite").parquet(s"$outRoot/${name}_undated")
      println(f"  NOTE: $undatedCount%,d undated rows quarantined to ${name}_undated")
    }

    // --- 6. Verify what was actually written -----------------------
    // Read the output back rather than trusting the in-memory plan. A
    // count on the source DataFrame would re-run the whole pipeline and
    // could differ from what landed on disk.
    val written = spark.read.parquet(outPath)

    val summary = written.agg(
      count(lit(1)).as("records_written"),
      sum(when(col(Canonical.qualityFlag) === Quality.Valid, 1L).otherwise(0L)).as("valid"),
      sum(when(col(OutlierTreatment.PriceOutlier), 1L).otherwise(0L)).as("outliers"),
      min(col(Canonical.arrivalDate)).as("min_date"),
      max(col(Canonical.arrivalDate)).as("max_date")
    ).head()

    val written_n = summary.getAs[Long]("records_written")
    val rawCount  = raw.count()

    println(f"\n  raw records in     : $rawCount%,d")
    println(f"  records written    : $written_n%,d")
    println(f"  removed as duplicate: ${rawCount - written_n - undatedCount}%,d")
    println(f"  VALID              : ${summary.getAs[Long]("valid")}%,d")
    println(f"  flagged outlier    : ${summary.getAs[Long]("outliers")}%,d")
    println(s"  date range         : ${summary.get(3)} .. ${summary.get(4)}")

    println("\n  QUALITY AFTER PREPROCESSING")
    val qualityAfter = written
      .groupBy(Canonical.qualityFlag)
      .agg(count(lit(1)).as("records"))
      .orderBy(desc("records"))
    qualityAfter.collect().foreach { r =>
      println(f"    ${r.getString(0)}%-22s ${r.getAs[Long]("records")}%,14d")
    }

    println("\n  TOP COMMODITIES BY OUTLIER RATE (min 10k records)")
    written
      .groupBy(Canonical.commodity)
      .agg(
        count(lit(1)).as("n"),
        sum(when(col(OutlierTreatment.PriceOutlier), 1L).otherwise(0L)).as("outliers"))
      .filter(col("n") >= 10000)
      .withColumn("rate_pct", round(col("outliers") * 100.0 / col("n"), 3))
      .orderBy(desc("rate_pct"))
      .limit(10)
      .collect()
      .foreach { r =>
        println(f"    ${r.getString(0)}%-38s ${r.getAs[Long]("outliers")}%8d / ${r.getAs[Long]("n")}%10d  ${r.getAs[Double]("rate_pct")}%6.3f%%")
      }

    // --- 7. Persist run statistics ---------------------------------
    bounds.coalesce(1).write.mode("overwrite")
      .option("header", "true").csv(s"$StatsDir/$name/commodity_price_bounds")

    qualityAfter.coalesce(1).write.mode("overwrite")
      .option("header", "true").csv(s"$StatsDir/$name/quality_after")

    Seq((name, rawCount, written_n, rawCount - written_n - undatedCount, undatedCount,
         summary.getAs[Long]("valid"), summary.getAs[Long]("outliers"),
         summary.get(3).toString, summary.get(4).toString, tBounds, tWrite))
      .toDF("dataset", "raw_records", "records_written", "duplicates_removed",
            "undated_quarantined", "valid_records", "outliers_flagged",
            "min_date", "max_date", "learn_bounds_seconds", "write_seconds")
      .coalesce(1).write.mode("overwrite")
      .option("header", "true").csv(s"$StatsDir/$name/summary")

    bounds.unpersist()
    println(s"\n  -> parquet : $outPath (partitioned by $YearCol)")
    println(s"  -> stats   : $StatsDir/$name/")
  }

  private def parseArgs(args: Array[String]): Map[String, String] =
    args.sliding(2, 2).collect {
      case Array(k, v) if k.startsWith("--") => k.drop(2) -> v
    }.toMap
}
