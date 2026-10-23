package com.agribigdata.streaming

import com.agribigdata.forecast.Features
import com.agribigdata.ingestion.Schemas.Canonical
import com.agribigdata.preprocessing.DataQuality
import org.apache.spark.sql.{Column, DataFrame}
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._

/**
 * The single canonicalisation used by BOTH the streaming path (Kafka JSON
 * events) and the batch path (archived CSV/Parquet rows). StreamParitySpec
 * pushes the same records through both entry points and requires identical
 * output, so the two paths cannot drift apart silently.
 */
object CanonicalEvent {

  /** JSON contract of topic agri.prices.v1 (schema_version 1, see docs/DATA_DICTIONARY.md). */
  val EventSchema: StructType = StructType(Seq(
    StructField("schema_version", IntegerType),
    StructField("event_id", StringType),
    StructField("state", StringType),
    StructField("district", StringType),
    StructField("market", StringType),
    StructField("commodity", StringType),
    StructField("variety", StringType),
    StructField("grade", StringType),
    StructField("arrival_date", StringType),
    StructField("min_price", DoubleType),
    StructField("max_price", DoubleType),
    StructField("modal_price", DoubleType),
    StructField("price_unit", StringType),
    StructField("source", StringType),
    StructField("source_record_ts", StringType),
    StructField("ingest_ts", StringType),
    StructField("data_origin", StringType),
    StructField("quality_flag", StringType)))

  val SupportedSchemaVersions: Seq[Int] = Seq(1)

  private def clean(c: Column): Column = trim(regexp_replace(c, "\\s+", " "))

  /**
   * Shared standardisation: whitespace, date parsing, quality verdict,
   * entity id and event time. Input must carry the canonical column names.
   */
  def standardize(df: DataFrame): DataFrame = {
    val d = Seq(Canonical.state, Canonical.district, Canonical.market, Canonical.commodity, Canonical.variety, Canonical.grade)
      .foldLeft(df)((acc, c) => acc.withColumn(c, coalesce(clean(col(c)), lit(""))))
    Features.normalizeIdentifiers(d)
      .withColumn(Canonical.arrivalDate, coalesce(
        try_to_date(col(Canonical.arrivalDate).cast("string"), "yyyy-MM-dd"),
        try_to_date(col(Canonical.arrivalDate).cast("string"), "dd/MM/yyyy"),
        try_to_date(col(Canonical.arrivalDate).cast("string"), "dd MMM yyyy")))
      .withColumn(Canonical.qualityFlag, DataQuality.classify)
      .withColumn(Features.EntityId, Features.entityIdCol)
      .withColumn("event_time", col(Canonical.arrivalDate).cast("timestamp"))
      .withColumn("price_hash", xxhash64(col(Canonical.minPrice), col(Canonical.maxPrice), col(Canonical.modalPrice)))
  }

  val OutputCols: Seq[String] = Seq(Features.EntityId) ++ Features.EntityCols ++ Seq(Canonical.grade, "market_raw", Canonical.arrivalDate,
    Canonical.minPrice, Canonical.maxPrice, Canonical.modalPrice, Canonical.qualityFlag, "event_time", "price_hash")

  /** Streaming entry: Kafka value bytes -> parsed events (+ parse status). */
  def fromKafkaValue(kafka: DataFrame): DataFrame =
    kafka.select(
        col("key").cast("string").as("kafka_key"),
        col("value").cast("string").as("raw_json"),
        col("topic"), col("partition"), col("offset"), col("timestamp").as("kafka_ts"))
      .withColumn("e", from_json(col("raw_json"), EventSchema, Map("mode" -> "PERMISSIVE")))

  /** Is a parsed event usable (well-formed JSON, known schema, has the key fields)? */
  val Parsable: Column =
    col("e").isNotNull && col("e.schema_version").isin(SupportedSchemaVersions: _*) &&
      col("e.market").isNotNull && col("e.commodity").isNotNull && col("e.arrival_date").isNotNull

  def eventsToCanonical(parsed: DataFrame): DataFrame =
    standardize(parsed.select(col("e.*"), col("kafka_ts"), col("partition"), col("offset")))

  /** Batch entry: rows already in canonical column names (silver layer or Readers output). */
  def batchToCanonical(rows: DataFrame): DataFrame = standardize(rows)
}
