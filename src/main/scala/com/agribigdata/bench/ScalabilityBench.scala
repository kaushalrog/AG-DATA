package com.agribigdata.bench

import com.agribigdata.forecast.{Features, ResultsIO}
import com.agribigdata.ingestion.Schemas.{Canonical, Quality}
import com.agribigdata.utils.SparkSetup
import org.apache.spark.scheduler.{SparkListener, SparkListenerTaskEnd}
import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions._

import java.time.Instant
import java.util.concurrent.atomic.AtomicLong

/**
 * Scalability measurements, separate from accuracy.
 *
 *   sbt "runMain com.agribigdata.bench.ScalabilityBench mode=size"        # data-size sweep
 *   sbt "runMain com.agribigdata.bench.ScalabilityBench mode=partitions"  # shuffle-partition sweep
 *   AGRI_MASTER=local[2] sbt "runMain ... mode=cores"                   # run once per core count
 *
 * Two workloads on the REAL silver layer (synthetic only when asked, labelled):
 *   W1 aggregate: quality filter -> per (commodity, state, month) aggregates   (one shuffle)
 *   W2 features:  harmonise -> per-entity windows (lags, 7/30/90-day stats)  (sort-heavy)
 * Each run records wall time, rows/s, shuffle read/write bytes, spill and
 * task counts collected by a SparkListener, appended to
 * results/scalability/runs.jsonl with the master URL and core count.
 */
object ScalabilityBench {

  final class Metrics extends SparkListener {
    val shuffleWrite, shuffleRead, memSpill, diskSpill, tasks, inputBytes, peakMem = new AtomicLong()
    override def onTaskEnd(e: SparkListenerTaskEnd): Unit = Option(e.taskMetrics).foreach { m =>
      shuffleWrite.addAndGet(m.shuffleWriteMetrics.bytesWritten)
      shuffleRead.addAndGet(m.shuffleReadMetrics.totalBytesRead)
      memSpill.addAndGet(m.memoryBytesSpilled); diskSpill.addAndGet(m.diskBytesSpilled)
      inputBytes.addAndGet(m.inputMetrics.bytesRead)
      peakMem.accumulateAndGet(m.peakExecutionMemory, math.max)
      tasks.incrementAndGet()
    }
    def reset(): Unit = Seq(shuffleWrite, shuffleRead, memSpill, diskSpill, tasks, inputBytes, peakMem).foreach(_.set(0))
  }

  def w1(df: DataFrame): DataFrame =
    df.filter(col(Canonical.qualityFlag) === Quality.Valid)
      .groupBy(col(Canonical.commodity), col(Canonical.state), date_trunc("month", col(Canonical.arrivalDate)).as("month"))
      .agg(count(lit(1)).as("n"), avg(Canonical.modalPrice).as("mean_modal"),
        percentile_approx(col(Canonical.modalPrice), lit(0.5), lit(1000)).as("median_modal"))

  def w2(df: DataFrame): DataFrame = {
    val base = df.filter(col(Canonical.qualityFlag) === Quality.Valid && col(Canonical.modalPrice) > 0)
      .select((Features.EntityCols ++ Seq(Canonical.grade, Canonical.arrivalDate, Canonical.minPrice, Canonical.maxPrice,
        Canonical.modalPrice)).map(col): _*)
    Features.withEntityFeatures(Features.withKeys(base))
      .select(Features.EntityId, "day", "ret1", "dev7", "dev30", "std30", "cnt90")
  }

  def run(spark: SparkSession, m: Metrics, name: String, df: DataFrame, rows: Long, extra: Map[String, Any]): Unit = {
    val wl = if (name == "W1") w1(df) else w2(df)
    m.reset()
    val t0 = System.nanoTime()
    // noop sink: forces full execution without measuring local disk write speed
    wl.write.format("noop").mode("overwrite").save()
    val sec = (System.nanoTime() - t0) / 1e9
    val rec = Map("ts" -> Instant.now().toString, "workload" -> name, "rows_in" -> rows, "seconds" -> sec,
      "rows_per_s" -> rows / sec, "master" -> spark.sparkContext.master, "cores" -> spark.sparkContext.defaultParallelism,
      "shuffle_partitions" -> spark.conf.get("spark.sql.shuffle.partitions"), "aqe" -> spark.conf.get("spark.sql.adaptive.enabled"),
      "tasks" -> m.tasks.get, "input_bytes" -> m.inputBytes.get, "shuffle_write_bytes" -> m.shuffleWrite.get,
      "shuffle_read_bytes" -> m.shuffleRead.get, "memory_spill_bytes" -> m.memSpill.get, "disk_spill_bytes" -> m.diskSpill.get,
      "peak_task_execution_memory_bytes" -> m.peakMem.get,
      "driver_max_heap_bytes" -> Runtime.getRuntime.maxMemory) ++ extra
    val js = ResultsIO.json(rec)
    ResultsIO.appendLine("results/scalability/runs.jsonl", js)
    println(s"[SCALE] $js")
  }

  def main(args: Array[String]): Unit = {
    val o = args.flatMap(_.split("=", 2) match { case Array(k, v) => Some(k -> v); case _ => None }).toMap
    val mode = o.getOrElse("mode", "size")
    val silver = o.getOrElse("silver", sys.env.getOrElse("AGRI_SILVER_DAILY", "data/processed/daily_market_prices"))
    val extraConf = sys.env.get("AGRI_MASTER").map(mm => Map("spark.master" -> mm)).getOrElse(Map.empty)
    if (extraConf.nonEmpty) System.setProperty("spark.master", extraConf("spark.master"))
    val spark = SparkSetup.session(s"scalability-$mode", extraConf)
    val m = new Metrics; spark.sparkContext.addSparkListener(m)
    val all = spark.read.parquet(silver)

    def slice(from: Int, to: Int): (DataFrame, Long) = {
      val d = all.filter(col("year").between(from, to)); (d, d.count())
    }
    mode match {
      case "size" =>
        for ((from, to) <- Seq((2025, 2025), (2024, 2025), (2022, 2025), (2018, 2025), (2010, 2025), (2001, 2026))) {
          val (d, n) = slice(from, to)
          for (w <- Seq("W1", "W2")) run(spark, m, w, d, n, Map("years" -> s"$from-$to", "data" -> "real"))
        }
      case "partitions" =>
        val (d, n) = slice(2018, 2025)
        for (p <- Seq("8", "32", "128", "512")) {
          spark.conf.set("spark.sql.shuffle.partitions", p)
          for (aqe <- Seq("true", "false")) {
            spark.conf.set("spark.sql.adaptive.enabled", aqe)
            run(spark, m, "W2", d, n, Map("years" -> "2018-2025", "data" -> "real"))
          }
        }
      case "cores" =>
        val Array(f, t) = o.getOrElse("years", "2018-2025").split("-").map(_.toInt)
        val (d, n) = slice(f, t)
        for (w <- Seq("W1", "W2")) run(spark, m, w, d, n, Map("years" -> s"$f-$t", "data" -> "real",
          "storage" -> (if (silver.startsWith("hdfs://")) "hdfs" else "local")))
      case "synthetic" =>
        val syn = spark.read.parquet(o.getOrElse("synthetic", "data/scaled/synthetic_market_workload"))
        val n = syn.count()
        run(spark, m, "W1", syn, n, Map("data" -> "synthetic_scaled"))
    }
    spark.stop()
  }
}
