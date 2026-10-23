package com.agribigdata.forecast

import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions._
import org.scalatest.BeforeAndAfterAll
import org.scalatest.funsuite.AnyFunSuite

/** Metric definitions, split boundaries, conformal calibration and decision rule. */
class ForecastEvalSpec extends AnyFunSuite with BeforeAndAfterAll {
  private var spark: SparkSession = _
  override def beforeAll(): Unit =
    spark = SparkSession.builder().master("local[2]").appName("eval-spec").config("spark.ui.enabled", "false")
      .config("spark.sql.shuffle.partitions", "2").config("spark.driver.host", "127.0.0.1").getOrCreate()
  override def afterAll(): Unit = if (spark != null) spark.stop()

  test("rupee-scale metrics match hand calculation") {
    val s = spark; import s.implicits._
    // P0=100; actual = 110 (y=ln1.1); forecasts 100 (persistence) and 120
    val df = Seq((1L, 100.0, math.log(1.1), 0.0, math.log(1.2), 5.0), (1L, 200.0, 0.0, 0.0, math.log(0.9), 5.0))
      .toDF("entity_id", "modal_price", "y", "pred_p", "pred_m", "mase_scale")
    val p = ForecastEval.overall(df, "pred_p", "y")
    val m = ForecastEval.overall(df, "pred_m", "y")
    assert(math.abs(p.mae - 5.0) < 1e-9)                  // |100-110|, |200-200|
    assert(math.abs(m.mae - 15.0) < 1e-9)                 // |120-110|, |180-200|
    assert(math.abs(m.rmse - math.sqrt((100 + 400) / 2.0)) < 1e-9)
    assert(math.abs(m.wape - 30.0 / 310.0) < 1e-9)
    assert(math.abs(m.bias - (10 - 20) / 2.0) < 1e-9)
    assert(math.abs(m.mase - 3.0) < 1e-9)                 // mean(10/5, 20/5)
    assert(math.abs(m.dirAcc - 1.0) < 1e-9)               // only row 1 has |y| >= 1%, sign matches
  }

  test("period filter purges rows whose target crosses the boundary") {
    val s = spark; import s.implicits._
    val h7 = ForecastConfig.Horizons.find(_.name == "h7").get
    val df = Seq(("2023-12-20", "2023-12-28"), ("2023-12-28", "2024-01-04"), ("2024-01-02", "2024-01-09"))
      .toDF("o", "t").select(to_date($"o").as("arrival_date"), unix_date(to_date($"t")).cast("long").as(Features.targetDay(h7)),
        lit(0.01).as(Features.target(h7)))
    val tr = ForecastBenchmark.periodFilter(df, h7, "2016-01-01", Some("2023-12-31")).count()
    val va = ForecastBenchmark.periodFilter(df, h7, "2024-01-01", Some("2024-12-31")).count()
    assert(tr == 1, "the 2023-12-28 origin targets 2024 and must be purged from training")
    assert(va == 1)
  }

  test("conformal intervals reach nominal coverage on exchangeable data and widen with volatility") {
    val s = spark; import s.implicits._
    val rnd = new scala.util.Random(1)
    def gen(n: Int) = (1 to n).map { i =>
      val std30 = 0.02 + 0.2 * rnd.nextDouble()
      (std30, std30 * rnd.nextGaussian(), 0.0)
    }.toDF("std30", "y", "pred")
    val conf = ForecastEval.fitConformal(gen(20000), "pred", "y")
    val test = ForecastEval.applyConformal(gen(20000), conf, "pred")
    val r = test.agg(ForecastEval.intervalAggs("y").head, ForecastEval.intervalAggs("y").tail: _*).head()
    assert(math.abs(r.getDouble(0) - 0.8) < 0.02, s"80% coverage was ${r.getDouble(0)}")
    assert(math.abs(r.getDouble(2) - 0.9) < 0.02, s"90% coverage was ${r.getDouble(2)}")
    val w = test.groupBy("bucket").agg(avg($"hi80" - $"lo80").as("w")).orderBy("bucket").as[(Int, Double)].collect()
    assert(w.map(_._2).sliding(2).forall { case Array(a, b) => b > a })
  }

  test("decision rule follows conf/decision_rules.json") {
    val s = spark; import s.implicits._
    val r = DecisionRules.load()
    val df = Seq(("Tomato", 0.10, 0.3), ("Tomato", 0.03, 0.3), ("Wheat", 0.03, 0.3), ("Wheat", -0.2, -0.01), ("Wheat", -0.1, 0.1))
      .toDF("commodity", "lo80", "hi80")
    val sig = ForecastEval.decisions(df, 7, r.perishable, (r.weeklyPerishable, r.weeklyDurable), r.fixedCost)
      .select("signal").as[String].collect().toSeq
    assert(sig == Seq("HOLD", "WATCH", "HOLD", "SELL", "WATCH"))
  }

  test("absolute-loss GBT pipeline (percent target) learns the conditional median and survives save/load") {
    val s = spark; import s.implicits._
    val rnd = new scala.util.Random(3)
    // y is 0 with prob 0.6, else a positive jump: median 0, mean > 0
    val df = (1 to 4000).map { _ =>
      val x = rnd.nextDouble()
      val y = if (rnd.nextDouble() < 0.6) 0.0 else 0.05 + 0.05 * rnd.nextDouble()
      ("Tomato", x, y)
    }.toDF("commodity", "x", "y")
    val l1 = ForecastModels.fit(ForecastModels.GBT(3, 100, 0.5, "absolute"), Seq("x"), "y", "pred_gbt", 1L, df)
    val l2 = ForecastModels.fit(ForecastModels.GBT(3, 60, 0.1), Seq("x"), "y", "pred_gbt", 1L, df)
    val p1 = l1.transform(df).agg(avg("pred_gbt")).head().getDouble(0)
    val p2 = l2.transform(df).agg(avg("pred_gbt")).head().getDouble(0)
    assert(math.abs(p1) < 0.01, s"L1 prediction should be near the median 0, was $p1")
    assert(p2 > 0.02, s"L2 prediction should be near the mean ~0.03, was $p2")
    val dir = java.nio.file.Files.createTempDirectory("m").toString + "/m"
    l1.write.overwrite().save(dir)
    val back = org.apache.spark.ml.PipelineModel.load(dir).transform(df.drop("y")).agg(avg("pred_gbt")).head().getDouble(0)
    assert(math.abs(back - p1) < 1e-9, "reloaded model (no label column) must reproduce predictions")
  }

  test("Spark backtest rule agrees with the shared fixtures (cases it can express)") {
    val s = spark; import s.implicits._
    val r = DecisionRules.load()
    val fx = new com.fasterxml.jackson.databind.ObjectMapper().readTree(new java.io.File("conf/decision_fixtures.json"))
    import scala.jdk.CollectionConverters._
    val cases = fx.get("cases").elements().asScala.toSeq.filter { c =>
      val i = c.get("input")
      // the backtest has no unsupported / expired / stale / COMPARE inputs
      i.get("supported").asBoolean() && !i.get("expired").asBoolean() && !i.get("stale").asBoolean() &&
        c.get("expected").get("signal").asText() != "COMPARE" && i.get("compare").size() == 0
    }
    assert(cases.size >= 6)
    val df = cases.map { c =>
      val i = c.get("input"); val t = i.get("today").asDouble()
      (c.get("name").asText(), i.get("commodity").asText(), math.log(i.get("lo80").asDouble() / t), math.log(i.get("hi80").asDouble() / t),
        c.get("expected").get("signal").asText())
    }.toDF("name", "commodity", "lo80", "hi80", "expected")
    val out = ForecastEval.decisions(df, 7, r.perishable, (r.weeklyPerishable, r.weeklyDurable), r.fixedCost)
      .select("name", "signal", "expected").as[(String, String, String)].collect()
    out.foreach { case (n, got, exp) => assert(got == exp, s"$n: $got != $exp") }
  }

  test("conformal quantiles survive a CSV round trip (keys normalised)") {
    val c = ForecastEval.Conformal(Array(0.1), Map((0, ForecastEval.qkey((1 - 0.8) / 2)) -> -0.2))
    assert(c.q.contains((0, ForecastEval.qkey("0.100000".toDouble))))
  }

  test("externally scored (lgbm) predictions join on entity and origin, and a missing one refuses to publish") {
    val s = spark; import s.implicits._
    val dir = java.nio.file.Files.createTempDirectory("lgbm-preds").toString
    Seq((1L, "2026-10-22", "h7", 0.05), (2L, "2026-10-21", "h7", -0.02), (1L, "2026-10-22", "next", 0.01))
      .toDF("entity_id", "d", "horizon", "pred_lgbm").select($"entity_id", to_date($"d").as("arrival_date"), $"horizon", $"pred_lgbm")
      .write.parquet(s"$dir/ok")
    val base = Seq((1L, "2026-10-22"), (2L, "2026-10-21")).toDF("entity_id", "d").select($"entity_id", to_date($"d").as("arrival_date"))
    val out = ForecastPublish.externalPredictions(base, "h7", "pred_lgbm", s"$dir/ok").collect()
      .map(r => r.getLong(0) -> r.getAs[Double]("pred_lgbm")).toMap
    assert(out == Map(1L -> 0.05, 2L -> -0.02))
    val e = intercept[IllegalArgumentException](ForecastPublish.externalPredictions(base, "next", "pred_lgbm", s"$dir/ok"))
    assert(e.getMessage.contains("refusing to publish"))
  }
}
