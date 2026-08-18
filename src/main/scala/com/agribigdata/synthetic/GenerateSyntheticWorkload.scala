package com.agribigdata.synthetic

import com.agribigdata.ingestion.Schemas.Canonical
import com.agribigdata.preprocessing.DataQuality
import com.agribigdata.utils.SparkSetup
import org.apache.hadoop.fs.{FileSystem, Path}
import org.apache.spark.sql.{Column, DataFrame, SparkSession}
import org.apache.spark.sql.functions._

/**
 * PHASE 11b — generate the synthetic scaled workload.
 *
 * PROVENANCE, stated once and enforced everywhere below:
 * every row this job writes carries `data_source = "synthetic_scaled"`.
 * It is NOT government data, NOT AGMARKNET data, and is never presented as
 * such. It exists only to evaluate storage, partitioning, shuffle behaviour
 * and throughput at ~18 GB.
 *
 * HOW IT AVOIDS BEING A COPY.
 * Two things are taken from the real data, and they are different in kind:
 *
 *   1. The DIMENSIONAL SKELETON — which mandi trades which commodity, in
 *      which district, in which year. This is resampled (with replacement)
 *      from the real market structure, because inventing market names would
 *      produce a dataset with no realistic commodity-market relationships,
 *      which is exactly what the brief forbids. Frequency-weighting comes
 *      for free: markets that report often are sampled often.
 *
 *   2. Every MEASURED VALUE — price, spread, arrivals, day-of-month — is
 *      newly generated from the fitted distributions in SynthesisProfile.
 *      No price is copied from any real record.
 *
 * So a generated row is "a plausible new observation from a real market",
 * not a duplicated government record.
 *
 * MEMORY. Nothing is collected to the driver except scalar counts and sizes.
 * The profile tables are small (the largest is ~231k rows) and broadcast;
 * the skeleton is streamed straight from Parquet with column pruning.
 *
 * Run:
 *   sbt "runMain com.agribigdata.synthetic.GenerateSyntheticWorkload --target-gb 7.1"
 */
object GenerateSyntheticWorkload {

  private val Processed = "data/processed"
  val OutDir            = "data/scaled/synthetic_market_workload"

  /** Column marking deliberately injected market anomalies. */
  val InjectedAnomaly = "synthetic_injected_anomaly"

  // --- generation constants, all deliberately conservative -----------
  /** Ordinary day-to-day market noise, as a fraction of price. */
  private val MarketNoise = 0.05
  /** Probability a generated record carries an injected market anomaly. */
  private val AnomalyRate = 0.004

  def main(args: Array[String]): Unit = {
    val opts      = parseArgs(args)
    val targetGb  = opts.get("target-gb").map(_.toDouble).getOrElse(7.1)
    val batchRows = opts.get("batch-rows").map(_.toLong).getOrElse(25000000L)
    val outPath   = opts.getOrElse("out", OutDir)
    val maxBatch  = opts.get("max-batches").map(_.toInt).getOrElse(40)

    val spark = SparkSetup.session("AgriSyntheticGen")
    spark.sparkContext.setLogLevel("WARN")

    try {
      generate(spark, outPath, targetGb, batchRows, maxBatch)
    } finally {
      spark.stop()
    }
  }

  // ==================================================================
  def generate(spark: SparkSession, outPath: String, targetGb: Double,
               batchRows: Long, maxBatches: Int): Unit = {

    val targetBytes = (targetGb * 1024 * 1024 * 1024).toLong

    println("\n" + "=" * 68)
    println("SYNTHETIC WORKLOAD GENERATION")
    println("=" * 68)
    println(f"  target size   : $targetGb%.2f GB ($targetBytes%,d bytes)")
    println(f"  batch size    : $batchRows%,d rows")
    println(s"  output        : $outPath")

    // --- load the learned profile ---------------------------------
    val priceModel = broadcast(spark.read.parquet(s"${SynthesisProfile.ProfileDir}/price_model"))
    val seasonal   = broadcast(spark.read.parquet(s"${SynthesisProfile.ProfileDir}/seasonal"))
    val arrivals   = broadcast(spark.read.parquet(s"${SynthesisProfile.ProfileDir}/arrivals"))
    val qRates     = broadcast(spark.read.parquet(s"${SynthesisProfile.ProfileDir}/quality_rates"))

    // --- the dimensional skeleton ---------------------------------
    // Only the dimension columns are read. Parquet column pruning means the
    // price columns are never even decoded, which is why this stays cheap
    // despite being re-read once per batch.
    val skeleton = SynthesisProfile.Sources
      .map(s => spark.read.parquet(s"$Processed/$s"))
      .reduce(_ unionByName _)
      .select(
        col(Canonical.state), col(Canonical.district), col(Canonical.market),
        col(Canonical.commodity), col(Canonical.variety), col(Canonical.grade),
        col(Canonical.commodityGroup), col(Canonical.sourceDataset),
        col("year"), month(col(Canonical.arrivalDate)).as("month"))
      // A market that only reported in 2005 must not receive 2026 records,
      // so the (year, month) of the sampled row is kept and only the day is
      // regenerated. This preserves both market lifespan and seasonality.
      .filter(col("year").isNotNull && col("month").isNotNull)

    val skeletonCount = skeleton.count()
    println(f"  skeleton rows : $skeletonCount%,d real (state,district,market,commodity,variety,year,month) tuples")

    val fs = FileSystem.get(new java.net.URI(outPath), spark.sparkContext.hadoopConfiguration)
    val out = new Path(outPath)
    // Start clean: this job owns its output directory entirely.
    if (fs.exists(out)) {
      println(s"  clearing existing $outPath")
      fs.delete(out, true)
    }

    var batch        = 0
    var totalRows    = 0L
    var bytesOnDisk  = 0L
    var stop         = false

    while (!stop && batch < maxBatches) {
      batch += 1
      val fraction = batchRows.toDouble / skeletonCount

      val (rowsWritten, tBatch) = SparkSetup.timed(f"batch $batch%02d") {
        val df = buildBatch(spark, skeleton, priceModel, seasonal, arrivals, qRates,
                            fraction, seed = 20260818L + batch * 7919L)
        df.write.mode("append").partitionBy("year").parquet(outPath)
        // Counting the written batch by re-reading would cost a full scan;
        // instead the running total is taken from the output itself below.
        0L
      }

      // Measure ACTUAL bytes on disk via the Hadoop FileSystem API. This is
      // the same call that works against hdfs://, so the measurement does
      // not change when the workload moves to the cluster.
      bytesOnDisk = fs.getContentSummary(out).getLength
      val gb = bytesOnDisk.toDouble / (1024 * 1024 * 1024)
      val pct = bytesOnDisk.toDouble / targetBytes * 100

      println(f"  batch $batch%02d done in $tBatch%6.1f s  ->  $gb%6.3f GB  ($pct%5.1f%% of target)")

      if (bytesOnDisk >= targetBytes) {
        stop = true
        println(f"\n  TARGET REACHED after $batch batches")
      }
    }

    if (!stop) println(f"\n  WARNING: stopped at max-batches=$maxBatches before reaching target")

    // --- final measured facts -------------------------------------
    val written = spark.read.parquet(outPath)
    totalRows = written.count()
    val finalGb = bytesOnDisk.toDouble / (1024 * 1024 * 1024)

    println("\n" + "-" * 68)
    println(f"  synthetic rows written : $totalRows%,d")
    println(f"  synthetic size on disk : $finalGb%.3f GB ($bytesOnDisk%,d bytes)")
    println(f"  bytes per row          : ${bytesOnDisk.toDouble / totalRows}%.2f")
    println(f"  batches                : $batch")
    println("-" * 68)
  }

  // ==================================================================
  /**
   * Build one batch of synthetic records.
   *
   * Everything here is a column expression, so the whole batch is generated
   * inside Spark's engine with no per-row driver work and no UDFs.
   */
  private def buildBatch(spark: SparkSession, skeleton: DataFrame,
                         priceModel: DataFrame, seasonal: DataFrame,
                         arrivals: DataFrame, qRates: DataFrame,
                         fraction: Double, seed: Long): DataFrame = {

    // Sampling WITH replacement: the workload is larger than the real
    // structure, so tuples must be reusable. Each reuse still produces a
    // different date and a different, independently drawn price.
    val base = skeleton.sample(withReplacement = true, fraction = fraction, seed = seed)

    val joined = base
      .join(priceModel,
            Seq(Canonical.sourceDataset, Canonical.commodity, Canonical.market), "left")
      .join(seasonal, Seq(Canonical.commodity, "month"), "left")
      .join(arrivals.withColumnRenamed("n_obs", "arr_n_obs"), Seq(Canonical.commodity), "left")
      .join(qRates, Seq(Canonical.sourceDataset), "left")

    // ---------------------------------------------------------------
    // STAGE 1 — materialise every random draw as a NAMED COLUMN.
    //
    // This staging is not stylistic, it is required for correctness.
    // rand()/randn() are NONDETERMINISTIC expressions. Reusing the same
    // Column object in several output columns does not reuse the value: it
    // plants an independent generator in each one. An earlier version of
    // this method computed min, max and modal from a shared `modalRaw`
    // Column and silently produced a DIFFERENT price in each — 40% of rows
    // came out with min > max, and only 20% were VALID.
    //
    // Naming them here forces one draw per row; every later reference is an
    // AttributeReference to that single value. Spark will not collapse these
    // projections precisely because the expressions are nondeterministic.
    // ---------------------------------------------------------------
    val draws = joined
      .withColumn("_z_price", randn(seed + 1))    // price shock
      .withColumn("_z_noise", randn(seed + 2))    // ordinary market noise
      .withColumn("_u_anom",  rand(seed + 3))     // is this record anomalous?
      .withColumn("_u_dir",   rand(seed + 4))     // spike or drop?
      .withColumn("_u_mag",   rand(seed + 5))     // magnitude
      .withColumn("_u_low",   rand(seed + 6))     // min-price offset
      .withColumn("_u_high",  rand(seed + 7))     // max-price offset
      .withColumn("_u_day",   rand(seed + 8))     // day within month
      .withColumn("_u_qual",  rand(seed + 9))     // data-quality defect draw
      .withColumn("_z_arr",   randn(seed + 10))   // arrivals shock

    // ---------------------------------------------------------------
    // STAGE 2 — the price, from the market's own fitted distribution.
    // ---------------------------------------------------------------
    val priced = draws
      .withColumn("_log_mu",    coalesce(col("log_mu"), lit(math.log(2000.0))))
      .withColumn("_log_sigma", coalesce(col("log_sigma"), lit(0.35)))
      .withColumn("_season",    coalesce(col("seasonal_factor"), lit(1.0)))
      // Log-normal draw at the market's level, adjusted for season, then
      // perturbed by ordinary day-to-day fluctuation.
      .withColumn("_base_price",
        exp(col("_log_mu") + col("_log_sigma") * col("_z_price")) *
          col("_season") * (lit(1.0) + lit(MarketNoise) * col("_z_noise")))
      // Rare injected anomalies, LABELLED. The real data carries no anomaly
      // labels, so this is the only ground truth the anomaly stage can be
      // evaluated against without fabricating accuracy.
      .withColumn(InjectedAnomaly, col("_u_anom") < lit(AnomalyRate))
      .withColumn("_anom_factor",
        when(!col(InjectedAnomaly), lit(1.0))
          // spike: +40%..+150%
          .when(col("_u_dir") < lit(0.5), lit(1.4) + col("_u_mag") * lit(1.1))
          // drop: -65%..-30%
          .otherwise(lit(0.35) + col("_u_mag") * lit(0.35)))
      .withColumn("_modal_raw",
        greatest(round(col("_base_price") * col("_anom_factor"), 2), lit(0.05)))

    // ---------------------------------------------------------------
    // STAGE 3 — min/max placed around the ALREADY-FIXED modal.
    //
    // Built as multiplicative offsets below and above modal, so
    // min <= modal <= max holds by construction rather than by repair.
    // ---------------------------------------------------------------
    val bounded = priced
      .withColumn("_spread", coalesce(col("spread_ratio"), lit(0.10)))
      .withColumn("_min_raw",
        round(col("_modal_raw") * (lit(1.0) - col("_u_low") * col("_spread") * lit(0.5)), 2))
      .withColumn("_max_raw",
        round(col("_modal_raw") * (lit(1.0) + col("_u_high") * col("_spread") * lit(0.5)), 2))

    // ---------------------------------------------------------------
    // STAGE 4 — realistic data-quality defects, at the rates measured in
    // the real data, so the synthetic workload exercises the same cleaning
    // paths. A perfectly clean synthetic set would make the quality stage
    // look unnecessary.
    // ---------------------------------------------------------------
    val defected = bounded
      .withColumn("_r_zero",     coalesce(col("rate_zero_min_max"), lit(0.0)))
      .withColumn("_r_zero_max", coalesce(col("rate_zero_max"), lit(0.0)))
      .withColumn("_r_missing",  coalesce(col("rate_missing_price"), lit(0.0)))
      // Disjoint bands of a single uniform draw, so the three defects can
      // never collide and the observed rates match the learned ones.
      .withColumn("_min_price",
        when(col("_u_qual") < col("_r_zero"), lit(0.0)).otherwise(col("_min_raw")))
      .withColumn("_max_price",
        when(col("_u_qual") < col("_r_zero") + col("_r_zero_max"), lit(0.0))
          .otherwise(col("_max_raw")))
      .withColumn("_modal_price",
        when(col("_u_qual") >= col("_r_zero") + col("_r_zero_max") &&
             col("_u_qual") <  col("_r_zero") + col("_r_zero_max") + col("_r_missing"),
             lit(0.0))
          .otherwise(col("_modal_raw")))

    // ---------------------------------------------------------------
    // STAGE 5 — date and arrivals, then the final canonical projection.
    // ---------------------------------------------------------------
    val dated = defected
      .withColumn("_first_of_month", make_date(col("year"), col("month"), lit(1)))
      .withColumn("_days_in_month", dayofmonth(last_day(col("_first_of_month"))))
      .withColumn("_arrival_date",
        date_add(col("_first_of_month"),
                 floor(col("_u_day") * col("_days_in_month")).cast("int")))
      // Only India Mandi reports quantity; Daily Market Prices has no such
      // column and must stay null rather than gain invented data.
      .withColumn("_arrivals",
        when(col(Canonical.sourceDataset) === "india_mandi" && col("arr_log_mu").isNotNull,
             round(exp(col("arr_log_mu") + col("arr_log_sigma") * col("_z_arr")), 2))
          .otherwise(lit(null).cast("double")))

    val assembled = dated.select(
      col(Canonical.state),
      col(Canonical.district),
      col(Canonical.market),
      col(Canonical.commodity),
      col(Canonical.variety),
      col(Canonical.grade),
      col("_arrival_date").as(Canonical.arrivalDate),
      col("_min_price").as(Canonical.minPrice),
      col("_max_price").as(Canonical.maxPrice),
      col("_modal_price").as(Canonical.modalPrice),
      col("_arrivals").as(Canonical.arrivalsTonnes),
      col(Canonical.commodityGroup),
      col(Canonical.sourceDataset),
      // THE provenance marker. Non-negotiable, on every single row.
      lit("synthetic_scaled").as(Canonical.dataSource),
      col(InjectedAnomaly),
      col("year")
    )

    // Classified with the SAME rule used on real data, so quality
    // comparisons between real and synthetic are like-for-like.
    DataQuality.withQualityFlag(assembled)
  }

  private def parseArgs(args: Array[String]): Map[String, String] =
    args.sliding(2, 2).collect {
      case Array(k, v) if k.startsWith("--") => k.drop(2) -> v
    }.toMap
}
