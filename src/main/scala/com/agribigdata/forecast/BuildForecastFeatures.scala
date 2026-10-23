package com.agribigdata.forecast

import com.agribigdata.ingestion.Schemas.{Canonical, Quality}
import com.agribigdata.utils.SparkSetup
import org.apache.spark.sql.SaveMode
import org.apache.spark.sql.functions._
import org.apache.spark.storage.StorageLevel

import java.nio.file.{Files, Paths}

/**
 * Stage F1: silver daily prices -> forecasting panel -> feature table.
 *
 *   sbt "runMain com.agribigdata.forecast.BuildForecastFeatures"
 *
 * Reads the deduplicated silver layer written by PreprocessDatasets
 * (VALID rows only), restricts it to the panel commodities, applies the
 * causal sanity rule, marks which entities are eligible for training and
 * evaluation (decided from 2021-2023 data only) and writes one feature
 * row per (entity, observation date) with targets for every horizon.
 *
 * Outputs
 *   data/forecast/panel_entities   one row per entity with eligibility
 *   data/forecast/features         partitioned by year
 *   results/forecast/panel_report.json
 */
object BuildForecastFeatures {

  def main(args: Array[String]): Unit = {
    val spark = SparkSetup.session("forecast-features",
      Map("spark.sql.shuffle.partitions" -> sys.env.getOrElse("AGRI_SHUFFLE_PARTITIONS", "64")))
    import ForecastConfig._

    val commodityList = commodities()
    println(s"[F1] commodities in panel: ${commodityList.size}")

    val silver = spark.read.parquet(SilverDaily)
      .filter(col(Canonical.qualityFlag) === Quality.Valid)
      .filter(col(Canonical.commodity).isin(commodityList: _*))
      .filter(col(Canonical.arrivalDate) >= lit(HistoryStart))
      .filter(col(Canonical.modalPrice) > 0)
      .select((Features.EntityCols ++ Seq(Canonical.grade, Canonical.arrivalDate, Canonical.minPrice,
        Canonical.maxPrice, Canonical.modalPrice)).map(col): _*)

    // Stages are checkpointed as Parquet (columnar + snappy) rather than
    // persisted with DISK_ONLY: on a laptop disk the serialized row blocks of
    // a 33M-row, 50-column frame plus window shuffles exhausted free space.
    val cleanPath = s"$Root/_stage_clean"
    val entFeatPath = s"$Root/_stage_entity_features"
    val (_, tClean) = SparkSetup.timed("F1 harmonise + sanity rule -> stage") {
      Features.withJumpFlag(Features.withKeys(Features.harmonize(silver)
          .withColumn("harmonize_collision", col("harmonize_collision")).drop("_rk")))
        .write.mode(SaveMode.Overwrite).parquet(cleanPath)
    }
    val staged = spark.read.parquet(cleanPath)
    val (counts, tCount) = SparkSetup.timed("F1 counts") {
      staged.agg(count(lit(1)).as("rows"),
        sum(when(col("sanity_jump") && !col("harmonize_collision"), 1).otherwise(0)).as("jump_rows"),
        countDistinct(col(Features.EntityId)).as("entities"),
        sum(when(col("harmonize_collision"), 1).otherwise(0)).as("collisions")).head()
    }
    val rowsIn = counts.getLong(0); val jumpRows = counts.getLong(1); val entitiesIn = counts.getLong(2)
    val collisions = counts.getLong(3)
    // A collision row's own jump flag is meaningless (it is a second report for
    // the same entity-day), so collisions are removed first.
    val flagged = staged.filter(!col("harmonize_collision")).drop("harmonize_collision")

    val clean = flagged.filter(!col("sanity_jump")).drop("sanity_jump")

    // Eligibility uses only 2021-2023 observations.
    val entities = clean
      .groupBy((Features.EntityId +: Features.EntityCols).map(col): _*)
      .agg(
        countDistinct(when(col(Canonical.arrivalDate).between(EligibilityStart, EligibilityEnd),
          col(Canonical.arrivalDate))).as("elig_days"),
        min(Canonical.arrivalDate).as("first_date"),
        max(Canonical.arrivalDate).as("last_date"),
        count(lit(1)).as("n_obs"))
      .withColumn("in_panel", col("elig_days") >= MinReportingDays)

    // AGRI_PANEL_FROM reuses an existing eligibility table (e.g. the main experiment's),
    // required when HistoryStart is later than the eligibility window.
    val ent = sys.env.get("AGRI_PANEL_FROM") match {
      case Some(p) =>
        println(s"[F1] reusing panel eligibility from $p")
        spark.read.parquet(p)
      case None =>
        require(HistoryStart <= EligibilityStart, "history must cover the eligibility window, or set AGRI_PANEL_FROM")
        SparkSetup.timed("F1 write panel_entities") {
          entities.coalesce(4).write.mode(SaveMode.Overwrite).parquet(EntitiesPath)
        }
        spark.read.parquet(EntitiesPath)
    }
    val panelEntities = ent.filter(col("in_panel")).count()

    // Materialise per-entity features once: the cross-section aggregates and
    // the main table both read them, and recomputing the window plan twice
    // would double the most expensive sort in the job.
    SparkSetup.timed("F1 entity features -> stage") {
      Features.withEntityFeatures(clean).write.mode(SaveMode.Overwrite).parquet(entFeatPath)
    }
    var feats = Features.withCrossSection(spark.read.parquet(entFeatPath))
    for (h <- Horizons) {
      feats = Features.withSeasonal(feats, h)
      feats = Features.withTarget(feats, h)
    }
    val horizonCols = Horizons.flatMap(h => Seq(Features.target(h), Features.targetDay(h),
      Features.seasonalNaive(h), Features.horizonFeature(h)))

    val out = feats
      .filter(Features.WarmUp)
      .join(ent.select(Features.EntityId, "in_panel"), Seq(Features.EntityId))
      .withColumn("year", year(col(Canonical.arrivalDate)))
      .select((Features.EntityCols ++ Seq(Canonical.grade, "market_raw", Features.EntityId, Canonical.arrivalDate, Features.Day, "year", "in_panel",
        Canonical.minPrice, Canonical.maxPrice, Canonical.modalPrice, "mean7", "mean30") ++
        Features.BaseFeatures ++ horizonCols).distinct.map(col): _*)

    val (_, tWrite) = SparkSetup.timed("F1 features: compute + write") {
      // AGRI_FEATURES_WRITE_MODE=append lets the table be built in commodity shards
      // (features and cross-sections are per commodity, so shards are exact).
      val mode = if (sys.env.get("AGRI_FEATURES_WRITE_MODE").contains("append")) SaveMode.Append else SaveMode.Overwrite
      out.repartition(col("year"), pmod(col(Features.EntityId), lit(4))).write.mode(mode).partitionBy("year").parquet(FeaturesPath)
    }
    val written = spark.read.parquet(FeaturesPath)
    val summary = written.agg(count(lit(1)).as("rows"),
      sum(when(col("in_panel"), 1).otherwise(0)).as("panel_rows"),
      min(Canonical.arrivalDate).as("min_date"), max(Canonical.arrivalDate).as("max_date")).head()

    val labelCounts = Horizons.map { h =>
      h.name -> written.filter(col(Features.target(h)).isNotNull).count()
    }

    val json =
      s"""{
         |  "stage": "F1_build_forecast_features",
         |  "silver_input": "$SilverDaily",
         |  "commodities": ${commodityList.size},
         |  "history_start": "$HistoryStart",
         |  "rows_valid_in_scope": $rowsIn,
         |  "entities_in_scope": $entitiesIn,
         |  "entity_key": "state|district|market(APMC suffix removed)|commodity|variety (grade is an attribute)",
         |  "harmonize_collisions_removed": $collisions,
         |  "sanity_jump_rows_removed": $jumpRows,
         |  "sanity_jump_share": ${jumpRows.toDouble / rowsIn},
         |  "eligibility_window": ["$EligibilityStart", "$EligibilityEnd"],
         |  "min_reporting_days": $MinReportingDays,
         |  "panel_entities": $panelEntities,
         |  "feature_rows": ${summary.getLong(0)},
         |  "feature_rows_panel": ${summary.getLong(1)},
         |  "feature_date_range": ["${summary.get(2)}", "${summary.get(3)}"],
         |  "labelled_rows_by_horizon": {${labelCounts.map { case (k, v) => s""""$k": $v""" }.mkString(", ")}},
         |  "seconds_harmonise_sanity_stage": $tClean,
         |  "seconds_counts": $tCount,
         |  "seconds_features_write": $tWrite
         |}""".stripMargin
    // intermediate stages are not part of the data layout
    val fs = org.apache.hadoop.fs.FileSystem.get(new java.net.URI(Root), spark.sparkContext.hadoopConfiguration)
    Seq(cleanPath, entFeatPath).foreach(p => fs.delete(new org.apache.hadoop.fs.Path(p), true))
    Files.createDirectories(Paths.get(ResultsRoot))
    Files.writeString(Paths.get(s"$ResultsRoot/panel_report${sys.env.get("AGRI_SHARD_TAG").map("_" + _).getOrElse("")}.json"), json)
    println(json)
    spark.stop()
  }
}
