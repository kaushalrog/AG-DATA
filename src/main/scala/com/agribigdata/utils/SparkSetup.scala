package com.agribigdata.utils

import org.apache.spark.sql.SparkSession

/**
 * Single place where the SparkSession is built.
 *
 * The tuning here is deliberate and sized for the machine this project is
 * developed on (Apple Silicon MacBook Air, 10 cores, 16 GB RAM) while
 * staying valid on a real cluster: every setting below is either a
 * cluster-neutral correctness choice or is read from the environment so
 * that `spark-submit` can override it.
 */
object SparkSetup {

  /**
   * @param appName  shows up in the Spark UI and event logs
   * @param extra    per-job overrides, applied last so a job can always win
   */
  def session(appName: String, extra: Map[String, String] = Map.empty): SparkSession = {

    val builder = SparkSession
      .builder()
      .appName(appName)

    // Only force local[*] when nothing else set a master. Under
    // spark-submit the master arrives from the command line and we must
    // not clobber it, or the job would silently stop being distributed.
    if (sys.env.get("SPARK_MASTER").isEmpty && System.getProperty("spark.master") == null) {
      builder.master("local[*]")
    }

    builder
      // --- Shuffle sizing -------------------------------------------
      // Spark's default of 200 shuffle partitions is tuned for a cluster.
      // On 10 local cores it produces 200 tiny tasks whose scheduling
      // overhead dominates. Adaptive Query Execution then coalesces
      // partitions at runtime based on actual shuffle output size, which
      // is strictly better than any static guess.
      .config("spark.sql.adaptive.enabled", "true")
      .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
      .config("spark.sql.adaptive.skewJoin.enabled", "true")
      .config("spark.sql.shuffle.partitions", sys.env.getOrElse("AGRI_SHUFFLE_PARTITIONS", "32"))

      // --- Memory safety --------------------------------------------
      // The driver runs in the same JVM under local[*]. Keeping the
      // broadcast threshold modest avoids the driver pulling a large
      // dimension table into heap.
      .config("spark.sql.autoBroadcastJoinThreshold", (32 * 1024 * 1024).toString)
      // Spill sooner rather than OOM: this project has already hit a
      // Java heap OOM once (whole-row distinct on 5.8M rows), and on a
      // 16 GB laptop a spill to disk is always preferable to a crash.
      .config("spark.memory.fraction", "0.6")

      // --- Output format --------------------------------------------
      .config("spark.sql.parquet.compression.codec", "snappy")
      // Without this, Spark writes dates/timestamps in a legacy calendar
      // and refuses to read pre-1582 dates written by other tools.
      .config("spark.sql.parquet.datetimeRebaseModeInWrite", "CORRECTED")
      .config("spark.sql.parquet.datetimeRebaseModeInRead", "CORRECTED")

      // --- Date parsing ---------------------------------------------
      // CORRECTED (not LEGACY/EXCEPTION) so that an unparseable date
      // becomes null rather than throwing and killing the whole job.
      // Null dates are then caught by the data-quality layer, which is
      // where malformed input belongs.
      .config("spark.sql.legacy.timeParserPolicy", "CORRECTED")

      // The hostname on this machine resolves to a loopback address,
      // which makes Spark guess at the bind address. Pinning it removes
      // the warning and keeps local runs deterministic.
      .config("spark.driver.host", sys.env.getOrElse("SPARK_LOCAL_IP", "127.0.0.1"))

      .config(extra)
      .getOrCreate()
  }

  /** Wall-clock timer used by every benchmark in this project. */
  def timed[T](label: String)(body: => T): (T, Double) = {
    val t0  = System.nanoTime()
    val out = body
    val sec = (System.nanoTime() - t0) / 1e9
    println(f"[TIMING] $label%-50s ${sec}%8.2f s")
    (out, sec)
  }
}
