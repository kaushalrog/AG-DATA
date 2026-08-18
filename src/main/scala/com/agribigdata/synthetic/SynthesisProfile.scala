package com.agribigdata.synthetic

import com.agribigdata.ingestion.Schemas.{Canonical, Quality}
import com.agribigdata.utils.SparkSetup
import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions._

/**
 * PHASE 11a — learn the statistical shape of the REAL data.
 *
 * This job reads only `data/processed/` and writes only small profile
 * tables. It never writes into the real data and never generates a row.
 *
 * What it deliberately does NOT do: copy prices, or memorise individual
 * records. Every table below is an AGGREGATE — parameters of a distribution,
 * not the observations themselves. The generator later samples from these
 * parameters, which is what makes the output synthetic rather than a
 * reshuffled copy of government data.
 *
 * Run:
 *   sbt "runMain com.agribigdata.synthetic.SynthesisProfile"
 */
object SynthesisProfile {

  val ProfileDir = "results/synthesis_profile"
  private val Processed = "data/processed"

  /** Sources whose real distributions are modelled. */
  val Sources = Seq("daily_market_prices", "india_mandi")

  def main(args: Array[String]): Unit = {
    val spark = SparkSetup.session("AgriSynthesisProfile")
    spark.sparkContext.setLogLevel("WARN")
    try { build(spark) } finally { spark.stop() }
  }

  def build(spark: SparkSession): Unit = {
    import spark.implicits._

    val real = Sources
      .map(s => spark.read.parquet(s"$Processed/$s"))
      .reduce(_ unionByName _)

    // Distributions are learned from VALID rows only. Including partial
    // reports (min=0, max=0) would drag every learned mean toward zero and
    // the generator would then faithfully reproduce a reporting defect as
    // if it were market behaviour.
    val valid = real.filter(col(Canonical.qualityFlag) === Quality.Valid)
    valid.persist(org.apache.spark.storage.StorageLevel.DISK_ONLY)

    // -------------------------------------------------------------
    // 1. PRICE MODEL, per (source, commodity, market)
    //
    // Prices are modelled log-normally. Agricultural prices are strictly
    // positive and right-skewed — a normal model would generate negative
    // prices and understate the upper tail. Fitting the mean and stddev of
    // log(price) and exponentiating on the way out reproduces both
    // properties for free.
    //
    // Learned per commodity AND market because the same commodity trades at
    // materially different levels in different mandis; a commodity-level
    // model alone would erase that structure.
    // -------------------------------------------------------------
    val priceModel = valid
      .withColumn("log_modal", log(col(Canonical.modalPrice)))
      .groupBy(Canonical.sourceDataset, Canonical.commodity, Canonical.market)
      .agg(
        avg("log_modal").as("log_mu"),
        // A market with one observation has no dispersion to measure.
        // coalesce to a modest default so the generator still varies it.
        coalesce(stddev("log_modal"), lit(0.25)).as("log_sigma"),
        // Observed relative spread, used to place min/max around modal.
        avg(
          when(col(Canonical.modalPrice) > 0,
            (col(Canonical.maxPrice) - col(Canonical.minPrice)) / col(Canonical.modalPrice))
        ).as("spread_ratio"),
        count(lit(1)).as("n_obs")
      )
      // Clamp pathological fits: a near-zero sigma makes every generated
      // price identical, a huge sigma makes the output meaningless.
      .withColumn("log_sigma", least(greatest(col("log_sigma"), lit(0.05)), lit(1.5)))
      .withColumn("spread_ratio",
        least(greatest(coalesce(col("spread_ratio"), lit(0.10)), lit(0.0)), lit(2.0)))

    // -------------------------------------------------------------
    // 2. SEASONALITY, per (commodity, month)
    //
    // Expressed as a multiplier on the commodity's own annual median, so it
    // is scale-free and can be applied to any market's price level.
    // -------------------------------------------------------------
    val commodityMedian = valid
      .groupBy(Canonical.commodity)
      .agg(percentile_approx(col(Canonical.modalPrice), lit(0.5), lit(1000)).as("annual_median"))

    val seasonal = valid
      .withColumn("month", month(col(Canonical.arrivalDate)))
      .groupBy(Canonical.commodity, "month")
      .agg(
        percentile_approx(col(Canonical.modalPrice), lit(0.5), lit(1000)).as("month_median"),
        count(lit(1)).as("n_obs"))
      .join(commodityMedian, Seq(Canonical.commodity), "inner")
      .withColumn("seasonal_factor",
        when(col("annual_median") > 0, col("month_median") / col("annual_median")).otherwise(1.0))
      // Keep the factor in a believable band. Genuine seasonal swings are
      // large but a 10x monthly median is a sign of sparse data, not season.
      .withColumn("seasonal_factor",
        least(greatest(col("seasonal_factor"), lit(0.4)), lit(2.5)))
      .select(Canonical.commodity, "month", "seasonal_factor", "n_obs")

    // -------------------------------------------------------------
    // 3. ARRIVALS, per commodity (India Mandi only — the only source
    //    that reports quantity). Log-normal for the same reasons as price.
    // -------------------------------------------------------------
    val arrivals = valid
      .filter(col(Canonical.arrivalsTonnes).isNotNull && col(Canonical.arrivalsTonnes) > 0)
      .withColumn("log_arr", log(col(Canonical.arrivalsTonnes)))
      .groupBy(Canonical.commodity)
      .agg(
        avg("log_arr").as("arr_log_mu"),
        coalesce(stddev("log_arr"), lit(0.5)).as("arr_log_sigma"),
        count(lit(1)).as("n_obs"))
      .withColumn("arr_log_sigma", least(greatest(col("arr_log_sigma"), lit(0.1)), lit(2.0)))

    // -------------------------------------------------------------
    // 4. DATA-QUALITY DEFECT RATES, per source.
    //
    // Real data is imperfect in specific, measurable ways. The generator
    // reproduces those rates so that the synthetic workload exercises the
    // same cleaning paths — a perfectly clean synthetic set would make the
    // quality stage look unnecessary.
    // -------------------------------------------------------------
    val qualityRates = real
      .groupBy(Canonical.sourceDataset)
      .agg(
        count(lit(1)).as("n_total"),
        avg(when(col(Canonical.qualityFlag) === Quality.ZeroMinMax, 1.0).otherwise(0.0)).as("rate_zero_min_max"),
        avg(when(col(Canonical.qualityFlag) === Quality.ZeroMax, 1.0).otherwise(0.0)).as("rate_zero_max"),
        avg(when(col(Canonical.qualityFlag) === Quality.MissingPrice, 1.0).otherwise(0.0)).as("rate_missing_price"),
        avg(when(col(Canonical.qualityFlag) === Quality.ModalOutsideRange, 1.0).otherwise(0.0)).as("rate_modal_outside")
      )

    // -------------------------------------------------------------
    // 5. TEMPORAL SHAPE, per (source, year) — record share per year.
    //    Recorded for the report; the generator preserves the real
    //    year/month of each sampled market so that a mandi never receives
    //    records in a year it did not operate.
    // -------------------------------------------------------------
    val yearShape = real
      .groupBy(Canonical.sourceDataset, "year")
      .agg(count(lit(1)).as("n_records"))

    def write(df: DataFrame, name: String): Unit = {
      df.coalesce(4).write.mode("overwrite").parquet(s"$ProfileDir/$name")
      println(f"  wrote $name%-22s rows=${df.count()}%,d")
    }

    println("\n" + "=" * 68)
    println("SYNTHESIS PROFILE (learned from real VALID rows only)")
    println("=" * 68)

    val (_, t) = SparkSetup.timed("build synthesis profile") {
      write(priceModel,   "price_model")
      write(seasonal,     "seasonal")
      write(arrivals,     "arrivals")
      write(qualityRates, "quality_rates")
      write(yearShape,    "year_shape")
    }

    println("\n  QUALITY DEFECT RATES LEARNED FROM REAL DATA")
    qualityRates.collect().foreach { r =>
      println(f"    ${r.getString(0)}%-22s zero_min_max=${r.getAs[Double]("rate_zero_min_max")}%.5f  " +
              f"zero_max=${r.getAs[Double]("rate_zero_max")}%.5f  missing=${r.getAs[Double]("rate_missing_price")}%.5f")
    }

    println("\n  SEASONALITY EXTREMES (sanity check)")
    seasonal.filter(col("n_obs") > 5000)
      .orderBy(desc("seasonal_factor")).limit(5)
      .collect().foreach(r =>
        println(f"    ${r.getString(0)}%-30s month=${r.getInt(1)}%2d  factor=${r.getAs[Double]("seasonal_factor")}%.3f"))

    valid.unpersist()
    println(s"\n  -> profile written to $ProfileDir/  ($t%.1f s)")
  }
}
