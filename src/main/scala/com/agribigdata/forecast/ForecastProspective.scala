package com.agribigdata.forecast

import com.agribigdata.utils.SparkSetup
import com.fasterxml.jackson.databind.ObjectMapper
import org.apache.spark.ml.PipelineModel
import org.apache.spark.sql.functions._
import org.apache.spark.sql.{DataFrame, SaveMode}
import org.apache.spark.storage.StorageLevel

import java.io.File
import java.nio.file.{Files, Paths}
import java.time.Instant
import scala.collection.mutable.ArrayBuffer

/**
 * Scores FROZEN models on new data: no fitting, no tuning, no recalibration.
 *
 *   sbt "runMain com.agribigdata.forecast.ForecastProspective exp=fc_main_v3 features=data/forecast_v2/features
 *        from=2026-04-21 to=2026-10-22 label=prospective"
 *
 * Uses the models, the conformal quantiles and the MASE scales (from the main
 * experiment's training period) chosen before the data in [from, to] existed in
 * this project. Writes results/forecast/<exp>/<label>/ with metrics_overall.csv,
 * intervals.csv, decisions.csv, test_by_commodity_<h>.csv, test_daily_loss_<h>.csv
 * and manifest.json. The entity panel is the main experiment's panel (in_panel).
 */
object ForecastProspective {
  import ForecastConfig._

  def main(args: Array[String]): Unit = {
    val o = args.flatMap(_.split("=", 2) match { case Array(k, v) => Some(k -> v); case _ => None }).toMap
    val exp = o("exp"); val from = o("from"); val to = o("to"); val label = o.getOrElse("label", s"prospective_${from}_$to")
    val featPath = o.getOrElse("features", FeaturesPath)
    val modelsRoot = o.getOrElse("models", s"$ModelsPath/$exp")
    val expDir = s"$ResultsRoot/$exp"
    val out = ResultsIO.dir(s"$expDir/$label").toString
    val spark = SparkSetup.session("forecast-prospective")
    val manifest = new ObjectMapper().readTree(new File(s"$expDir/manifest.json"))
    val rules = DecisionRules.load()
    val feats = spark.read.parquet(featPath).filter(col("in_panel"))
    val allFeatureCols = (Features.BaseFeatures ++ Horizons.map(Features.horizonFeature)).distinct
    // MASE scale from the ORIGINAL training period (same definition as the benchmark)
    val trainFeats = spark.read.parquet(FeaturesPath).filter(col("in_panel"))

    val overall = ArrayBuffer[Seq[Any]](); val intervals = ArrayBuffer[Seq[Any]](); val decisions = ArrayBuffer[Seq[Any]]()
    val sizes = scala.collection.mutable.Map[String, Long]()
    for (h <- Horizons) {
      val y = Features.target(h)
      val sel = manifest.get("selected_on_validation").get(h.name).asText()
      val scale = ForecastEval.maseScale(ForecastBenchmark.periodFilter(trainFeats, h, TrainStart, Some(TrainEnd)), y)
      // targets must also fall inside [from, to]: nothing after `to` exists yet
      val rows = ForecastBenchmark.withBaselines(
          ForecastBenchmark.periodFilter(Features.fillFeatureNulls(feats, allFeatureCols), h, from, Some(to)), h)
        .join(scale, Seq(Features.EntityId), "left")
      val fams = Seq("lr", "rf", "gbt").filter(f => Files.exists(Paths.get(s"$modelsRoot/${h.name}/$f")))
      var scored: DataFrame = rows
      for (f <- fams) {
        val m = PipelineModel.load(s"$modelsRoot/${h.name}/$f")
        scored = m.transform(scored).select((scored.columns :+ s"pred_$f").map(col): _*)
      }
      val conf = ForecastPublish.readConformal(s"$expDir/conformal_${h.name}.csv")
      val s = ForecastEval.applyConformal(scored, conf, s"pred_$sel").withColumn("pred_selected", col(s"pred_$sel"))
        .persist(StorageLevel.DISK_ONLY)
      val n = s.count(); sizes(h.name) = n
      val preds = ForecastBenchmark.BaselinePreds ++ fams.map(f => s"pred_$f") :+ "pred_selected"
      val pers = ForecastEval.overall(s, "pred_persistence", y)
      for (p <- preds) {
        val m = ForecastEval.overall(s, p, y)
        overall += Seq(h.name, p.stripPrefix("pred_"), label, m.n, m.mae, m.rmse, m.wape, m.smape, m.bias, m.mase, m.maseN, m.dirAcc, m.mae / pers.mae)
      }
      val ia = ForecastEval.intervalAggs(y)
      val iAll = s.agg(count(lit(1)), ia: _*).head()
      intervals += Seq(h.name, sel, "all", iAll.getLong(0), iAll.getDouble(1), iAll.getDouble(2), iAll.getDouble(3), iAll.getDouble(4))
      s.groupBy("bucket").agg(count(lit(1)), ia: _*).orderBy("bucket").collect().foreach { r =>
        intervals += Seq(h.name, sel, s"vol_bucket_${r.getInt(0)}", r.getLong(1), r.getDouble(2), r.getDouble(3), r.getDouble(4), r.getDouble(5))
      }
      ResultsIO.writeCsv(ForecastEval.grouped(s, Seq("pred_persistence", "pred_selected"), y, Seq("commodity")).withColumn("horizon", lit(h.name)),
        s"$out/test_by_commodity_${h.name}.csv")
      val daily = Seq("pred_persistence", "pred_selected").map { p =>
        val e = ForecastEval.forecast(p) - ForecastEval.actual(y)
        s.groupBy("arrival_date").agg(count(lit(1)).as("n"), sum(abs(e)).as("sum_abs_err"), sum(e * e).as("sum_sq_err"))
          .withColumn("model", lit(p.stripPrefix("pred_")))
      }.reduce(_ unionByName _).withColumn("horizon", lit(h.name)).orderBy("model", "arrival_date")
      ResultsIO.writeCsv(daily, s"$out/test_daily_loss_${h.name}.csv")
      if (h.name != "next") {
        val dec = ForecastEval.decisions(s, h.days, rules.perishable, (rules.weeklyPerishable, rules.weeklyDurable), rules.fixedCost)
        dec.groupBy("signal").agg(count(lit(1)).as("n"),
          avg(when(col("signal") === "HOLD", when(col(y) >= log(lit(1.0) + col("cost_h")), 1.0).otherwise(0.0))
            .when(col("signal") === "SELL", when(col(y) < 0, 1.0).otherwise(0.0))).as("hit_rate"),
          expr(s"percentile_approx(exp($y) - 1, 0.5)").as("median_realised_return")).collect().foreach { r =>
          decisions += Seq(h.name, r.getString(0), r.getLong(1), r.getLong(1).toDouble / n, Option(r.get(2)).getOrElse(Double.NaN), r.getDouble(3))
        }
      }
      s.select("entity_id", "commodity", "state", "arrival_date", "modal_price", y, "lo80", "hi80", "pred_persistence", "pred_selected")
        .withColumn("horizon", lit(h.name)).write.mode(SaveMode.Overwrite).parquet(s"$TestPredPath/$exp/$label/horizon=${h.name}")
      s.unpersist()
    }
    ResultsIO.writeLines(s"$out/metrics_overall.csv", "horizon,model,split,n,mae,rmse,wape,smape,bias,mase,mase_n,dir_acc,rel_mae_vs_persistence", overall.toSeq)
    ResultsIO.writeLines(s"$out/intervals.csv", "horizon,model,group,n,coverage80,rel_width80,coverage90,rel_width90", intervals.toSeq)
    ResultsIO.writeLines(s"$out/decisions.csv", "horizon,signal,n,share,hit_rate,median_realised_return", decisions.toSeq)
    val mf = Map("experiment_id" -> exp, "evaluation" -> label, "created_utc" -> Instant.now().toString,
      "git_commit" -> ResultsIO.gitCommit, "git_dirty" -> ResultsIO.gitDirty, "features" -> featPath, "models" -> modelsRoot,
      "origins_and_targets_within" -> Seq(from, to), "rows" -> sizes.toMap,
      "frozen" -> "models, conformal quantiles and MASE scales from the main experiment; nothing refitted",
      "selected" -> Horizons.map(h => h.name -> manifest.get("selected_on_validation").get(h.name).asText()).toMap)
    Files.writeString(Paths.get(s"$out/manifest.json"), ResultsIO.json(mf))
    println(ResultsIO.json(mf))
    spark.stop()
  }
}
