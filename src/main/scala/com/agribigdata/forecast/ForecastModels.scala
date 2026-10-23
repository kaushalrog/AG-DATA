package com.agribigdata.forecast

import org.apache.spark.ml.{Pipeline, PipelineStage}
import org.apache.spark.ml.feature.{OneHotEncoder, SQLTransformer, StandardScaler, StringIndexer, VectorAssembler}
import org.apache.spark.ml.regression.{GBTRegressor, LinearRegression, RandomForestRegressor}

/**
 * Spark MLlib candidates. Every model predicts the log return to the target
 * date, so persistence corresponds to predicting exactly 0.
 *
 * Preprocessing is part of the Pipeline and is fitted on training rows only:
 * the commodity StringIndexer and the StandardScaler see no validation or
 * test data. Unseen commodities map to an extra "unknown" index.
 */
object ForecastModels {

  sealed trait Spec { def family: String; def name: String }
  final case class LR(reg: Double, loss: String = "squaredError") extends Spec {
    val family = "lr"; val name = f"lr_reg$reg%.0e" + (if (loss == "huber") "_huber" else "")
  }
  final case class RF(trees: Int, depth: Int) extends Spec {
    val family = "rf"; val name = s"rf_t${trees}_d$depth"
  }
  final case class GBT(depth: Int, iters: Int, step: Double, loss: String = "squared") extends Spec {
    val family = "gbt"; val name = s"gbt_d${depth}_i${iters}_s$step" + (if (loss == "squared") "" else s"_$loss")
  }

  /**
   * Search space v2. Kept deliberately small: see docs/EXPERIMENTS.md#budget.
   *
   * v1 contained squared-loss models only. On VALIDATION (2024) the best of
   * them merely tied persistence on MAE for the next-report horizon, because
   * 34% of next-report changes are exactly zero (sticky quoted prices): a
   * squared loss estimates the conditional mean, whereas MAE is minimised by
   * the conditional median, which is often exactly "no change". v2 adds
   * absolute-loss GBT and Huber regression. v3: the absolute-loss GBTs are
   * trained on the target in percent (see pipeline). Both amendments were made
   * from validation evidence only, before any test metric was read
   * (docs/EXPERIMENTS.md#a10-protocol-amendment).
   */
  val SearchSpace: Seq[Spec] = Seq(
    LR(1e-4), LR(1e-2), LR(1e-4, "huber"),
    RF(60, 10),
    GBT(6, 200, 0.05),
    GBT(5, 150, 0.5, "absolute"), GBT(7, 150, 0.5, "absolute"), GBT(6, 300, 0.25, "absolute"))

  val CommodityIdx = "commodity_idx"

  /** Percent-scaled label used by absolute-loss GBTs (added at fit time only, never needed to predict). */
  def pctLabel(label: String): String = s"${label}__pct"

  /** Fits a candidate. Use this rather than pipeline(...).fit so label preparation stays outside the model. */
  def fit(spec: Spec, numeric: Seq[String], label: String, predCol: String, seed: Long,
          df: org.apache.spark.sql.DataFrame): org.apache.spark.ml.PipelineModel = {
    val prepared = spec match {
      case GBT(_, _, _, loss) if loss != "squared" =>
        df.withColumn(pctLabel(label), org.apache.spark.sql.functions.col(label) * 100.0)
      case _ => df
    }
    pipeline(spec, numeric, label, predCol, seed).fit(prepared)
  }

  def pipeline(spec: Spec, numeric: Seq[String], label: String, predCol: String, seed: Long): Pipeline = {
    val indexer = new StringIndexer().setInputCol("commodity").setOutputCol(CommodityIdx).setHandleInvalid("keep")
    val stages: Array[PipelineStage] = spec match {
      case LR(reg, loss) =>
        val ohe = new OneHotEncoder().setInputCol(CommodityIdx).setOutputCol("commodity_ohe").setHandleInvalid("keep")
        val num = new VectorAssembler().setInputCols(numeric.toArray).setOutputCol("num_vec").setHandleInvalid("keep")
        val scaler = new StandardScaler().setInputCol("num_vec").setOutputCol("num_scaled").setWithMean(true).setWithStd(true)
        val all = new VectorAssembler().setInputCols(Array("num_scaled", "commodity_ohe")).setOutputCol("features")
        val lr = new LinearRegression().setLabelCol(label).setFeaturesCol("features").setPredictionCol(predCol)
          .setRegParam(reg).setElasticNetParam(0.0).setMaxIter(100).setLoss(loss)
        Array(indexer, ohe, num, scaler, all, lr)
      case RF(trees, depth) =>
        val asm = new VectorAssembler().setInputCols((numeric :+ CommodityIdx).toArray).setOutputCol("features")
        val rf = new RandomForestRegressor().setLabelCol(label).setFeaturesCol("features").setPredictionCol(predCol)
          .setNumTrees(trees).setMaxDepth(depth).setSubsamplingRate(0.5).setFeatureSubsetStrategy("onethird")
          .setMaxBins(64).setMinInstancesPerNode(20).setSeed(seed)
        Array(indexer, asm, rf)
      case GBT(depth, iters, step, "squared") =>
        val asm = new VectorAssembler().setInputCols((numeric :+ CommodityIdx).toArray).setOutputCol("features")
        val gbt = new GBTRegressor().setLabelCol(label).setFeaturesCol("features").setPredictionCol(predCol)
          .setMaxDepth(depth).setMaxIter(iters).setStepSize(step).setSubsamplingRate(0.7).setLossType("squared")
          .setMaxBins(64).setMinInstancesPerNode(20).setSeed(seed)
        Array(indexer, asm, gbt)
      case GBT(depth, iters, step, loss) =>
        // MLlib's absolute-loss GBT fits each tree after the first to sign(residual) in
        // {-1, +1} with no leaf line search, so one iteration moves the prediction by up
        // to stepSize. In log-return units (typical |y| ~ 0.01) a step of 0.1 is ten times
        // the signal. Training on the target in PERCENT (x100) with stepSize 0.25-0.5 bounds each step at
        // 0.0025-0.005 log units;
        // the prediction is rescaled inside the pipeline, so the persisted model is used
        // unchanged downstream.
        val asm = new VectorAssembler().setInputCols((numeric :+ CommodityIdx).toArray).setOutputCol("features")
        val gbt = new GBTRegressor().setLabelCol(pctLabel(label)).setFeaturesCol("features").setPredictionCol(s"${predCol}__pct")
          .setMaxDepth(depth).setMaxIter(iters).setStepSize(step).setSubsamplingRate(0.7).setLossType(loss)
          .setMaxBins(64).setMinInstancesPerNode(20).setSeed(seed)
        val unscale = new SQLTransformer().setStatement(
          s"SELECT *, `${predCol}__pct` / 100.0 AS `$predCol` FROM __THIS__")
        // label scaling happens in fit(): a transform-time stage referencing the
        // label would fail when the model is applied to unlabelled (live) rows
        Array(indexer, asm, gbt, unscale)
    }
    new Pipeline().setStages(stages)
  }
}
