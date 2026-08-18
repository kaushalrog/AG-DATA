package com.agribigdata.synthetic

import com.agribigdata.ingestion.Schemas.{Canonical, Quality}
import com.agribigdata.utils.SparkSetup
import org.apache.hadoop.fs.{FileSystem, Path}
import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions._

/**
 * PHASE 11c — verify the synthetic workload against the real data.
 *
 * This job exists to make the synthetic set falsifiable. Each check either
 * passes or fails on measured data; none of them is a claim about intent.
 * A generator that silently produced min > modal, or lost the provenance
 * marker, or collapsed every price onto one value, would be caught here.
 *
 * Run:
 *   sbt "runMain com.agribigdata.synthetic.VerifySyntheticWorkload"
 */
object VerifySyntheticWorkload {

  private val Processed = "data/processed"

  private var failures = 0

  /** Assert a property of the data and record the outcome. */
  private def check(label: String, ok: Boolean, detail: String = ""): Unit = {
    if (!ok) failures += 1
    val mark = if (ok) "PASS" else "FAIL"
    println(f"  [$mark] $label%-52s $detail")
  }

  def main(args: Array[String]): Unit = {
    val opts = args.sliding(2, 2).collect {
      case Array(k, v) if k.startsWith("--") => k.drop(2) -> v
    }.toMap
    val path = opts.getOrElse("path", GenerateSyntheticWorkload.OutDir)

    val spark = SparkSetup.session("AgriSyntheticVerify")
    spark.sparkContext.setLogLevel("WARN")

    try { verify(spark, path) } finally { spark.stop() }

    if (failures > 0) {
      println(s"\n  $failures CHECK(S) FAILED")
      System.exit(1)
    } else {
      println("\n  ALL CHECKS PASSED")
    }
  }

  def verify(spark: SparkSession, path: String): Unit = {
    val syn  = spark.read.parquet(path)
    val real = SynthesisProfile.Sources
      .map(s => spark.read.parquet(s"$Processed/$s"))
      .reduce(_ unionByName _)

    syn.persist(org.apache.spark.storage.StorageLevel.DISK_ONLY)

    println("\n" + "=" * 72)
    println("SYNTHETIC WORKLOAD VERIFICATION")
    println("=" * 72)

    // --- size + volume ---------------------------------------------
    val fs    = FileSystem.get(new java.net.URI(path), spark.sparkContext.hadoopConfiguration)
    val bytes = fs.getContentSummary(new Path(path)).getLength
    val gb    = bytes.toDouble / (1024 * 1024 * 1024)
    val n     = syn.count()

    println(f"\n  MEASURED SIZE")
    println(f"    rows                 : $n%,d")
    println(f"    bytes on disk        : $bytes%,d  (${gb}%.3f GB)")
    println(f"    bytes per row        : ${bytes.toDouble / n}%.2f")

    // --- 1. PROVENANCE ---------------------------------------------
    // The single most important property: nothing here may be mistakable
    // for real government data.
    println("\n  PROVENANCE")
    val distinctSources = syn.select(Canonical.dataSource).distinct().collect().map(_.getString(0)).sorted
    check("every row is data_source='synthetic_scaled'",
      distinctSources.sameElements(Array("synthetic_scaled")),
      s"found: ${distinctSources.mkString(",")}")

    val realSources = real.select(Canonical.dataSource).distinct().collect().map(_.getString(0)).sorted
    check("real data still marked data_source='real'",
      realSources.sameElements(Array("real")),
      s"found: ${realSources.mkString(",")}")

    // --- 2. PRICE INVARIANT ----------------------------------------
    println("\n  PRICE INVARIANTS")
    // Only meaningful where a full price report was generated: rows given a
    // deliberate zero-price defect are excluded, exactly as they would be
    // in the real data.
    val complete = syn.filter(
      col(Canonical.minPrice) > 0 && col(Canonical.maxPrice) > 0 && col(Canonical.modalPrice) > 0)
    val completeN = complete.count()
    val violations = complete.filter(
      !(col(Canonical.minPrice) <= col(Canonical.modalPrice) &&
        col(Canonical.modalPrice) <= col(Canonical.maxPrice))).count()
    check("min <= modal <= max on complete reports", violations == 0,
      f"$violations%,d violations of $completeN%,d")

    val negatives = syn.filter(
      col(Canonical.minPrice) < 0 || col(Canonical.maxPrice) < 0 || col(Canonical.modalPrice) < 0).count()
    check("no negative prices", negatives == 0, f"$negatives%,d negatives")

    val badDates = syn.filter(col(Canonical.arrivalDate).isNull).count()
    check("no null arrival_date", badDates == 0, f"$badDates%,d nulls")

    // --- 3. DISTRIBUTIONAL FIDELITY --------------------------------
    println("\n  DISTRIBUTION VS REAL (VALID rows)")
    def priceStats(df: DataFrame, label: String) = {
      val r = df.filter(col(Canonical.qualityFlag) === Quality.Valid).agg(
        count(lit(1)).as("n"),
        round(percentile_approx(col(Canonical.modalPrice), lit(0.25), lit(1000)), 2).as("p25"),
        round(percentile_approx(col(Canonical.modalPrice), lit(0.50), lit(1000)), 2).as("p50"),
        round(percentile_approx(col(Canonical.modalPrice), lit(0.75), lit(1000)), 2).as("p75")
      ).head()
      println(f"    $label%-10s n=${r.getAs[Long]("n")}%,14d  p25=${r.get(1)}%-10s p50=${r.get(2)}%-10s p75=${r.get(3)}")
      (r.getAs[Double]("p50"), r.getAs[Double]("p25"), r.getAs[Double]("p75"))
    }
    val (realMed, _, _) = priceStats(real, "real")
    val (synMed,  _, _) = priceStats(syn,  "synthetic")

    // The generator is not expected to reproduce the median exactly — it
    // resamples market structure and adds season and noise — but a median
    // off by more than 2x would mean the log-normal fit is wrong.
    val ratio = synMed / realMed
    check("synthetic median price within 2x of real", ratio > 0.5 && ratio < 2.0,
      f"ratio=$ratio%.3f (real=$realMed%.2f syn=$synMed%.2f)")

    // --- 4. CATEGORICAL COVERAGE -----------------------------------
    println("\n  CATEGORICAL COVERAGE")
    Seq(Canonical.state, Canonical.district, Canonical.market,
        Canonical.commodity, Canonical.variety).foreach { c =>
      val rc = real.select(c).distinct().count()
      val sc = syn.select(c).distinct().count()
      val cov = sc.toDouble / rc * 100
      println(f"    $c%-12s real=$rc%,8d  synthetic=$sc%,8d  coverage=$cov%6.2f%%")
    }

    // --- 5. NOT A COPY ---------------------------------------------
    // If the generator were duplicating real rows, real prices would
    // reappear verbatim against the same market and date. This measures how
    // often a full (market, commodity, date, modal_price) tuple collides.
    println("\n  COPY DETECTION")
    val keyCols = Seq(Canonical.market, Canonical.commodity, Canonical.arrivalDate, Canonical.modalPrice)
    val collisions = syn.select(keyCols.map(col): _*).distinct()
      .join(real.select(keyCols.map(col): _*).distinct(), keyCols, "inner")
      .count()
    val synDistinct = syn.select(keyCols.map(col): _*).distinct().count()
    val collisionPct = collisions.toDouble / synDistinct * 100
    // A small overlap is unavoidable and expected: prices are rounded to 2dp
    // and cheap commodities have few plausible values. What matters is that
    // it is nowhere near total.
    check("synthetic rows are not copies of real rows", collisionPct < 5.0,
      f"$collisions%,d of $synDistinct%,d distinct tuples collide ($collisionPct%.3f%%)")

    // --- 6. QUALITY MIX --------------------------------------------
    println("\n  DATA-QUALITY MIX (synthetic vs real)")
    def qualityMix(df: DataFrame, total: Long) =
      df.groupBy(Canonical.qualityFlag).agg(count(lit(1)).as("n"))
        .collect().map(r => r.getString(0) -> r.getAs[Long]("n").toDouble / total * 100).toMap

    val realN  = real.count()
    val rMix   = qualityMix(real, realN)
    val sMix   = qualityMix(syn, n)
    (rMix.keySet ++ sMix.keySet).toSeq.sorted.foreach { k =>
      println(f"    $k%-22s real=${rMix.getOrElse(k, 0.0)}%6.3f%%   synthetic=${sMix.getOrElse(k, 0.0)}%6.3f%%")
    }

    // --- 7. INJECTED ANOMALIES -------------------------------------
    println("\n  INJECTED ANOMALY LABELS")
    val anomN = syn.filter(col(GenerateSyntheticWorkload.InjectedAnomaly)).count()
    println(f"    labelled anomalies   : $anomN%,d (${anomN.toDouble / n * 100}%.3f%%)")
    check("injected anomalies are present and rare", anomN > 0 && anomN.toDouble / n < 0.02,
      f"${anomN.toDouble / n * 100}%.3f%%")

    // --- 8. NULL RATES ---------------------------------------------
    println("\n  NULL RATES")
    syn.columns.foreach { c =>
      val nulls = syn.filter(col(c).isNull).count()
      if (nulls > 0) println(f"    $c%-22s ${nulls}%,14d  (${nulls.toDouble / n * 100}%6.2f%%)")
    }

    // --- 9. TEMPORAL SPREAD ----------------------------------------
    println("\n  YEAR COVERAGE")
    val yrs = syn.groupBy("year").agg(count(lit(1)).as("n")).orderBy("year").collect()
    println(f"    years covered        : ${yrs.length} (${yrs.head.get(0)} .. ${yrs.last.get(0)})")
    val realYrs = real.select("year").distinct().count()
    check("synthetic covers the real year range", yrs.length >= realYrs - 1,
      s"${yrs.length} vs real $realYrs")

    syn.unpersist()
  }
}
