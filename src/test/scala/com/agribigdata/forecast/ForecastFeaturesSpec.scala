package com.agribigdata.forecast

import com.agribigdata.ingestion.Schemas.Canonical
import org.apache.spark.sql.{DataFrame, Row, SparkSession}
import org.apache.spark.sql.functions._
import org.scalatest.BeforeAndAfterAll
import org.scalatest.funsuite.AnyFunSuite

import java.time.LocalDate

/**
 * Leakage and boundary tests for the forecasting features.
 *
 * The strongest check here is the perturbation test: change every price
 * AFTER an origin date (and every price of a different entity) and assert
 * that no feature at or before the origin moves. If any window frame looked
 * forward or crossed entities, that test fails.
 */
class ForecastFeaturesSpec extends AnyFunSuite with BeforeAndAfterAll {

  private var spark: SparkSession = _

  override def beforeAll(): Unit = {
    spark = SparkSession.builder().master("local[2]").appName("features-spec")
      .config("spark.sql.shuffle.partitions", "2")
      .config("spark.ui.enabled", "false")
      .config("spark.driver.host", "127.0.0.1")
      .getOrCreate()
  }

  override def afterAll(): Unit = if (spark != null) spark.stop()

  private val base = LocalDate.parse("2023-01-01")

  /** (market, dayOffset, price) -> canonical frame with one commodity. */
  private def frame(rows: Seq[(String, Int, Double)]): DataFrame = {
    val s = spark
    import s.implicits._
    rows.map { case (m, d, p) =>
      ("Tamil Nadu", "Salem", m, "Tomato", "Local", "FAQ", java.sql.Date.valueOf(base.plusDays(d)), p * 0.9, p * 1.1, p)
    }.toDF(Canonical.state, Canonical.district, Canonical.market, Canonical.commodity, Canonical.variety,
      Canonical.grade, Canonical.arrivalDate, Canonical.minPrice, Canonical.maxPrice, Canonical.modalPrice)
  }

  private def build(df: DataFrame): DataFrame = {
    var f = Features.withEntityFeatures(Features.withKeys(df))
    f = Features.withCrossSection(f)
    for (h <- ForecastConfig.Horizons) { f = Features.withSeasonal(f, h); f = Features.withTarget(f, h) }
    f
  }

  private val featureCols = Features.BaseFeatures.filterNot(_.startsWith("cs_")).filterNot(_.startsWith("sc_")) ++
    ForecastConfig.Horizons.flatMap(h => Seq(Features.horizonFeature(h), Features.seasonalNaive(h)))

  private def featuresAt(df: DataFrame, market: String, day: Int): Map[String, Any] = {
    val r: Row = df.filter(col(Canonical.market) === market && col(Canonical.arrivalDate) === java.sql.Date.valueOf(base.plusDays(day)))
      .select(featureCols.map(col): _*).head()
    featureCols.zipWithIndex.map { case (c, i) => c -> r.get(i) }.toMap
  }

  // 450 days of a gently varying price, every other day, two markets.
  private val history: Seq[(String, Int, Double)] =
    for { m <- Seq("A", "B"); d <- 0 until 450 by 2 } yield (m, d, 1000.0 + 50 * math.sin(d / 9.0) + (if (m == "B") 300 else 0))

  test("features at an origin do not change when future prices or other entities change") {
    val origin = 400
    val perturbed = history.map {
      case (m, d, p) if d > origin => (m, d, p * 7.3)   // future of every entity
      case ("B", d, p)             => ("B", d, p * 3.1) // all of entity B
      case x                       => x
    }
    val a = featuresAt(build(frame(history)), "A", origin)
    val b = featuresAt(build(frame(perturbed)), "A", origin)
    featureCols.foreach { c => assert(a(c) == b(c), s"feature $c leaked: ${a(c)} vs ${b(c)}") }
  }

  test("h7 target is the first observation in [t+7, t+10] and is null when that window is empty") {
    val rows = Seq(("A", 0, 100.0), ("A", 1, 110.0), ("A", 2, 120.0), ("A", 3, 130.0), ("A", 4, 140.0), ("A", 5, 150.0),
      ("A", 6, 160.0), ("A", 9, 190.0), ("A", 10, 200.0), ("A", 30, 300.0))
    val h7 = ForecastConfig.Horizons.find(_.name == "h7").get
    val f = Features.withTarget(Features.withKeys(frame(rows)), h7)
      .select(col(Features.Day), col(Features.target(h7)), col(Features.targetDay(h7)), col(Canonical.modalPrice))
      .orderBy(Features.Day).collect()
    val d0 = f.head.getLong(0)
    // origin day 0 -> window [7,10] -> first obs is day 9 (190)
    assert(f.head.getLong(2) - d0 == 9)
    assert(math.abs(f.head.getDouble(1) - math.log(190.0 / 100.0)) < 1e-12)
    // origin day 10 -> window [17,20] is empty -> no label
    val r10 = f.find(r => r.getLong(0) - d0 == 10).get
    assert(r10.isNullAt(1) && r10.isNullAt(2))
    // no row is ever its own target
    f.filterNot(_.isNullAt(2)).foreach(r => assert(r.getLong(2) > r.getLong(0)))
  }

  test("next-observation target respects the maximum gap") {
    val rows = Seq(("A", 0, 100.0), ("A", 3, 110.0), ("A", 20, 120.0))
    val next = ForecastConfig.Horizons.find(_.name == "next").get
    val f = Features.withTarget(Features.withKeys(frame(rows)), next)
      .orderBy(Features.Day).select(Features.target(next)).collect()
    assert(math.abs(f(0).getDouble(0) - math.log(1.1)) < 1e-12)
    assert(f(1).isNullAt(0), "17-day gap exceeds NextObsMaxGap and must not be labelled")
    assert(f(2).isNullAt(0))
  }

  test("targets never cross entity boundaries") {
    val rows = Seq(("A", 0, 100.0), ("B", 7, 999.0))
    val h7 = ForecastConfig.Horizons.find(_.name == "h7").get
    val f = Features.withTarget(Features.withKeys(frame(rows)), h7)
      .filter(col(Canonical.market) === "A").select(Features.target(h7)).head()
    assert(f.isNullAt(0))
  }

  test("seasonal naive uses only observations at least 348 days old") {
    val rows = (0 until 420).map(d => ("A", d, if (d < 50) 100.0 else 400.0))
    val h14 = ForecastConfig.Horizons.find(_.name == "h14").get
    val f = Features.withSeasonal(Features.withEntityFeatures(Features.withKeys(frame(rows))), h14)
    val r = f.filter(col(Canonical.arrivalDate) === java.sql.Date.valueOf(base.plusDays(380)))
      .select(Features.seasonalNaive(h14)).head()
    // t+14-365 = day 29 +-3 -> all prices 100, today 400
    assert(math.abs(r.getDouble(0) - math.log(100.0 / 400.0)) < 1e-12)
  }

  test("sanity rule flags a 100x keying slip but not a genuine 2x move") {
    val rows = (0 until 12).map(d => ("A", d, 1000.0)) ++ Seq(("A", 12, 100000.0), ("A", 13, 2000.0))
    val f = Features.withJumpFlag(Features.withKeys(frame(rows))).orderBy(Features.Day)
      .select("sanity_jump").collect().map(_.getBoolean(0))
    assert(f(12))
    assert(!f(13))
    assert(!f.take(12).exists(identity))
  }
}
