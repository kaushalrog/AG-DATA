package com.agribigdata.forecast

import com.agribigdata.utils.SparkSetup
import org.apache.spark.sql.functions._
import org.apache.spark.storage.StorageLevel

import scala.collection.mutable.ArrayBuffer

/**
 * Stage F2b: rolling-origin (expanding window) backtest.
 *
 *   sbt "runMain com.agribigdata.forecast.ForecastBacktest exp=<main experiment> folds=2021,2022,2023,2024 spec=gbt_d7_i100_s0.1"
 *
 * For each fold year Y: train on origins 2016-01-01 .. (Y-1)-12-31 (targets
 * purged at the boundary), test on origins in year Y (targets inside Y).
 * Hyper-parameters are FIXED (the configuration chosen on 2024 validation in
 * the main experiment), so this measures stability over time, not tuning.
 *
 * Caveat recorded in the output: panel membership was decided from 2021-2023
 * reporting density, so for folds 2021-2023 the choice of WHICH series are
 * evaluated used information from the fold's own period (no prices or labels).
 */
object ForecastBacktest {
  import ForecastConfig._

  def main(args: Array[String]): Unit = {
    val o = args.flatMap(_.split("=", 2) match { case Array(k, v) => Some(k -> v); case _ => None }).toMap
    val exp = o.getOrElse("exp", sys.error("exp= required"))
    val folds = o.getOrElse("folds", "2021,2022,2023,2024").split(",").map(_.toInt).toSeq
    val specName = o.getOrElse("spec", "gbt_d7_i100_s0.1")
    val spec = ForecastModels.SearchSpace.find(_.name == specName).getOrElse(sys.error(s"unknown spec $specName"))
    val horizons = o.get("horizons").map(_.split(",").toSet).map(s => Horizons.filter(h => s(h.name))).getOrElse(Horizons)
    val spark = SparkSetup.session("forecast-backtest", Map("spark.sql.shuffle.partitions" -> "64"))
    val feats = spark.read.parquet(FeaturesPath).filter(col("in_panel"))
    val allFeatureCols = (Features.BaseFeatures ++ Horizons.map(Features.horizonFeature)).distinct
    val out = ArrayBuffer[Seq[Any]]()

    for (h <- horizons; y <- folds) {
      val tgt = Features.target(h)
      val prepared = Features.fillFeatureNulls(feats, allFeatureCols)
      val train = ForecastBenchmark.periodFilter(prepared, h, TrainStart, Some(s"${y - 1}-12-31"))
      val test = ForecastBenchmark.withBaselines(ForecastBenchmark.periodFilter(prepared, h, s"$y-01-01", Some(s"$y-12-31")), h)
      val nTrain = train.count()
      val trainS = train.sample(withReplacement = false, math.min(1.0, MaxTrainRows.toDouble / nTrain), Seed).persist(StorageLevel.DISK_ONLY)
      val scale = ForecastEval.maseScale(train, tgt)
      val (model, tFit) = SparkSetup.timed(s"backtest ${h.name} $y fit") {
        ForecastModels.fit(spec, ForecastBenchmark.numericFeatures(h), tgt, "pred_model", Seed, trainS)
      }
      val scored = model.transform(test.join(scale, Seq(Features.EntityId), "left")).persist(StorageLevel.DISK_ONLY)
      val pers = ForecastEval.overall(scored, "pred_persistence", tgt)
      for (p <- Seq("pred_persistence", "pred_ma7", "pred_snaive", "pred_sadj", "pred_model")) {
        val m = ForecastEval.overall(scored, p, tgt)
        out += Seq(h.name, y, p.stripPrefix("pred_"), m.n, m.mae, m.wape, m.mase, m.mae / pers.mae, m.dirAcc, trainS.count(), tFit)
        println(f"[BT] ${h.name} $y ${p}%-18s MAE=${m.mae}%.1f relMAE=${m.mae / pers.mae}%.3f")
      }
      scored.unpersist(); trainS.unpersist()
    }
    val dir = ResultsIO.dir(s"$ResultsRoot/$exp").toString
    ResultsIO.writeLines(s"$dir/backtest_${specName}.csv",
      "horizon,fold_year,model,n,mae,wape,mase,rel_mae_vs_persistence,dir_acc,train_rows,fit_seconds", out.toSeq)
    spark.stop()
  }
}
