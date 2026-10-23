package com.agribigdata.streaming

import com.agribigdata.forecast.{Features, ResultsIO}
import com.agribigdata.ingestion.Schemas.Canonical
import com.agribigdata.utils.SparkSetup
import org.apache.spark.sql.functions._

import java.nio.file.{Files, Paths}

/**
 * Batch/stream parity on REAL replayed records.
 *
 *   sbt "runMain com.agribigdata.streaming.StreamParityCheck root=data/stream from=2026-04-15 to=2026-04-21"
 *
 * Takes every event that reached the streaming silver sink (de-duplicated by
 * event_id), looks up the same business keys in the batch silver layer,
 * canonicalises those batch rows with the shared CanonicalEvent.standardize,
 * and compares entity_id, normalised market, prices and quality flag.
 * Also compares, in BOTH directions, the event ids the producer actually sent
 * (sent=<ndjson written by the replay CLI>) with the ids that reached silver,
 * so dropped events cannot hide (red-team RT-11).
 *
 * Note: the replay reads the batch silver layer, so the canonicalisation
 * comparison shows that the two code paths agree on the same input; it does
 * not test the raw-CSV readers.
 * Writes results/streaming/parity.json.
 */
object StreamParityCheck {
  def main(args: Array[String]): Unit = {
    val o = args.flatMap(_.split("=", 2) match { case Array(k, v) => Some(k -> v); case _ => None }).toMap
    val root = o.getOrElse("root", "data/stream")
    val from = o.getOrElse("from", "2026-04-15"); val to = o.getOrElse("to", "2026-04-21")
    val silverBatch = o.getOrElse("silver", "data/processed/daily_market_prices")
    val spark = SparkSetup.session("stream-parity")

    val cols = CanonicalEvent.OutputCols.filterNot(c => c == "event_time")
    val stream = spark.read.parquet(s"$root/silver/prices_stream")
      .filter(col("source").startsWith("replay:") && !col("source").contains("+"))   // exclude injected faults
      .dropDuplicates("event_id")
      .select(cols.map(col): _*)
    val batch = CanonicalEvent.batchToCanonical(
        spark.read.parquet(silverBatch).filter(col(Canonical.arrivalDate).between(from, to))
          .select(Seq(Canonical.state, Canonical.district, Canonical.market, Canonical.commodity, Canonical.variety,
            Canonical.grade, Canonical.arrivalDate, Canonical.minPrice, Canonical.maxPrice, Canonical.modalPrice).map(col): _*))
      .select(cols.map(col): _*)
    val keys = Seq(Features.EntityId, Canonical.arrivalDate, Canonical.grade)
    // re-select: the join moves key columns first, and exceptAll compares by position
    val batchForStream = batch.join(stream.select(keys.map(col): _*).distinct(), keys).select(cols.map(col): _*)

    val sentPath = o.get("sent")
    val delivery = sentPath.map { sp =>
      val sent = spark.read.json(sp).filter(col("event_id").isNotNull)
      val expected = sent.select("event_id").distinct()
      val received = spark.read.parquet(s"$root/silver/prices_stream").select("event_id").distinct()
      Map("sent_valid_distinct_ids" -> expected.count(),
        "received_distinct_ids" -> received.count(),
        "sent_but_missing_in_silver" -> expected.except(received).count(),
        "in_silver_but_never_sent" -> received.except(expected).count(),
        "sent_lines_total" -> spark.read.text(sp).count())
    }.getOrElse(Map("note" -> "no sent= file given"))
    val nStream = stream.count(); val nBatch = batchForStream.count()
    val onlyStream = stream.exceptAll(batchForStream).count()
    val onlyBatch = batchForStream.exceptAll(stream).count()
    val res = Map("records_streamed" -> nStream, "batch_records_same_keys" -> nBatch,
      "mismatched_stream_rows" -> onlyStream, "mismatched_batch_rows" -> onlyBatch,
      "parity" -> (onlyStream == 0 && onlyBatch == 0 && nStream == nBatch),
      "delivery" -> delivery,
      "compared_columns" -> cols, "date_range" -> Seq(from, to))
    val js = ResultsIO.json(res)
    ResultsIO.dir("results/streaming")
    Files.writeString(Paths.get("results/streaming/parity.json"), js)
    println(s"[PARITY] $js")
    spark.stop()
  }
}
