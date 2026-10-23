package com.agribigdata.streaming

import com.agribigdata.forecast.Features
import com.agribigdata.ingestion.Schemas.{Canonical, Quality}
import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.execution.streaming.runtime.MemoryStream
import org.apache.spark.sql.functions._
import org.apache.spark.sql.streaming.Trigger
import org.scalatest.BeforeAndAfterAll
import org.scalatest.funsuite.AnyFunSuite

import java.nio.file.Files

/**
 * Streaming correctness: batch/stream parity of canonicalisation, duplicate
 * and late handling, invalid messages and checkpoint restart. Kafka itself is
 * replaced by MemoryStream so the tests run without a broker; the Kafka wiring
 * is exercised by scripts/streaming_demo.sh against a real broker.
 */
class StreamingSpec extends AnyFunSuite with BeforeAndAfterAll {

  private var spark: SparkSession = _

  override def beforeAll(): Unit = {
    spark = SparkSession.builder().master("local[2]").appName("streaming-spec")
      .config("spark.sql.shuffle.partitions", "2").config("spark.ui.enabled", "false")
      .config("spark.driver.host", "127.0.0.1").getOrCreate()
  }

  override def afterAll(): Unit = if (spark != null) spark.stop()

  private def ev(id: String, market: String, date: String, modal: Double, min: Double = -1, max: Double = -1): String = {
    val mn = if (min < 0) modal * 0.9 else min
    val mx = if (max < 0) modal * 1.1 else max
    s"""{"schema_version":1,"event_id":"$id","state":"Tamil Nadu","district":"Salem","market":"$market","commodity":"Tomato","variety":"Hybrid","grade":"FAQ","arrival_date":"$date","min_price":$mn,"max_price":$mx,"modal_price":$modal,"source":"test","ingest_ts":"2026-04-21T10:00:00.000+00:00","data_origin":"fixture"}"""
  }

  /** The streaming pipeline up to the sink, on a MemoryStream of raw JSON strings. */
  private def pipeline(src: DataFrame, watermark: String = "10 days"): DataFrame = {
    val s = spark
    import s.implicits._
    val kafkaLike = src.select(lit("k").cast("binary").as("key"), $"value".cast("binary").as("value"),
      lit("t").as("topic"), lit(0).as("partition"), lit(0L).as("offset"),
      current_timestamp().as("timestamp"))
    val parsed = CanonicalEvent.fromKafkaValue(kafkaLike).withColumn("parsable", CanonicalEvent.Parsable)
    // mirrors PriceEventStream: only usable rows reach the watermark
    CanonicalEvent.standardize(parsed.select($"parsable", $"raw_json", $"kafka_ts", $"e.*"))
      .filter($"parsable" && col(Canonical.arrivalDate).isNotNull)
      .withColumn("dedup_key", coalesce($"event_id", xxhash64($"raw_json").cast("string")))
      .withWatermark("event_time", watermark)
      .dropDuplicatesWithinWatermark("dedup_key")
  }

  private def run(input: MemoryStream[String], batches: Seq[Seq[String]], ckpt: String, table: String,
                  watermark: String = "10 days"): Array[org.apache.spark.sql.Row] = {
    val q = pipeline(input.toDF(), watermark).writeStream.format("memory").queryName(table)
      .option("checkpointLocation", ckpt).outputMode("append").trigger(Trigger.ProcessingTime(0)).start()
    batches.foreach { b => input.addData(b: _*); q.processAllAvailable() }
    q.stop()
    spark.table(table).collect()
  }

  test("batch and streaming canonicalisation produce identical rows for the same records") {
    val s = spark
    import s.implicits._
    val recs = Seq(("Tamil Nadu", "Salem", "Salem  APMC", "Tomato", "Hybrid", "FAQ", "2026-04-20", 900.0, 1100.0, 1000.0),
      ("Tamil Nadu", "Salem", "Salem", "Tomato", "Hybrid", "Local", "2026-04-21", 0.0, 0.0, 1000.0),
      ("Kerala", " Ernakulam", "Aluva", "Banana", "Nendra Bale", "FAQ", "21/04/2026", 4000.0, 3800.0, 3900.0))
    val batchIn = recs.toDF(Canonical.state, Canonical.district, Canonical.market, Canonical.commodity, Canonical.variety,
      Canonical.grade, Canonical.arrivalDate, Canonical.minPrice, Canonical.maxPrice, Canonical.modalPrice)
    val batch = CanonicalEvent.batchToCanonical(batchIn).select(CanonicalEvent.OutputCols.map(col): _*)

    val json = recs.zipWithIndex.map { case (r, i) =>
      s"""{"schema_version":1,"event_id":"e$i","state":"${r._1}","district":"${r._2}","market":"${r._3}","commodity":"${r._4}","variety":"${r._5}","grade":"${r._6}","arrival_date":"${r._7}","min_price":${r._8},"max_price":${r._9},"modal_price":${r._10}}"""
    }
    val kafkaLike = json.toDF("value").select(lit(null).cast("binary").as("key"), $"value".cast("binary").as("value"),
      lit("t").as("topic"), lit(0).as("partition"), lit(0L).as("offset"), current_timestamp().as("timestamp"))
    val stream = CanonicalEvent.eventsToCanonical(CanonicalEvent.fromKafkaValue(kafkaLike))
      .select(CanonicalEvent.OutputCols.map(col): _*)

    assert(batch.exceptAll(stream).isEmpty && stream.exceptAll(batch).isEmpty)
    val flags = batch.orderBy(Canonical.arrivalDate, Canonical.commodity).select(Canonical.qualityFlag).as[String].collect().toSet
    assert(flags == Set(Quality.Valid, Quality.ZeroMinMax, Quality.MinGreaterThanMax))
    // APMC rename and FAQ->Local relabel resolve to ONE entity
    assert(batch.filter(col(Canonical.commodity) === "Tomato").select(Features.EntityId).distinct().count() == 1)
  }

  test("API spellings (no space before '(', Keralam, APMC suffix) map to the archive entity") {
    val s = spark
    import s.implicits._
    val cols = Seq(Canonical.state, Canonical.district, Canonical.market, Canonical.commodity, Canonical.variety,
      Canonical.grade, Canonical.arrivalDate, Canonical.minPrice, Canonical.maxPrice, Canonical.modalPrice)
    val archive = Seq(("Kerala", "Ernakulam", "Karur (Uzhavar Sandhai )", "Bhindi (Ladies Finger)", "Bhindi", "FAQ", "2026-04-20", 1.0, 3.0, 2.0),
      ("Tamil Nadu", "Salem", "Salem", "Bengal Gram (Gram)(Whole)", "Desi", "FAQ", "2026-04-20", 1.0, 3.0, 2.0)).toDF(cols: _*)
    val api = Seq(("Keralam", "Ernakulam", "Karur(Uzhavar Sandhai ) APMC", "Bhindi(Ladies Finger)", "Bhindi", "Local", "20/04/2026", 1.0, 3.0, 2.0),
      ("Tamil Nadu", "Salem", "Salem APMC", "Bengal Gram(Gram)(Whole)", "Desi", "FAQ", "20/04/2026", 1.0, 3.0, 2.0)).toDF(cols: _*)
    val ids = (df: DataFrame) => CanonicalEvent.batchToCanonical(df).select(Features.EntityId, Canonical.commodity).as[(Long, String)].collect().toSet
    assert(ids(archive) == ids(api))
    assert(ids(api).map(_._2) == Set("Bhindi (Ladies Finger)", "Bengal Gram (Gram)(Whole)"))
  }

  test("exact re-sends are dropped; corrected prices for the same key are kept as revisions") {
    val s = spark
    import s.implicits._
    implicit val ctx = s.sqlContext
    val in = MemoryStream[String]
    val out = run(in, Seq(
      Seq(ev("a", "Salem", "2026-04-20", 1000), ev("a", "Salem", "2026-04-20", 1000)),  // duplicate in batch
      Seq(ev("a", "Salem", "2026-04-20", 1000)),                                          // duplicate across batches
      Seq(ev("a2", "Salem", "2026-04-20", 1050))),                                        // revision
      Files.createTempDirectory("ck").toString, "dedup")
    val ids = out.map(_.getAs[String]("event_id")).sorted.toSeq
    assert(ids == Seq("a", "a2"))
  }

  test("out-of-order events inside the watermark are kept; events older than the watermark are dropped") {
    val s = spark
    import s.implicits._
    implicit val ctx = s.sqlContext
    val in = MemoryStream[String]
    val out = run(in, Seq(
      Seq(ev("n1", "Salem", "2026-04-21", 1000)),
      Seq(ev("o1", "Salem", "2026-04-18", 990)),      // 3 days late: within 10-day watermark
      Seq(ev("n2", "Salem", "2026-05-30", 1200)),     // advances watermark to 2026-05-20
      Seq(ev("late", "Salem", "2026-04-22", 980))),   // older than watermark -> dropped by the stateful op
      Files.createTempDirectory("ck").toString, "late")
    val ids = out.map(_.getAs[String]("event_id")).toSet
    assert(ids.contains("o1") && ids.contains("n2"))
    assert(!ids.contains("late"))
  }

  test("invalid and unknown-schema messages never reach silver and never move the watermark (RT-01)") {
    val s = spark
    import s.implicits._
    implicit val ctx = s.sqlContext
    val in = MemoryStream[String]
    val out = run(in, Seq(
      Seq("""{"schema_version":1,"modal_price":"abc"""",
        """{"schema_version":99,"event_id":"v99","market":"X","commodity":"Y","arrival_date":"2026-04-21"}""",
        "not json at all"),
      // valid April events AFTER a batch of garbage must all arrive
      Seq(ev("a1", "Salem", "2026-04-15", 1000), ev("a2", "Salem", "2026-04-16", 1010)),
      Seq(ev("a3", "Salem", "2026-04-17", 1020))), Files.createTempDirectory("ck").toString, "invalid")
    assert(out.map(_.getAs[String]("event_id")).sorted.toSeq == Seq("a1", "a2", "a3"))
  }

  test("unusable rows are routed to quarantine with their offsets") {
    val s = spark
    import s.implicits._
    val kafkaLike = Seq("not json", ev("ok", "Salem", "2026-04-15", 1000)).toDF("value")
      .select(lit(null).cast("binary").as("key"), $"value".cast("binary").as("value"), lit("t").as("topic"),
        lit(0).as("partition"), lit(7L).as("offset"), current_timestamp().as("timestamp"))
    val parsed = CanonicalEvent.fromKafkaValue(kafkaLike).withColumn("parsable", CanonicalEvent.Parsable)
    val c = CanonicalEvent.standardize(parsed.select($"parsable", $"raw_json", $"offset", $"e.*"))
      .withColumn("usable", $"parsable" && col(Canonical.arrivalDate).isNotNull)
    assert(c.filter(!$"usable").select("raw_json").as[String].collect().toSeq == Seq("not json"))
  }

  test("restarting from a checkpoint does not reprocess committed events (file sink)") {
    val s = spark
    import s.implicits._
    implicit val ctx = s.sqlContext
    val in = MemoryStream[String]
    val ck = Files.createTempDirectory("ck").toString
    val outDir = Files.createTempDirectory("sink").toString
    def runFile(batch: Seq[String]): Unit = {
      val q = pipeline(in.toDF()).select("event_id", "arrival_date").writeStream.format("parquet")
        .option("path", outDir).option("checkpointLocation", ck).trigger(Trigger.ProcessingTime(0)).start()
      in.addData(batch: _*); q.processAllAvailable(); q.stop()
    }
    runFile(Seq(ev("r1", "Salem", "2026-04-20", 1000), ev("r2", "Salem", "2026-04-21", 1010)))
    // same source, same checkpoint, new query: only the new event must be written,
    // and a re-send of r1 must still be recognised as a duplicate (dedup state restored)
    runFile(Seq(ev("r3", "Salem", "2026-04-22", 1020), ev("r1", "Salem", "2026-04-20", 1000)))
    val ids = spark.read.parquet(outDir).select("event_id").as[String].collect().sorted.toSeq
    assert(ids == Seq("r1", "r2", "r3"))
  }

  test("anomaly rule: spike, drop, data error and no reference") {
    val s = spark
    import s.implicits._
    val df = Seq((1L, 1000.0, Some(math.log(1000)), Some(0.05)), (2L, 2000.0, Some(math.log(1000)), Some(0.05)),
      (3L, 500.0, Some(math.log(1000)), Some(0.05)), (4L, 9000.0, Some(math.log(1000)), Some(0.05)),
      (5L, 1000.0, None, None), (6L, 1150.0, Some(math.log(1000)), Some(0.01)))
      .toDF(Features.EntityId, Canonical.modalPrice, "ref_mean30", "ref_std30")
    val t = Anomaly.withScore(df).orderBy(Features.EntityId).select("anomaly_type").as[String].collect().toSeq
    // id 6: z = ln(1.15)/0.03 = 4.7 but the move is < 20% -> not an alert
    assert(t == Seq("none", "price_spike", "price_drop", "suspect_data_error", "no_reference", "none"))
  }
}
