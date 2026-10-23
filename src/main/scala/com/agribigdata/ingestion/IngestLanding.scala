package com.agribigdata.ingestion

import com.agribigdata.forecast.{Features, ResultsIO}
import com.agribigdata.ingestion.Schemas.Canonical
import com.agribigdata.preprocessing.DataQuality
import com.agribigdata.streaming.CanonicalEvent
import com.agribigdata.utils.SparkSetup
import org.apache.spark.sql.{DataFrame, SaveMode}
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.functions._

import java.nio.file.{Files, Paths}

/**
 * Builds silver v2: the archived Daily Market Prices for dates before `cutoff`,
 * plus the official data.gov.in variety-wise records (backfill landing zone)
 * from `cutoff` on.
 *
 *   sbt "runMain com.agribigdata.ingestion.IngestLanding cutoff=2025-11-01"
 *
 * Why a cutoff: measured on sample days, the Kaggle archive holds 94-100% of the
 * official daily reports up to October 2025 but only 0-54% from November 2025
 * (AGMARKNET 2.0 migration). From the cutoff on, the official API replaces it.
 *
 * Rows keep their PUBLISHED spellings (silver is a faithful record); identifier
 * harmonisation happens downstream in Features.harmonize, identically for both
 * sources. Within the API data, the latest ingested version of a business key wins.
 *
 * Also writes results/ingest/revision_report.json: for the overlap period, how many
 * archive records exist in the API and how many have identical prices
 * (differences = source revisions or mirror errors).
 */
object IngestLanding {

  def main(args: Array[String]): Unit = {
    val o = args.flatMap(_.split("=", 2) match { case Array(k, v) => Some(k -> v); case _ => None }).toMap
    val cutoff = o.getOrElse("cutoff", "2025-11-01")
    val landing = o.getOrElse("landing", "data/ingest/landing/datagovin_variety")
    val archivePath = o.getOrElse("archive", "data/processed/daily_market_prices")
    val outPath = o.getOrElse("out", "data/processed/daily_market_prices_v2")
    val spark = SparkSetup.session("ingest-landing")

    // recursiveFileLookup disables partition discovery: the JSON's own arrival_date wins
    val api = spark.read.schema(CanonicalEvent.EventSchema).option("recursiveFileLookup", "true").json(landing)
      .withColumn(Canonical.arrivalDate, to_date(col("arrival_date")))
      .withColumn("_ingest", to_timestamp(col("ingest_ts")))
    val latest = Window.partitionBy((DataQuality.businessKey.filterNot(_ == Canonical.sourceDataset) :+ Canonical.grade).map(col): _*)
      .orderBy(col("_ingest").desc)
    val apiRows = api
      .withColumn("_r", row_number().over(latest)).filter(col("_r") === 1)
      .select(col(Canonical.state), col(Canonical.district), col(Canonical.market), col(Canonical.commodity),
        col(Canonical.variety), col(Canonical.grade), col(Canonical.arrivalDate), col(Canonical.minPrice),
        col(Canonical.maxPrice), col(Canonical.modalPrice))
      .withColumn(Canonical.arrivalsTonnes, lit(null).cast("double"))
      .withColumn(Canonical.commodityGroup, lit(null).cast("string"))
      .withColumn(Canonical.sourceDataset, lit("datagovin_variety"))
      .withColumn(Canonical.dataSource, lit("real"))
      .transform(DataQuality.withQualityFlag)
      .withColumn("price_outlier", lit(null).cast("boolean"))
      .withColumn("year", year(col(Canonical.arrivalDate)).cast("long"))

    val archive = spark.read.parquet(archivePath)
    val cols = archive.columns.toSeq
    val v2 = archive.filter(col(Canonical.arrivalDate) < lit(cutoff))
      .unionByName(apiRows.filter(col(Canonical.arrivalDate) >= lit(cutoff)).select(cols.map(col): _*))

    val (_, t) = SparkSetup.timed("silver v2 write") {
      v2.repartition(col("year")).write.mode(SaveMode.Overwrite).partitionBy("year").parquet(outPath)
    }

    // ---- revision report on the overlap (archive dates >= cutoff that the API also covers) ----
    def keyed(df: DataFrame): DataFrame = Features.normalizeIdentifiers(df)
      .select((Features.EntityCols :+ Canonical.grade :+ Canonical.arrivalDate).map(col) ++
        Seq(col(Canonical.modalPrice), col(Canonical.minPrice), col(Canonical.maxPrice)): _*)
    val apiDates = apiRows.select(Canonical.arrivalDate).distinct()
    val arch = keyed(archive.filter(col(Canonical.arrivalDate) >= lit(cutoff))).join(apiDates, Seq(Canonical.arrivalDate))
      .withColumnRenamed(Canonical.modalPrice, "a_modal").withColumnRenamed(Canonical.minPrice, "a_min").withColumnRenamed(Canonical.maxPrice, "a_max")
    val apiK = keyed(apiRows.filter(col(Canonical.arrivalDate) >= lit(cutoff)))
    val keys = Features.EntityCols :+ Canonical.grade :+ Canonical.arrivalDate
    val j = arch.join(apiK, keys, "left")
    val r = j.agg(count(lit(1)), count(col(Canonical.modalPrice)),
      sum(when(col("a_modal") === col(Canonical.modalPrice), 1).otherwise(0)),
      sum(when(col(Canonical.modalPrice).isNotNull && col("a_modal") =!= col(Canonical.modalPrice), 1).otherwise(0))).head()
    val perDay = apiRows.groupBy(Canonical.arrivalDate).count()
      .join(archive.filter(col(Canonical.arrivalDate) >= lit(cutoff)).groupBy(Canonical.arrivalDate).count().withColumnRenamed("count", "archive"),
        Seq(Canonical.arrivalDate), "left")
      .agg(sum("count"), sum(coalesce(col("archive"), lit(0L))), countDistinct(Canonical.arrivalDate), min(Canonical.arrivalDate), max(Canonical.arrivalDate)).head()
    val counts = spark.read.parquet(outPath).groupBy(Canonical.sourceDataset).count().collect().map(x => x.getString(0) -> x.getLong(1)).toMap
    val report = Map(
      "cutoff" -> cutoff, "landing" -> landing, "silver_v2" -> outPath, "write_seconds" -> t,
      "silver_v2_rows_by_source" -> counts,
      "api_days" -> perDay.getLong(2), "api_date_range" -> Seq(perDay.get(3).toString, perDay.get(4).toString),
      "api_records_after_dedup_on_api_days" -> perDay.getLong(0),
      "archive_records_on_same_days" -> perDay.getLong(1),
      "archive_coverage_of_api_on_overlap_days" -> perDay.getLong(1).toDouble / perDay.getLong(0),
      "overlap_archive_records" -> r.getLong(0),
      "overlap_archive_records_found_in_api" -> r.getLong(1),
      "overlap_identical_modal" -> r.getLong(2),
      "overlap_different_modal" -> r.getLong(3),
      "note" -> "Different modal prices on matched keys are source revisions or mirror errors; silver v2 uses the API value.")
    val js = ResultsIO.json(report)
    ResultsIO.dir("results/ingest")
    Files.writeString(Paths.get("results/ingest/revision_report.json"), js)
    println(s"[INGEST] $js")
    spark.stop()
  }
}
