package com.agribigdata.forecast

import com.agribigdata.ingestion.Schemas.Canonical
import org.apache.spark.sql.{Column, DataFrame}
import org.apache.spark.sql.expressions.{Window, WindowSpec}
import org.apache.spark.sql.functions._

/**
 * Leakage-safe feature and target construction for mandi price forecasting.
 *
 * Conventions (each one is covered by a unit test in ForecastFeaturesSpec):
 *
 *  - An ENTITY is one price series: state, district, market, commodity,
 *    variety and grade. Varieties and grades are never pooled, because their
 *    prices are not interchangeable.
 *  - `day` is the integer day number (unix_date), so calendar windows can be
 *    expressed with rangeBetween.
 *  - Every FEATURE frame ends at the current row (0) or earlier. Nothing in a
 *    feature looks at a later day of the same entity.
 *  - Every TARGET frame starts strictly after the current row (>= +1 day).
 *  - The target is a log return y = ln(P_target) - ln(P_origin), so one global
 *    model can serve commodities whose prices differ by two orders of
 *    magnitude. Rupee forecasts are recovered as P_origin * exp(y_hat).
 */
object Features {

  /**
   * Entity key. Grade is deliberately NOT part of it: in the archive no
   * (market, commodity, variety, date) ever carries two grades, yet from
   * 2025-01-27 many series switch their grade label from "FAQ" to "Local"
   * with no overlap, which would split one price series into two. Grade is
   * kept as an attribute. See docs/DATA_DICTIONARY.md#identifier-harmonisation.
   */
  val EntityCols: Seq[String] = Seq(
    Canonical.state, Canonical.district, Canonical.market,
    Canonical.commodity, Canonical.variety)

  /**
   * AGMARKNET 2.0 (live from Nov 2025) republishes most markets with an
   * " APMC" suffix ("Lasalgaon" -> "Lasalgaon APMC"). The suffix is removed
   * so a market keeps one identity across the migration.
   */
  def normalizeMarket(c: Column): Column = normalizeName(regexp_replace(trim(c), "(?i)\\s+APMC$", ""))

  /**
   * Name spelling rule shared by every identifier. The data.gov.in API writes
   * "Bhindi(Ladies Finger)" and "Karur(Uzhavar Sandhai )" where the archive
   * writes "Bhindi (Ladies Finger)": collapse whitespace and put one space
   * before "(" unless it follows ")" (so "(Gram)(Whole)" is unchanged).
   * Verified on 2026-04-20: with this rule all 5,152 archive keys of that day
   * are found among the API's 22,716 records.
   */
  def normalizeName(c: Column): Column =
    regexp_replace(trim(regexp_replace(c, "\\s+", " ")), "([^\\s)])\\(", "$1 (")

  /** State spellings that changed or vary in the source, mapped to the archive spelling. */
  val StateAliases: Map[String, String] = Map("Keralam" -> "Kerala", "Uttrakhand" -> "Uttarakhand")

  def normalizeState(c: Column): Column = {
    val t = trim(regexp_replace(c, "\\s+", " "))
    StateAliases.foldLeft(t) { case (acc, (from, to)) => when(t === from, lit(to)).otherwise(acc) }
  }

  /** Applies every identifier rule; keeps the published market spelling in market_raw. */
  def normalizeIdentifiers(df: DataFrame): DataFrame =
    df.withColumn("market_raw", col(Canonical.market))
      .withColumn(Canonical.state, normalizeState(col(Canonical.state)))
      .withColumn(Canonical.district, normalizeName(col(Canonical.district)))
      .withColumn(Canonical.market, normalizeMarket(col(Canonical.market)))
      .withColumn(Canonical.commodity, normalizeName(col(Canonical.commodity)))
      .withColumn(Canonical.variety, normalizeName(col(Canonical.variety)))

  /**
   * Applies identifier harmonisation and keeps one report per entity-day
   * (collisions created by the rename are rare and resolved
   * deterministically: the record whose original market name is shortest,
   * i.e. the pre-migration spelling, wins).
   */
  def harmonize(df: DataFrame): DataFrame = {
    val w = Window.partitionBy((EntityCols :+ Canonical.arrivalDate).map(col): _*)
      .orderBy(length(col("market_raw")), col(Canonical.grade))
    normalizeIdentifiers(df)
      .withColumn("_rk", row_number().over(w))
      .withColumn("harmonize_collision", col("_rk") > 1)
  }

  val EntityId = "entity_id"
  val Day      = "day"
  val LogPrice = "lp"

  /** Numeric features fed to every model (horizon-specific ones are added per horizon). */
  val BaseFeatures: Seq[String] = Seq(
    "lp", "ret1", "ret2", "ret5", "gap1",
    "dev7", "dev30", "dev90", "std30", "std90", "cnt30", "cnt90",
    "hi30", "lo30", "spread", "ly_dev", "has_ly",
    "cs_dev30", "cs_ret1", "cs_n", "sc_dev30",
    "doy_sin", "doy_cos", "dow")

  def horizonFeature(h: ForecastConfig.Horizon): String = s"ly_chg_${h.name}"
  def target(h: ForecastConfig.Horizon): String         = s"y_${h.name}"
  def targetDay(h: ForecastConfig.Horizon): String      = s"tday_${h.name}"
  def seasonalNaive(h: ForecastConfig.Horizon): String  = s"snaive_${h.name}"

  private def byEntity: WindowSpec = Window.partitionBy(EntityId).orderBy(col(Day))
  private def days(lo: Long, hi: Long): WindowSpec = byEntity.rangeBetween(lo, hi)

  /**
   * Entity id shared by batch and streaming: whitespace-collapsed, null-safe
   * key fields hashed with xxhash64. Market must already be normalised.
   */
  def entityIdCol: Column =
    xxhash64(concat_ws("|", EntityCols.map(c => coalesce(trim(regexp_replace(col(c), "\\s+", " ")), lit(""))): _*))

  /** Adds entity_id, day and lp. Rows with non-positive modal prices must already be gone. */
  def withKeys(df: DataFrame): DataFrame =
    df.withColumn(EntityId, entityIdCol)
      .withColumn(Day, unix_date(col(Canonical.arrivalDate)).cast("long"))
      .withColumn(LogPrice, log(col(Canonical.modalPrice)))

  /**
   * Causal sanity rule: flags a record whose price jumps by more than
   * JumpFactor relative to the geometric mean of the entity's previous
   * observations. Uses ROWS strictly before the current one.
   */
  def withJumpFlag(df: DataFrame,
                   factor: Double = ForecastConfig.JumpFactor,
                   lookback: Int = ForecastConfig.JumpLookback,
                   minHistory: Int = ForecastConfig.JumpMinHistory,
                   keepAudit: Boolean = false): DataFrame = {
    val prev = byEntity.rowsBetween(-lookback, -1)
    val flagged = df.withColumn("_prev_mean", avg(col(LogPrice)).over(prev))
      .withColumn("_prev_n", count(col(LogPrice)).over(prev))
      .withColumn("sanity_jump",
        col("_prev_n") >= minHistory && abs(col(LogPrice) - col("_prev_mean")) > math.log(factor))
    if (keepAudit) flagged else flagged.drop("_prev_mean", "_prev_n")
  }

  /** Per-entity features computed only from the current and earlier observations. */
  def withEntityFeatures(df: DataFrame): DataFrame = {
    val lp = col(LogPrice)
    df
      .withColumn("ret1", lp - lag(lp, 1).over(byEntity))
      .withColumn("ret2", lp - lag(lp, 2).over(byEntity))
      .withColumn("ret5", lp - lag(lp, 5).over(byEntity))
      .withColumn("gap1", col(Day) - lag(col(Day), 1).over(byEntity))
      .withColumn("obs_index", row_number().over(byEntity))
      .withColumn("mean7", avg(lp).over(days(-6, 0)))
      .withColumn("mean30", avg(lp).over(days(-29, 0)))
      .withColumn("mean90", avg(lp).over(days(-89, 0)))
      .withColumn("std30", stddev_samp(lp).over(days(-29, 0)))
      .withColumn("std90", stddev_samp(lp).over(days(-89, 0)))
      .withColumn("cnt30", count(lp).over(days(-29, 0)).cast("double"))
      .withColumn("cnt90", count(lp).over(days(-89, 0)).cast("double"))
      .withColumn("hi30", lp - max(lp).over(days(-29, 0)))
      .withColumn("lo30", lp - min(lp).over(days(-29, 0)))
      .withColumn("dev7", lp - col("mean7"))
      .withColumn("dev30", lp - col("mean30"))
      .withColumn("dev90", lp - col("mean90"))
      // Same season last year: mean log price within +-3 days of t-365.
      .withColumn("ly_base", avg(lp).over(days(-368, -362)))
      .withColumn("ly_dev", lp - col("ly_base"))
      .withColumn("has_ly", when(col("ly_base").isNotNull, 1.0).otherwise(0.0))
      .withColumn("spread",
        when(col(Canonical.modalPrice) > 0,
          (col(Canonical.maxPrice) - col(Canonical.minPrice)) / col(Canonical.modalPrice)))
      .withColumn("doy_sin", sin(lit(2 * math.Pi) * dayofyear(col(Canonical.arrivalDate)) / 365.25))
      .withColumn("doy_cos", cos(lit(2 * math.Pi) * dayofyear(col(Canonical.arrivalDate)) / 365.25))
      .withColumn("dow", dayofweek(col(Canonical.arrivalDate)).cast("double"))
  }

  /**
   * Seasonal-naive quantities for horizon h. Both frames end at least
   * 365-h-3 >= 348 days before the origin, so they are history.
   *   snaive: last year's level around t+h-365, minus today's level
   *   ly_chg: last year's change from t-365 to t+h-365
   */
  def withSeasonal(df: DataFrame, h: ForecastConfig.Horizon): DataFrame = {
    val tol = 3L
    val lvl = avg(col(LogPrice)).over(days(-(365L - h.days + tol), -(365L - h.days - tol)))
    df.withColumn(s"_ly_lvl_${h.name}", lvl)
      .withColumn(seasonalNaive(h), col(s"_ly_lvl_${h.name}") - col(LogPrice))
      .withColumn(horizonFeature(h), col(s"_ly_lvl_${h.name}") - col("ly_base"))
      .drop(s"_ly_lvl_${h.name}")
  }

  /**
   * Target for horizon h. The frame [h, h + tolerance] starts at +h >= +1, so
   * the current observation can never be its own target. `next` uses the
   * immediately following observation, if it is close enough.
   */
  def withTarget(df: DataFrame, h: ForecastConfig.Horizon,
                 tolerance: Int = ForecastConfig.TargetTolerance,
                 nextMaxGap: Int = ForecastConfig.NextObsMaxGap): DataFrame = {
    if (h.name == "next") {
      val nlp  = lead(col(LogPrice), 1).over(byEntity)
      val nday = lead(col(Day), 1).over(byEntity)
      df.withColumn("_nlp", nlp).withColumn("_nday", nday)
        .withColumn(targetDay(h), when(col("_nday") - col(Day) <= nextMaxGap, col("_nday")))
        .withColumn(target(h), when(col(targetDay(h)).isNotNull, col("_nlp") - col(LogPrice)))
        .drop("_nlp", "_nday")
    } else {
      val w = days(h.days.toLong, (h.days + tolerance).toLong)
      df.withColumn(targetDay(h), first(col(Day), ignoreNulls = true).over(w))
        .withColumn(target(h), first(col(LogPrice), ignoreNulls = true).over(w) - col(LogPrice))
    }
  }

  /**
   * Cross-sectional context: how the same commodity is moving in other
   * markets on the same day (nationally and within the state). These use
   * same-day reports only, i.e. information published by the end of day t.
   */
  def withCrossSection(df: DataFrame): DataFrame = {
    val cs = df.groupBy(Canonical.commodity, Day)
      .agg(avg("dev30").as("cs_dev30"), avg("ret1").as("cs_ret1"), count(lit(1)).cast("double").as("cs_n"))
    val sc = df.groupBy(Canonical.state, Canonical.commodity, Day)
      .agg(avg("dev30").as("sc_dev30"))
    df.join(cs, Seq(Canonical.commodity, Day), "left")
      .join(sc, Seq(Canonical.state, Canonical.commodity, Day), "left")
  }

  /** Imputation that needs no fitted statistics (so it cannot leak). */
  def fillFeatureNulls(df: DataFrame, cols: Seq[String]): DataFrame =
    df.na.fill(0.0, cols)

  /** Rows with enough history to be a forecast origin. */
  val WarmUp: Column = col("obs_index") > 5 && col("cnt90") >= 3
}
