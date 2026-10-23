package com.agribigdata.streaming

import com.agribigdata.forecast.{Features, ResultsIO}
import com.agribigdata.ingestion.Schemas.{Canonical, Quality}
import com.agribigdata.utils.SparkSetup
import org.apache.spark.sql.{DataFrame, SaveMode, SparkSession}
import org.apache.spark.sql.functions._
import org.apache.spark.sql.streaming.{StreamingQueryListener, Trigger}

import java.nio.file.{Files, Paths}
import java.time.Instant

/**
 * Incremental path: Kafka topic agri.prices.v1 -> bronze / silver / alerts.
 *
 *   sbt "runMain com.agribigdata.streaming.PriceEventStream bootstrap=localhost:9092 root=data/stream runSeconds=120"
 *   (root=hdfs://localhost:9000/agri to write to the HDFS data lake)
 *
 * Two queries share the source:
 *
 *  BRONZE  every Kafka record as received (raw JSON + topic/partition/offset),
 *          file sink with its own checkpoint. Nothing is filtered, so bronze
 *          is the replay/backfill source of truth for the incremental path.
 *
 *  SILVER  parse -> schema check (unparsable or unknown schema_version goes
 *          to quarantine) -> canonicalise with the SAME function as batch ->
 *          watermark on event time -> drop exact re-sends by event_id ->
 *          foreachBatch:
 *            * silver rows written to silver/prices_stream/batch_id=N with
 *              overwrite, so a replayed micro-batch rewrites the same files
 *              (idempotent sink)
 *            * anomaly alerts scored against the batch layer's entity
 *              statistics snapshot (gold/entity_stats)
 *            * per-batch latency/throughput metrics (results/streaming)
 *
 * Delivery semantics (stated precisely in docs/ARCHITECTURE.md): the Kafka
 * source + checkpoint gives exactly-once processing of each offset range into
 * these sinks; the producer is idempotent per session; duplicates that the
 * producer re-sends across sessions or that the source publishes twice are
 * removed by event_id within the watermark. Events older than the watermark
 * (10 days) are kept in bronze but not in silver, and are reconciled by the
 * batch backfill. This is NOT end-to-end exactly-once from the government
 * source to the app.
 */
object PriceEventStream {

  def main(args: Array[String]): Unit = {
    val o = args.flatMap(_.split("=", 2) match { case Array(k, v) => Some(k -> v); case _ => None }).toMap
    val bootstrap = o.getOrElse("bootstrap", "localhost:9092")
    val topic     = o.getOrElse("topic", "agri.prices.v1")
    val root      = o.getOrElse("root", "data/stream")
    val gold      = o.getOrElse("gold", "data/gold")
    val trigger   = o.getOrElse("triggerSeconds", "5").toInt
    val runSec    = o.get("runSeconds").map(_.toLong)
    val starting  = o.getOrElse("startingOffsets", "earliest")
    val watermark = o.getOrElse("watermark", "10 days")
    val maxOffsets = o.getOrElse("maxOffsetsPerTrigger", "50000")
    val metricsDir = ResultsIO.dir(o.getOrElse("metrics", "results/streaming")).toString

    val spark = SparkSetup.session("price-event-stream", Map("spark.sql.shuffle.partitions" -> "8"))
    import spark.implicits._

    spark.streams.addListener(new StreamingQueryListener {
      def onQueryStarted(e: StreamingQueryListener.QueryStartedEvent): Unit = ()
      def onQueryTerminated(e: StreamingQueryListener.QueryTerminatedEvent): Unit =
        e.exception.foreach(x => System.err.println(s"[STREAM] query ${e.id} failed: $x"))
      def onQueryProgress(e: StreamingQueryListener.QueryProgressEvent): Unit =
        ResultsIO.appendLine(s"$metricsDir/progress.jsonl", e.progress.json.replace("\n", " "))
    })

    val kafka = spark.readStream.format("kafka")
      .option("kafka.bootstrap.servers", bootstrap)
      .option("subscribe", topic)
      .option("startingOffsets", starting)
      .option("maxOffsetsPerTrigger", maxOffsets)   // back-pressure: bounded micro-batches
      .option("failOnDataLoss", "true")
      .load()

    val parsed = CanonicalEvent.fromKafkaValue(kafka)

    // ---------------- BRONZE ----------------
    val bronze = parsed.select($"kafka_key", $"raw_json", $"topic", $"partition", $"offset", $"kafka_ts",
        to_date($"kafka_ts").as("ingest_date"))
      .writeStream.format("parquet")
      .option("path", s"$root/bronze/prices_raw")
      .option("checkpointLocation", s"$root/checkpoints/bronze_prices_raw")
      .partitionBy("ingest_date")
      .trigger(Trigger.ProcessingTime(s"$trigger seconds"))
      .queryName("bronze")
      .start()

    // ---------------- SILVER ----------------
    val stats = loadEntityStats(spark, s"$gold/entity_stats")
    val events = parsed.withColumn("parsable", CanonicalEvent.Parsable)

    def processBatch(batch: DataFrame, batchId: Long): Unit = {
      val t0 = System.currentTimeMillis()
      batch.persist()
      val silver = batch.drop("parsable", "usable", "e", "raw_json", "kafka_key", "topic", "dedup_key")
      silver.write.mode(SaveMode.Overwrite).parquet(s"$root/silver/prices_stream/batch_id=$batchId")

      val alerts = Anomaly.score(silver.filter(col(Canonical.qualityFlag) === Quality.Valid), stats)
        .filter($"anomaly_type".isin(Anomaly.AlertTypes: _*))
      val nAlerts = alerts.count()
      if (nAlerts > 0) alerts.withColumn("batch_id", lit(batchId))
        .write.mode(SaveMode.Overwrite).parquet(s"$root/alerts/batch_id=$batchId")

      val now = System.currentTimeMillis()
      val lat = silver.select(
          ((lit(now) - unix_millis($"kafka_ts")) / 1000.0).as("broker_to_sink_s"),
          ((lit(now) - unix_millis(to_timestamp($"ingest_ts"))) / 1000.0).as("producer_to_sink_s"),
          $"quality_flag", $"data_origin")
      val r = lat.agg(count(lit(1)), percentile_approx($"producer_to_sink_s", lit(0.5), lit(1000)),
          percentile_approx($"producer_to_sink_s", lit(0.95), lit(1000)), max($"producer_to_sink_s"),
          percentile_approx($"broker_to_sink_s", lit(0.5), lit(1000)),
          sum(when($"quality_flag" =!= Quality.Valid, 1).otherwise(0)),
          collect_set($"data_origin")).head()
      val n = r.getLong(0)
      if (n > 0) {
        val line = ResultsIO.json(Map(
          "batch_id" -> batchId, "wall_clock" -> Instant.ofEpochMilli(now).toString,
          "rows_silver" -> n, "alerts" -> nAlerts,
          "quality_not_valid" -> Option(r.get(5)).getOrElse(0L),
          "latency_producer_to_sink_p50_s" -> Option(r.get(1)).getOrElse(Double.NaN),
          "latency_producer_to_sink_p95_s" -> Option(r.get(2)).getOrElse(Double.NaN),
          "latency_producer_to_sink_max_s" -> Option(r.get(3)).getOrElse(Double.NaN),
          "latency_broker_to_sink_p50_s" -> Option(r.get(4)).getOrElse(Double.NaN),
          "data_origin" -> r.getSeq[String](6),
          "batch_processing_ms" -> (System.currentTimeMillis() - t0)))
        ResultsIO.appendLine(s"$metricsDir/batches.jsonl", line)
        println(s"[STREAM] $line")
      }
      batch.unpersist()
    }

    val canon = CanonicalEvent.standardize(events.select($"parsable", $"raw_json", $"kafka_key", $"topic",
        $"partition", $"offset", $"kafka_ts", $"e",
        $"e.event_id", $"e.state", $"e.district", $"e.market", $"e.commodity", $"e.variety", $"e.grade",
        $"e.arrival_date", $"e.min_price", $"e.max_price", $"e.modal_price", $"e.source", $"e.ingest_ts",
        $"e.data_origin", $"e.schema_version"))
      // A message is usable only if it parsed, has a known schema version and a
      // valid report date. Everything else is quarantined by a SEPARATE query that
      // has no watermark: unusable rows must never influence event time. (A
      // previous version gave them the broker timestamp, which advanced the
      // watermark to wall-clock time and silently dropped every later replayed
      // event; see docs/RED_TEAM_REVIEW.md RT-01 and StreamingSpec.)
      .withColumn("usable", $"parsable" && col(Canonical.arrivalDate).isNotNull)
      .withColumn("dedup_key", coalesce($"event_id", xxhash64($"raw_json").cast("string")))

    val quarantineQ = canon.filter(!$"usable")
      .select($"raw_json", $"partition", $"offset", $"kafka_ts", to_date($"kafka_ts").as("ingest_date"))
      .writeStream.format("parquet")
      .option("path", s"$root/quarantine/prices")
      .option("checkpointLocation", s"$root/checkpoints/quarantine_prices")
      .partitionBy("ingest_date")
      .trigger(Trigger.ProcessingTime(s"$trigger seconds"))
      .queryName("quarantine")
      .start()

    val silverQ = canon.filter($"usable")
      .withWatermark("event_time", watermark)
      .dropDuplicatesWithinWatermark("dedup_key")
      .writeStream
      .foreachBatch(processBatch _)
      .option("checkpointLocation", s"$root/checkpoints/silver_prices")
      .trigger(Trigger.ProcessingTime(s"$trigger seconds"))
      .queryName("silver")
      .start()

    runSec match {
      case Some(s) =>
        silverQ.awaitTermination(s * 1000)
        bronze.stop(); quarantineQ.stop(); silverQ.stop()
      case None => spark.streams.awaitAnyTermination()
    }
    spark.stop()
  }

  /** Entity statistics snapshot produced by the batch layer (ForecastPublish). Empty if absent. */
  def loadEntityStats(spark: SparkSession, path: String): DataFrame =
    if (Files.exists(Paths.get(path)) || path.startsWith("hdfs://")) {
      try spark.read.parquet(path) catch { case _: Throwable => Anomaly.emptyStats(spark) }
    } else Anomaly.emptyStats(spark)
}

/**
 * Online anomaly rule, identical in batch (AnomalyBenchmark) and streaming.
 *
 *  suspect_data_error  |ln P - mean30| > ln 5   (order-of-magnitude slip)
 *  price_spike/drop    robust z = (ln P - mean30) / max(std30, 0.03) beyond +-3.5
 *                      AND the move exceeds 20% (|ln dev| > ln 1.2)
 *  no_reference        entity has no batch statistics yet
 * mean30/std30 are the entity's trailing 30-day log-price mean and std as of
 * the snapshot; they never include the scored observation.
 */
object Anomaly {
  val ZThreshold = 3.5
  val MinStd = 0.03
  val MinMove = math.log(1.2)
  val DataErrorMove = math.log(5.0)

  def emptyStats(spark: SparkSession): DataFrame = {
    import spark.implicits._
    Seq.empty[(Long, Double, Double, java.sql.Date)].toDF(Features.EntityId, "ref_mean30", "ref_std30", "ref_date")
  }

  val AlertTypes: Seq[String] = Seq("price_spike", "price_drop", "suspect_data_error")

  /** Scores rows that already carry ref_mean30 / ref_std30 (trailing, excluding the scored row). */
  def withScore(df: DataFrame): DataFrame = {
    val dev = log(col(Canonical.modalPrice)) - col("ref_mean30")
    val z = dev / greatest(coalesce(col("ref_std30"), lit(MinStd)), lit(MinStd))
    df.withColumn("log_dev", dev)
      .withColumn("robust_z", z)
      .withColumn("anomaly_type",
        when(col("ref_mean30").isNull, "no_reference")
          .when(abs(dev) > DataErrorMove, "suspect_data_error")
          .when(z > ZThreshold && dev > MinMove, "price_spike")
          .when(z < -ZThreshold && dev < -MinMove, "price_drop")
          .otherwise("none"))
  }

  /** Streaming: reference statistics come from the batch snapshot. */
  def score(df: DataFrame, stats: DataFrame): DataFrame =
    withScore(df.join(broadcast(stats.select(Features.EntityId, "ref_mean30", "ref_std30")), Seq(Features.EntityId), "left"))
}
