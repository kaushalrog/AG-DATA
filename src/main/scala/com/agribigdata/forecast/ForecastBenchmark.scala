package com.agribigdata.forecast

import com.agribigdata.utils.SparkSetup
import org.apache.spark.ml.PipelineModel
import org.apache.spark.ml.regression.{GBTRegressionModel, RandomForestRegressionModel}
import org.apache.spark.sql.{DataFrame, SaveMode, SparkSession}
import org.apache.spark.sql.functions._
import org.apache.spark.storage.StorageLevel

import java.nio.file.{Files, Paths}
import java.time.{Instant, LocalDate}
import scala.collection.mutable.ArrayBuffer

/**
 * Stage F2: chronological benchmark of baselines and MLlib models.
 *
 *   sbt "runMain com.agribigdata.forecast.ForecastBenchmark [horizons=next,h3,h7,h14] [ablation=true]"
 *
 * Protocol (also in docs/EXPERIMENTS.md):
 *  1. Rows are panel entities only (eligibility decided on 2021-2023).
 *  2. TRAIN origins 2016-2023 whose target date is <= 2023-12-31;
 *     VALIDATION origins in 2024 whose target is <= 2024-12-31;
 *     TEST origins >= 2025-01-01. The purge on target dates removes the
 *     only path by which a label could reach across a boundary.
 *  3. Hyper-parameters are chosen by validation MAE (rupees). The model
 *     family used downstream is the one with the lowest validation MAE,
 *     baselines included: if nothing beats persistence on validation,
 *     persistence is selected.
 *  4. Conformal intervals are calibrated on validation residuals.
 *  5. The test period is scored once, after all choices above are fixed.
 */
object ForecastBenchmark {

  import ForecastConfig._

  val BaselinePreds = Seq("pred_persistence", "pred_ma7", "pred_ma30", "pred_snaive", "pred_sadj")

  def periodFilter(df: DataFrame, h: Horizon, start: String, end: Option[String]): DataFrame = {
    val td = col(Features.targetDay(h))
    val y  = col(Features.target(h))
    val base = df.filter(y.isNotNull && col("arrival_date") >= lit(start))
    end match {
      case Some(e) => base.filter(col("arrival_date") <= lit(e) && td <= unix_date(lit(e).cast("date")))
      case None    => base
    }
  }

  def withBaselines(df: DataFrame, h: Horizon): DataFrame =
    df.withColumn("pred_persistence", lit(0.0))
      .withColumn("pred_ma7", col("mean7") - col("lp"))
      .withColumn("pred_ma30", col("mean30") - col("lp"))
      .withColumn("pred_snaive", coalesce(col(Features.seasonalNaive(h)), lit(0.0)))
      .withColumn("pred_sadj", coalesce(col(Features.horizonFeature(h)), lit(0.0)))

  def numericFeatures(h: Horizon, drop: Set[String] = Set.empty): Seq[String] =
    (Features.BaseFeatures :+ Features.horizonFeature(h)).filterNot(drop.contains)

  val AblationGroups: Map[String, Set[String]] = Map(
    "no_cross_section" -> Set("cs_dev30", "cs_ret1", "cs_n", "sc_dev30"),
    "no_seasonal"      -> Set("ly_dev", "has_ly", "ly_chg_next", "ly_chg_h3", "ly_chg_h7", "ly_chg_h14"),
    "no_calendar"      -> Set("doy_sin", "doy_cos", "dow"),
    "no_level"         -> Set("lp"),
    "returns_only"     -> Set("dev7", "dev30", "dev90", "std30", "std90", "cnt30", "cnt90", "hi30", "lo30", "spread",
      "ly_dev", "has_ly", "cs_dev30", "cs_ret1", "cs_n", "sc_dev30", "doy_sin", "doy_cos", "dow", "lp", "gap1",
      "ly_chg_next", "ly_chg_h3", "ly_chg_h7", "ly_chg_h14"))

  def main(args: Array[String]): Unit = {
    val opts = args.flatMap(_.split("=", 2) match { case Array(k, v) => Some(k -> v); case _ => None }).toMap
    val horizons = opts.get("horizons").map(_.split(",").toSet).map(s => Horizons.filter(h => s(h.name))).getOrElse(Horizons)
    val ablation = opts.get("ablation").contains("true")
    val ablationHorizons = opts.getOrElse("ablationHorizons", "h7").split(",").toSet
    val specs = opts.get("specs").map(_.split(",").toSet)
      .map(s => ForecastModels.SearchSpace.filter(sp => s(sp.name) || s(sp.family))).getOrElse(ForecastModels.SearchSpace)

    val spark = SparkSetup.session("forecast-benchmark",
      Map("spark.sql.shuffle.partitions" -> sys.env.getOrElse("AGRI_SHUFFLE_PARTITIONS", "64")))
    spark.sparkContext.setCheckpointDir(s"$Root/_ckpt")

    val expId = opts.getOrElse("exp", s"fc_${LocalDate.now()}_${ResultsIO.gitCommit}")
    val out = ResultsIO.dir(s"$ResultsRoot/$expId").toString
    println(s"[F2] experiment $expId -> $out; horizons=${horizons.map(_.name).mkString(",")}")

    // crossSection=lag1 replaces the same-day cross-market features with the PREVIOUS
    // calendar day's values: information certainly published before the origin. This tests
    // whether the same-day assumption (KNOWN_LIMITATIONS #24) drives the gains. The lagged
    // aggregates are computed over the feature table's (warm-up filtered) rows of all entities.
    val crossSection = opts.getOrElse("crossSection", "same_day")
    val rawFeats = spark.read.parquet(FeaturesPath)
    val feats0 = if (crossSection == "lag1") {
      val cs = rawFeats.groupBy("commodity", "day").agg(avg("dev30").as("cs_dev30"), avg("ret1").as("cs_ret1"),
        count(lit(1)).cast("double").as("cs_n")).withColumn("day", col("day") + 1)
      val sc = rawFeats.groupBy("state", "commodity", "day").agg(avg("dev30").as("sc_dev30")).withColumn("day", col("day") + 1)
      rawFeats.drop("cs_dev30", "cs_ret1", "cs_n", "sc_dev30")
        .join(cs, Seq("commodity", "day"), "left").join(sc, Seq("state", "commodity", "day"), "left")
    } else rawFeats
    val feats = feats0.filter(col("in_panel"))
    val allFeatureCols = (Features.BaseFeatures ++ Horizons.map(Features.horizonFeature)).distinct
    val dataEnd = feats.agg(max("arrival_date")).head().getDate(0).toString

    val tuning = ArrayBuffer[Seq[Any]]()
    val overallRows = ArrayBuffer[Seq[Any]]()
    val intervalRows = ArrayBuffer[Seq[Any]]()
    val decisionRows = ArrayBuffer[Seq[Any]]()
    val importanceRows = ArrayBuffer[Seq[Any]]()
    val ablationRows = ArrayBuffer[Seq[Any]]()
    val selected = scala.collection.mutable.Map[String, String]()
    val sizes = scala.collection.mutable.Map[String, Any]()
    val timings = scala.collection.mutable.Map[String, Double]()
    val warnings = ArrayBuffer[String]()

    val rules = DecisionRules.load()

    // Cumulative outputs are rewritten after every horizon, so a late failure
    // never discards completed horizons.
    def writeAll(done: Seq[String], final_ : Boolean): Unit = {
      ResultsIO.writeLines(s"$out/tuning.csv", "horizon,family,spec,val_mae,val_rows,train_rows,fit_seconds,eval_seconds", tuning.toSeq)
      ResultsIO.writeLines(s"$out/metrics_overall.csv", "horizon,model,split,n,mae,rmse,wape,smape,bias,mase,mase_n,dir_acc,rel_mae_vs_persistence", overallRows.toSeq)
      ResultsIO.writeLines(s"$out/intervals.csv", "horizon,model,group,n,coverage80,rel_width80,coverage90,rel_width90", intervalRows.toSeq)
      ResultsIO.writeLines(s"$out/decisions.csv", "horizon,signal,n,share,hit_rate,mean_realised_return,mean_cost", decisionRows.toSeq)
      ResultsIO.writeLines(s"$out/feature_importance.csv", "horizon,family,spec,feature,importance", importanceRows.toSeq)
      if (ablation) ResultsIO.writeLines(s"$out/ablation.csv", "horizon,variant,n_features,val_mae,test_mae,test_rel_mae,test_mase,fit_seconds", ablationRows.toSeq)

      val manifest = Map(
        "experiment_id" -> expId,
        "completed" -> final_,
        "cross_section" -> crossSection,
        "created_utc" -> Instant.now().toString,
        "git_commit" -> ResultsIO.gitCommit,
        "git_dirty" -> ResultsIO.gitDirty,
        "spark_version" -> spark.version,
        "java_version" -> System.getProperty("java.version"),
        "master" -> spark.sparkContext.master,
        "default_parallelism" -> spark.sparkContext.defaultParallelism,
        "dataset" -> Map("features" -> FeaturesPath, "silver" -> SilverDaily, "panel" -> "in_panel=true",
          "commodities_file" -> "conf/forecast_commodities.txt", "data_end" -> dataEnd),
        "periods" -> Map("train" -> Seq(TrainStart, TrainEnd), "validation" -> Seq(ValStart, ValEnd), "test" -> Seq(TestStart, dataEnd)),
        "target" -> s"log return to first observation in [t+h, t+h+$TargetTolerance]; next = following obs within $NextObsMaxGap days",
        "horizons" -> done,
        "horizons_requested" -> horizons.map(_.name),
        "search_space" -> specs.map(_.name),
        "seed" -> Seed,
        "max_train_rows" -> MaxTrainRows,
        "max_tune_val_rows" -> MaxTuneValRows,
        "sizes" -> sizes.toMap,
        "selected_on_validation" -> selected.toMap,
        "decision_rules_version" -> rules.version,
        "warnings" -> warnings.toSeq,
        "models_path" -> s"$ModelsPath/$expId",
        "test_predictions_path" -> s"$TestPredPath/$expId")
      Files.writeString(Paths.get(s"$out/manifest.json"), ResultsIO.json(manifest))
      if (final_) ResultsIO.appendLine("results/experiments/registry.jsonl", ResultsIO.json(manifest))
    }

    val completed = ArrayBuffer[String]()
    for (h <- horizons) {
      val y = Features.target(h)
      // snaive_* columns are not model features and keep their nulls, so the
      // seasonal baseline can report how often it had to fall back.
      val prepared = Features.fillFeatureNulls(feats, allFeatureCols)

      val train = periodFilter(prepared, h, TrainStart, Some(TrainEnd))
      val valAll = withBaselines(periodFilter(prepared, h, ValStart, Some(ValEnd)), h)
      val test = withBaselines(periodFilter(prepared, h, TestStart, None), h)

      val scale = ForecastEval.maseScale(train, y).persist(StorageLevel.MEMORY_AND_DISK)
      val nTrain = train.count()
      val frac = math.min(1.0, MaxTrainRows.toDouble / nTrain)
      val trainS = train.sample(withReplacement = false, frac, Seed).persist(StorageLevel.DISK_ONLY)
      val nTrainS = trainS.count()
      val valP = valAll.join(scale, Seq(Features.EntityId), "left").persist(StorageLevel.DISK_ONLY)
      val nVal = valP.count()
      val valTune = valP.sample(withReplacement = false, math.min(1.0, MaxTuneValRows.toDouble / nVal), Seed)
        .persist(StorageLevel.DISK_ONLY)
      val testP = test.join(scale, Seq(Features.EntityId), "left").persist(StorageLevel.DISK_ONLY)
      val nTest = testP.count()
      sizes(h.name) = Map("train_rows" -> nTrain, "train_rows_sampled" -> nTrainS, "val_rows" -> nVal, "test_rows" -> nTest)
      println(s"[F2][${h.name}] train=$nTrain (sampled $nTrainS) val=$nVal test=$nTest")

      // ---- tuning on validation ------------------------------------------------
      val numeric = numericFeatures(h)
      val fitted = scala.collection.mutable.Map[String, (ForecastModels.Spec, PipelineModel, Double)]()
      for (spec <- specs) {
        val predCol = s"pred_${spec.family}"
        val (model, tFit) = SparkSetup.timed(s"${h.name} fit ${spec.name}") {
          ForecastModels.fit(spec, numeric, y, predCol, Seed, trainS)
        }
        val (valMae, tEval) = SparkSetup.timed(s"${h.name} val ${spec.name}") {
          ForecastEval.overall(model.transform(valTune), predCol, y).mae
        }
        tuning += Seq(h.name, spec.family, spec.name, valMae, valTune.count(), nTrainS, tFit, tEval)
        println(f"[F2][${h.name}] ${spec.name}%-28s val MAE = $valMae%.2f  (fit ${tFit}%.1fs)")
        if (fitted.get(spec.family).forall(_._3 > valMae)) fitted(spec.family) = (spec, model, valMae)
      }
      val baselineVal = BaselinePreds.map(p => p -> ForecastEval.overall(valTune, p, y).mae).toMap
      baselineVal.foreach { case (p, m) => tuning += Seq(h.name, "baseline", p.stripPrefix("pred_"), m, valTune.count(), 0, 0.0, 0.0) }

      // ---- score full validation and test with each family's best ---------------
      var valScored = valP
      var testScored = testP
      for ((fam, (spec, model, _)) <- fitted) {
        val pc = s"pred_$fam"
        valScored = model.transform(valScored).select((valScored.columns :+ pc).map(col): _*)
        testScored = model.transform(testScored).select((testScored.columns :+ pc).map(col): _*)
        model.write.overwrite().save(s"$ModelsPath/$expId/${h.name}/$fam")
        if (fam == "gbt" || fam == "rf") {
          val imp = model.stages.collectFirst {
            case g: GBTRegressionModel => g.featureImportances.toArray
            case r: RandomForestRegressionModel => r.featureImportances.toArray
          }.get
          (numeric :+ ForecastModels.CommodityIdx).zip(imp).foreach { case (f, v) => importanceRows += Seq(h.name, fam, spec.name, f, v) }
        }
      }
      valScored = valScored.persist(StorageLevel.DISK_ONLY)
      testScored = testScored.persist(StorageLevel.DISK_ONLY)

      val candidates = BaselinePreds ++ fitted.keys.toSeq.sorted.map(f => s"pred_$f")
      val valMetrics = candidates.map(p => p -> ForecastEval.overall(valScored, p, y)).toMap
      val winner = candidates.minBy(p => valMetrics(p).mae)
      selected(h.name) = winner.stripPrefix("pred_")
      println(s"[F2][${h.name}] selected on validation: $winner")
      if (winner == "pred_persistence") warnings += s"${h.name}: no candidate beat persistence on validation"

      // ---- conformal intervals from validation residuals of the winner -----------
      val conf = ForecastEval.fitConformal(valScored, winner, y)
      val testI = ForecastEval.applyConformal(testScored, conf, winner).withColumn("pred_selected", col(winner))
        .persist(StorageLevel.DISK_ONLY)

      // ---- test metrics (scored once) --------------------------------------------
      val persistTest = ForecastEval.overall(testI, "pred_persistence", y)
      for (p <- candidates :+ "pred_selected") {
        val m = ForecastEval.overall(testI, p, y)
        val v = if (p == "pred_selected") valMetrics(winner) else valMetrics(p)
        overallRows += Seq(h.name, p.stripPrefix("pred_"), "test", m.n, m.mae, m.rmse, m.wape, m.smape, m.bias, m.mase, m.maseN, m.dirAcc, m.mae / persistTest.mae)
        overallRows += Seq(h.name, p.stripPrefix("pred_"), "validation", v.n, v.mae, v.rmse, v.wape, v.smape, v.bias, v.mase, v.maseN, v.dirAcc, v.mae / valMetrics("pred_persistence").mae)
      }
      val snCov = testI.agg(avg(when(col(Features.seasonalNaive(h)).isNotNull, 1.0).otherwise(0.0))).head().getDouble(0)
      if (snCov < 0.9) warnings += f"${h.name}: seasonal naive available for only ${snCov * 100}%.1f%% of test rows (persistence fallback)"

      // interval coverage overall and by volatility bucket
      val ia = ForecastEval.intervalAggs(y)
      val iAll = testI.agg(count(lit(1)), ia: _*).head()
      intervalRows += Seq(h.name, winner.stripPrefix("pred_"), "all", iAll.getLong(0), iAll.getDouble(1), iAll.getDouble(2), iAll.getDouble(3), iAll.getDouble(4))
      testI.groupBy("bucket").agg(count(lit(1)), ia: _*).orderBy("bucket").collect().foreach { r =>
        intervalRows += Seq(h.name, winner.stripPrefix("pred_"), s"vol_bucket_${r.getInt(0)}", r.getLong(1), r.getDouble(2), r.getDouble(3), r.getDouble(4), r.getDouble(5))
      }
      val confRows = conf.q.toSeq.sortBy(_._1).map { case ((b, p), v) => Seq(h.name, b, p, v, if (b < conf.edges.length) conf.edges(b) else Double.PositiveInfinity) }
      ResultsIO.writeLines(s"$out/conformal_${h.name}.csv", "horizon,bucket,quantile,residual_q,std30_upper_edge", confRows)

      // per-commodity / per-state breakdowns
      val brkPreds = Seq("pred_persistence", "pred_selected") ++ fitted.keys.toSeq.sorted.map(f => s"pred_$f")
      ResultsIO.writeCsv(ForecastEval.grouped(testI, brkPreds.distinct, y, Seq("commodity")).withColumn("horizon", lit(h.name)),
        s"$out/test_by_commodity_${h.name}.csv")
      ResultsIO.writeCsv(ForecastEval.grouped(testI, Seq("pred_persistence", "pred_selected"), y, Seq("state")).withColumn("horizon", lit(h.name)),
        s"$out/test_by_state_${h.name}.csv")

      // daily loss series for Diebold-Mariano tests (python/analysis)
      val daily = (Seq("pred_persistence", "pred_selected") ++ fitted.keys.toSeq.sorted.map(f => s"pred_$f")).distinct.map { p =>
        val e = ForecastEval.forecast(p) - ForecastEval.actual(y)
        testI.groupBy("arrival_date").agg(count(lit(1)).as("n"), sum(abs(e)).as("sum_abs_err"), sum(e * e).as("sum_sq_err"))
          .withColumn("model", lit(p.stripPrefix("pred_")))
      }.reduce(_ unionByName _).withColumn("horizon", lit(h.name)).orderBy("model", "arrival_date")
      ResultsIO.writeCsv(daily, s"$out/test_daily_loss_${h.name}.csv")

      // decision-support backtest (calendar horizons only)
      if (h.name != "next") {
        val dec = ForecastEval.decisions(testI, h.days, rules.perishable, (rules.weeklyPerishable, rules.weeklyDurable), rules.fixedCost)
        val total = nTest.toDouble
        dec.groupBy("signal").agg(count(lit(1)).as("n"),
          avg(when(col("signal") === "HOLD", when(col(y) >= log(lit(1.0) + col("cost_h")), 1.0).otherwise(0.0))
            .when(col("signal") === "SELL", when(col(y) < 0, 1.0).otherwise(0.0))).as("hit_rate"),
          avg(exp(col(y)) - 1).as("mean_realised_return"),
          avg(col("cost_h")).as("mean_cost")).collect().foreach { r =>
          decisionRows += Seq(h.name, r.getString(0), r.getLong(1), r.getLong(1) / total,
            Option(r.get(2)).getOrElse(Double.NaN), r.getDouble(3), r.getDouble(4))
        }
      }

      // test predictions for downstream analysis (panel entities, compact)
      testI.select((Seq("entity_id", "state", "district", "market", "commodity", "variety", "arrival_date", "modal_price", y,
        Features.targetDay(h), "std30", "bucket", "lo80", "hi80", "lo90", "hi90") ++ candidates :+ "pred_selected").distinct.map(col): _*)
        .withColumn("horizon", lit(h.name))
        .write.mode(SaveMode.Overwrite).parquet(s"$TestPredPath/$expId/horizon=${h.name}")

      // ---- ablation (GBT, best validation config) ---------------------------------
      if (ablation && ablationHorizons(h.name) && fitted.contains("gbt")) {
        val best = fitted("gbt")._1
        for ((name, drop) <- AblationGroups.toSeq.sortBy(_._1)) {
          val num = numericFeatures(h, drop)
          val (m, t) = SparkSetup.timed(s"${h.name} ablation $name") {
            ForecastModels.fit(best, num, y, "pred_abl", Seed, trainS)
          }
          val v = ForecastEval.overall(m.transform(valTune), "pred_abl", y)
          val te = ForecastEval.overall(m.transform(testP), "pred_abl", y)
          ablationRows += Seq(h.name, name, num.size, v.mae, te.mae, te.mae / persistTest.mae, te.mase, t)
        }
        val full = ForecastEval.overall(testI, "pred_gbt", y)
        ablationRows += Seq(h.name, "full", numeric.size, valMetrics("pred_gbt").mae, full.mae, full.mae / persistTest.mae, full.mase, 0.0)
      }

      Seq(scale, trainS, valP, valTune, testP, valScored, testScored, testI).foreach(_.unpersist())
      completed += h.name
      writeAll(completed.toSeq, final_ = false)
    }

    writeAll(horizons.map(_.name), final_ = true)
    println(Files.readString(Paths.get(s"$out/manifest.json")))
    spark.stop()
  }
}
