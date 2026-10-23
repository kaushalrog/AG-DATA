package com.agribigdata.forecast

import com.agribigdata.ingestion.Schemas.{Canonical, Quality}
import com.agribigdata.streaming.Anomaly
import com.agribigdata.utils.SparkSetup
import com.fasterxml.jackson.databind.ObjectMapper
import org.apache.spark.ml.PipelineModel
import org.apache.spark.sql.{DataFrame, SaveMode}
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.functions._

import java.io.File
import java.nio.file.{Files, Paths}
import java.time.Instant
import scala.io.Source

/**
 * Stage F3: publish the GOLD layer read by the API.
 *
 *   sbt "runMain com.agribigdata.forecast.ForecastPublish exp=<experiment_id>"
 *
 * Nothing is trained here. The models and conformal quantiles selected in
 * ForecastBenchmark (stage F2) are applied to the latest observation of
 * every entity of the forecast commodities. Outputs (Parquet, small):
 *
 *   gold/latest_prices     latest report per entity, ALL commodities (last 120 days of data)
 *   gold/price_history     180 days of history for those entities
 *   gold/latest_forecasts  one row per (entity, horizon) with median and 80/90% intervals
 *   gold/entity_stats      trailing 30-day log-price mean/std per entity (streaming anomaly reference)
 *   gold/alerts            anomaly flags over the last 30 days of data (trailing, causal statistics)
 *   gold/meta.json         dataset and model metadata
 */
object ForecastPublish {
  import ForecastConfig._

  def main(args: Array[String]): Unit = {
    val o = args.flatMap(_.split("=", 2) match { case Array(k, v) => Some(k -> v); case _ => None }).toMap
    val expId = o.getOrElse("exp", sys.error("exp=<experiment_id> is required"))
    // archive = Kaggle snapshot only; official = silver v2 with data.gov.in records
    val origin = o.getOrElse("origin", "archive")
    // models are read from the experiment that produced them, even when features come from another root
    val modelsRoot = o.getOrElse("models", s"$ModelsPath/$expId")
    require(Set("archive", "official", "replay")(origin), s"unknown origin $origin")
    val spark = SparkSetup.session("forecast-publish")
    val expDir = s"$ResultsRoot/$expId"
    val manifest = new ObjectMapper().readTree(new File(s"$expDir/manifest.json"))
    // Refuse partial experiments (red-team RT-04). Older manifests have no flag; they are
    // accepted only if every horizon was completed.
    val completed = Option(manifest.get("completed")).map(_.asBoolean()).getOrElse(
      manifest.get("horizons").size() == Horizons.size)
    require(completed, s"experiment $expId is not complete; refusing to publish")
    val selected = Horizons.map(h => h.name -> manifest.get("selected_on_validation").get(h.name).asText()).toMap
    val rules = DecisionRules.load()

    // ---------------- prices / history for ALL commodities ----------------
    val silver = spark.read.parquet(SilverDaily).filter(col(Canonical.qualityFlag) === Quality.Valid && col(Canonical.modalPrice) > 0)
    // data_as_of = the last date whose report volume is at least 10% of the
    // median daily volume of the preceding 30 days. A single straggler report
    // on the final date (2026-04-21 has 1 VALID row) must not define "as of"
    // (red-team RT-23); reports after that date are not published.
    val daily = silver.filter(col(Canonical.arrivalDate) >= date_sub(lit(silver.agg(max(Canonical.arrivalDate)).head().getDate(0)), 60))
      .groupBy(Canonical.arrivalDate).count().orderBy(Canonical.arrivalDate).collect()
      .map(r => (r.getDate(0), r.getLong(1)))
    val dataEnd = daily.indices.reverse.find { i =>
      val prev = daily.slice(math.max(0, i - 30), i).map(_._2).sorted
      prev.nonEmpty && daily(i)._2 >= 0.1 * prev(prev.length / 2)
    }.map(i => daily(i)._1).getOrElse(daily.last._1)
    println(s"[F3] data_as_of = $dataEnd (max date ${daily.last._1})")
    val recent = Features.harmonize(silver.filter(col(Canonical.arrivalDate) >= date_sub(lit(dataEnd), 300)
        && col(Canonical.arrivalDate) <= lit(dataEnd)))
      .filter(!col("harmonize_collision")).drop("_rk", "harmonize_collision")
    val keyed = Features.withJumpFlag(Features.withKeys(recent)).filter(!col("sanity_jump"))
      .withColumn("mean30_prev", avg(col("lp")).over(Window.partitionBy(Features.EntityId).orderBy(col("day")).rangeBetween(-30, -1)))
      .withColumn("std30_prev", stddev_samp(col("lp")).over(Window.partitionBy(Features.EntityId).orderBy(col("day")).rangeBetween(-30, -1)))
      .withColumn("lp_7d_ago", last(col("lp"), ignoreNulls = true).over(Window.partitionBy(Features.EntityId).orderBy(col("day")).rangeBetween(-10, -7)))
      .withColumn("mean30", avg(col("lp")).over(Window.partitionBy(Features.EntityId).orderBy(col("day")).rangeBetween(-29, 0)))
      .withColumn("std30", stddev_samp(col("lp")).over(Window.partitionBy(Features.EntityId).orderBy(col("day")).rangeBetween(-29, 0)))
      .withColumn("cnt30", count(col("lp")).over(Window.partitionBy(Features.EntityId).orderBy(col("day")).rangeBetween(-29, 0)))
      .cache()

    val newestFirst = Window.partitionBy(Features.EntityId).orderBy(col("day").desc)
    val latest = keyed.filter(col(Canonical.arrivalDate) >= date_sub(lit(dataEnd), 120))
      .withColumn("_r", row_number().over(newestFirst)).filter(col("_r") === 1).drop("_r")
      .withColumn("days_old", datediff(lit(dataEnd), col(Canonical.arrivalDate)))
      .withColumn("change_7d_pct", (exp(col("lp") - col("lp_7d_ago")) - 1) * 100)
    latest.select(col(Features.EntityId).cast("string"), col(Canonical.state), col(Canonical.district), col(Canonical.market),
        col("market_raw"), col(Canonical.commodity), col(Canonical.variety), col(Canonical.grade), col(Canonical.arrivalDate),
        col(Canonical.minPrice), col(Canonical.maxPrice), col(Canonical.modalPrice), col("days_old"), col("change_7d_pct"),
        col("cnt30"), col("std30"))
      .coalesce(4).write.mode(SaveMode.Overwrite).parquet(s"$GoldRoot/latest_prices")

    keyed.join(latest.select(Features.EntityId), Seq(Features.EntityId))
      .filter(col(Canonical.arrivalDate) >= date_sub(lit(dataEnd), 180))
      .select(col(Features.EntityId).cast("string"), col(Canonical.arrivalDate), col(Canonical.minPrice), col(Canonical.maxPrice), col(Canonical.modalPrice))
      .repartition(8, col(Features.EntityId)).sortWithinPartitions(Features.EntityId, Canonical.arrivalDate)
      .write.mode(SaveMode.Overwrite).parquet(s"$GoldRoot/price_history")

    // Streaming reference: trailing statistics that EXCLUDE the entity's last report
    // (red-team RT-10). For a replay of dates inside this window the reference still
    // contains earlier replayed days; replay alerts are pipeline evidence only.
    latest.select(col(Features.EntityId), col("mean30_prev").as("ref_mean30"), col("std30_prev").as("ref_std30"), col(Canonical.arrivalDate).as("ref_date"))
      .write.mode(SaveMode.Overwrite).parquet(s"$GoldRoot/entity_stats")

    // alerts: last 30 days, scored against the PREVIOUS 30 days only
    val scored = keyed.filter(col(Canonical.arrivalDate) >= date_sub(lit(dataEnd), 30))
      .withColumnRenamed("mean30_prev", "ref_mean30").withColumnRenamed("std30_prev", "ref_std30")
    val alertsOut = Anomaly.withScore(scored).withColumnRenamed("anomaly_type", "type")
      .filter(col("type").isin(Anomaly.AlertTypes: _*))
    alertsOut.select(col(Features.EntityId).cast("string"), col(Canonical.state), col(Canonical.district), col(Canonical.market),
        col(Canonical.commodity), col(Canonical.variety), col(Canonical.grade), col(Canonical.arrivalDate), col(Canonical.modalPrice),
        col("type"), col("log_dev"), col("robust_z"), exp(col("ref_mean30")).as("ref_mean_price"))
      .coalesce(1).write.mode(SaveMode.Overwrite).parquet(s"$GoldRoot/alerts")

    // ---------------- forecasts (forecast commodities only) ----------------
    val feats = spark.read.parquet(FeaturesPath)
    val latestFeat = feats.filter(col("arrival_date") >= date_sub(lit(dataEnd), 120) && col("arrival_date") <= lit(dataEnd))
      .withColumn("_r", row_number().over(Window.partitionBy(Features.EntityId).orderBy(col("day").desc)))
      .filter(col("_r") === 1).drop("_r")
    val allFeatureCols = (Features.BaseFeatures ++ Horizons.map(Features.horizonFeature)).distinct
    val base = Features.fillFeatureNulls(latestFeat, allFeatureCols)
      .withColumn("days_old", datediff(lit(dataEnd), col("arrival_date")))
      .withColumn("supported", col("cnt30") >= 4 && col("days_old") <= 30)
      .withColumn("unsupported_reason",
        when(col("days_old") > 30, "stale_beyond_limit").when(col("cnt30") < 4, "insufficient_history"))

    val perHorizon = Horizons.map { h =>
      val sel = selected(h.name)
      val pred = s"pred_$sel"
      val withPred =
        if (Seq("gbt", "rf", "lr").contains(sel)) {
          val model = PipelineModel.load(s"$modelsRoot/${h.name}/$sel")
          model.transform(base).select((base.columns :+ pred).map(col): _*)
        } else ForecastBenchmark.withBaselines(base, h)
      val conf = readConformal(s"$expDir/conformal_${h.name}.csv")
      ForecastEval.applyConformal(withPred, conf, pred)
        .select(col(Features.EntityId).cast("string"), col("commodity"), col("arrival_date").as("origin_date"),
          col("modal_price").as("origin_price"), lit(h.name).as("horizon"), lit(h.days).as("horizon_days"),
          date_add(col("arrival_date"), h.days).as("target_from"),
          date_add(col("arrival_date"), if (h.name == "next") NextObsMaxGap else h.days + TargetTolerance).as("target_to"),
          (col("modal_price") * exp(col(pred))).as("median"),
          (col("modal_price") * exp(col("lo80"))).as("lo80"), (col("modal_price") * exp(col("hi80"))).as("hi80"),
          (col("modal_price") * exp(col("lo90"))).as("lo90"), (col("modal_price") * exp(col("hi90"))).as("hi90"),
          col(pred).as("pred_log_return"), col("lo80").as("lo80_log"), col("hi80").as("hi80_log"),
          lit(sel).as("model"), col("supported"), col("unsupported_reason"), col("in_panel"), col("std30"), col("cnt30"),
          col("cs_dev30"), col("ly_chg_" + h.name).as("ly_chg"), col("has_ly"), col("days_old"))
    }
    perHorizon.reduce(_ unionByName _).coalesce(4).write.mode(SaveMode.Overwrite).parquet(s"$GoldRoot/latest_forecasts")

    val counts = spark.read.parquet(s"$GoldRoot/latest_forecasts").groupBy("horizon").agg(count(lit(1)), sum(col("supported").cast("int"))).collect()
      .map(r => r.getString(0) -> Map("rows" -> r.getLong(1), "supported" -> r.getLong(2))).toMap
    val meta = Map(
      "data_as_of" -> dataEnd.toString,
      "generated_at" -> Instant.now().toString,
      "data_origin" -> origin,
      "model_version" -> expId,
      "selected_models" -> selected,
      "horizons" -> Horizons.map(_.name),
      "price_unit" -> "INR/quintal",
      "decision_rules_version" -> rules.version,
      "latest_prices_rows" -> spark.read.parquet(s"$GoldRoot/latest_prices").count(),
      "alerts_rows" -> spark.read.parquet(s"$GoldRoot/alerts").count(),
      "forecast_rows" -> counts,
      "source" -> (if (origin == "official")
        Map("name" -> "AGMARKNET daily mandi prices via data.gov.in (official API from 2025-10-01; Kaggle archive before)",
          "licence" -> "GODL-India", "url" -> "https://www.data.gov.in/resource/variety-wise-daily-market-prices-data-commodity")
      else Map("name" -> "AGMARKNET daily mandi prices (archived via data.gov.in / Kaggle snapshot)",
        "licence" -> "GODL-India", "url" -> "https://www.data.gov.in/")))
    Files.writeString(Paths.get(s"$GoldRoot/meta.json"), ResultsIO.json(meta))
    println(ResultsIO.json(meta))
    spark.stop()
  }

  def readConformal(path: String): ForecastEval.Conformal = {
    val src = Source.fromFile(path)
    val rows = try src.getLines().drop(1).map(_.split(",")).toSeq finally src.close()
    val q = rows.map(r => (r(1).toInt, ForecastEval.qkey(r(2).toDouble)) -> r(3).toDouble).toMap
    val edges = rows.map(r => r(1).toInt -> r(4).toDouble).distinct.sortBy(_._1).map(_._2).filterNot(_.isInfinite).toArray
    ForecastEval.Conformal(edges, q)
  }
}
