package com.agribigdata.forecast

import org.apache.spark.sql.{Column, DataFrame, Row}
import org.apache.spark.sql.functions._

/**
 * Forecast metrics, computed distributed on the rupee scale.
 *
 * Notation for one row: P0 = price at origin, y = true log return,
 * yhat = predicted log return, A = P0*exp(y) (actual), F = P0*exp(yhat)
 * (forecast), e = F - A.
 *
 *   MAE   mean |e|
 *   RMSE  sqrt(mean e^2)
 *   WAPE  sum |e| / sum |A|         (scale-free, dominated by high-price rows)
 *   sMAPE mean 2|e| / (|A| + |F|)   (bounded in [0,2]; asymmetric, see docs)
 *   Bias  mean e                     (positive = over-forecast)
 *   MASE  mean |e| / s_entity, s_entity = mean |A - P0| over the entity's
 *         TRAINING rows for the same horizon (in-sample h-step naive MAE)
 *   RelMAE MAE / MAE(persistence) on exactly the same rows
 *   DirAcc share of rows with |y| >= 1% whose sign(yhat) == sign(y)
 *
 * MAPE is deliberately not reported: low-priced leafy vegetables produce
 * near-zero denominators.
 */
object ForecastEval {

  final case class Metric(n: Long, mae: Double, rmse: Double, wape: Double, smape: Double, bias: Double,
                          mase: Double, maseN: Long, dirAcc: Double)

  val P0 = "modal_price"

  def actual(y: String): Column = col(P0) * exp(col(y))
  def forecast(pred: String): Column = col(P0) * exp(col(pred))

  /** Aggregation expressions for one prediction column, optionally grouped. */
  def aggs(pred: String, y: String, scale: String = "mase_scale"): Seq[Column] = {
    val a = actual(y); val f = forecast(pred); val e = f - a
    Seq(
      count(lit(1)).as("n"),
      avg(abs(e)).as("mae"),
      sqrt(avg(e * e)).as("rmse"),
      // try_divide: Spark 4 runs in ANSI mode, where x/0 throws; small groups
      // (e.g. a state with no move >= 1%) must yield null, not kill the job.
      try_divide(sum(abs(e)), sum(abs(a))).as("wape"),
      avg(try_divide(lit(2.0) * abs(e), abs(a) + abs(f))).as("smape"),
      avg(e).as("bias"),
      avg(when(col(scale) > 0, try_divide(abs(e), col(scale)))).as("mase"),
      count(when(col(scale) > 0, lit(1))).as("mase_n"),
      try_divide(sum(when(abs(col(y)) >= 0.01 && signum(col(pred)) === signum(col(y)), 1).otherwise(0)).cast("double"),
        sum(when(abs(col(y)) >= 0.01, 1).otherwise(0)).cast("double")).as("dir_acc"))
  }

  private def d(r: Row, c: String): Double = Option(r.getAs[Any](c)).map(_.asInstanceOf[Double]).getOrElse(Double.NaN)

  def toMetric(r: Row): Metric = Metric(r.getAs[Long]("n"), r.getAs[Double]("mae"), r.getAs[Double]("rmse"),
    d(r, "wape"), d(r, "smape"), r.getAs[Double]("bias"),
    Option(r.getAs[Any]("mase")).map(_.asInstanceOf[Double]).getOrElse(Double.NaN), r.getAs[Long]("mase_n"),
    Option(r.getAs[Any]("dir_acc")).map(_.asInstanceOf[Double]).getOrElse(Double.NaN))

  def overall(df: DataFrame, pred: String, y: String): Metric = toMetric(df.agg(aggs(pred, y).head, aggs(pred, y).tail: _*).head())

  /** Per-group metrics for several predictors, long format. */
  def grouped(df: DataFrame, preds: Seq[String], y: String, by: Seq[String]): DataFrame =
    preds.map { p =>
      val a = aggs(p, y)
      df.groupBy(by.map(col): _*).agg(a.head, a.tail: _*).withColumn("model", lit(p.stripPrefix("pred_")))
    }.reduce(_ unionByName _)

  /** Per-entity MASE scale from training rows: mean |A - P0| for this horizon. */
  def maseScale(train: DataFrame, y: String): DataFrame =
    train.groupBy(Features.EntityId).agg(avg(abs(actual(y) - col(P0))).as("mase_scale"))

  // ------------------------------------------------------------------------
  // Split conformal prediction intervals (Mondrian by volatility bucket).
  //
  // Calibration residuals r = y - yhat come from the VALIDATION period only.
  // Rows are binned by trailing 30-day log-price volatility (std30) with bin
  // edges taken from validation quantiles, and within each bin the lower and
  // upper residual quantiles define the interval. This makes intervals wider
  // for volatile series and narrower for stable ones, without using any test
  // information. Coverage is a marginal (per-bin) guarantee only under
  // exchangeability, which time series violate; test coverage is therefore
  // MEASURED and reported, not assumed.
  // ------------------------------------------------------------------------
  final case class Conformal(edges: Array[Double], q: Map[(Int, Double), Double])

  /**
   * Quantile levels are used as map keys. (1 - 0.8) / 2 is 0.09999999999999998
   * in floating point but 0.1 once written to and read from CSV, so every key
   * is rounded to 6 decimals on insert and lookup. Without this, published
   * forecasts lost their lower bounds.
   */
  def qkey(p: Double): Double = math.rint(p * 1e6) / 1e6

  val Levels: Seq[Double] = Seq(0.8, 0.9)
  val NBuckets = 5

  /** Bucket i is the first edge e_i with std30 <= e_i; above every edge is the last bucket. */
  def bucketCol(edges: Array[Double]): Column =
    edges.zipWithIndex.reverse.foldLeft(lit(edges.length): Column) { case (acc, (e, i)) =>
      when(col("std30") <= e, lit(i)).otherwise(acc)
    }

  def fitConformal(valPred: DataFrame, pred: String, y: String): Conformal = {
    val probs = (1 until NBuckets).map(_.toDouble / NBuckets).toArray
    val edges = valPred.stat.approxQuantile("std30", probs, 1e-4)
    val withB = valPred.withColumn("bucket", bucketCol(edges)).withColumn("res", col(y) - col(pred))
    val qs = Levels.flatMap(l => Seq((1 - l) / 2, 1 - (1 - l) / 2)).distinct.sorted
    val rows = withB.groupBy("bucket").agg(count(lit(1)).as("n"),
      percentile_approx(col("res"), array(qs.map(lit): _*), lit(20000)).as("q")).collect()
    val m = rows.flatMap { r =>
      val b = r.getInt(0); val arr = r.getSeq[Double](2)
      qs.zip(arr).map { case (p, v) => (b, qkey(p)) -> v }
    }.toMap
    Conformal(edges, m)
  }

  /** Adds lo80/hi80/lo90/hi90 (log-return scale) and the bucket. */
  def applyConformal(df: DataFrame, c: Conformal, pred: String): DataFrame = {
    val withB = df.withColumn("bucket", bucketCol(c.edges))
    Levels.foldLeft(withB) { (acc, l) =>
      val lo = (1 - l) / 2; val hi = 1 - lo; val tag = (l * 100).round
      def lookup(p: Double): Column = (0 to NBuckets - 1).foldLeft(lit(null).cast("double"): Column) { (e, b) =>
        when(col("bucket") === b, lit(c.q.getOrElse((b, qkey(p)), Double.NaN))).otherwise(e)
      }
      acc.withColumn(s"lo$tag", col(pred) + lookup(lo)).withColumn(s"hi$tag", col(pred) + lookup(hi))
    }
  }

  def intervalAggs(y: String): Seq[Column] = Levels.flatMap { l =>
    val tag = (l * 100).round
    Seq(avg(when(col(y) >= col(s"lo$tag") && col(y) <= col(s"hi$tag"), 1.0).otherwise(0.0)).as(s"coverage$tag"),
      avg(exp(col(s"hi$tag")) - exp(col(s"lo$tag"))).as(s"rel_width$tag"))
  }

  // ------------------------------------------------------------------------
  // Decision-support backtest. The rule (conf/decision_rules.json):
  //   cost_h = fixed + weekly_cost(perishable?) * h / 7
  //   HOLD  if lo80 >= ln(1 + cost_h)   (even a pessimistic outcome beats selling now after costs)
  //   SELL  if hi80 <= 0                (even an optimistic outcome is below today's price)
  //   WATCH otherwise
  // Outcome: HOLD correct if realised y >= ln(1+cost_h); SELL correct if y < 0.
  // ------------------------------------------------------------------------
  def decisions(df: DataFrame, horizonDays: Int, perishable: Seq[String], weekly: (Double, Double), fixed: Double): DataFrame = {
    val cost = lit(fixed) + when(col("commodity").isin(perishable: _*), lit(weekly._1)).otherwise(lit(weekly._2)) * (horizonDays / 7.0)
    df.withColumn("cost_h", cost)
      .withColumn("signal",
        // EPS: same boundary tolerance as decisions.py / decision.js
        when(col("lo80") >= log(lit(1.0) + col("cost_h")) + log(lit(1.0 - 1e-9)), "HOLD")
          .when(col("hi80") <= log(lit(1.0 + 1e-9)), "SELL").otherwise("WATCH"))
  }
}
