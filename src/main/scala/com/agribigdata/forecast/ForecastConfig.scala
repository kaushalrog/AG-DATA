package com.agribigdata.forecast

import java.nio.file.{Files, Paths}
import scala.jdk.CollectionConverters._

/**
 * Every constant that defines the forecasting experiment lives here, so the
 * protocol written in docs/EXPERIMENTS.md can be checked against one file.
 *
 * Dates are inclusive. The three periods are disjoint and in time order:
 *
 *   TRAIN       2016-01-01 .. 2023-12-31   (fit models, MASE scale)
 *   VALIDATION  2024-01-01 .. 2024-12-31   (tune, calibrate intervals)
 *   TEST        2025-01-01 .. data end     (touched once, for reporting)
 *
 * A row belongs to a period by its ORIGIN date, and is only kept if its
 * TARGET date also falls inside the same period. That purge is what stops
 * a December training origin from looking at a January validation price.
 */
object ForecastConfig {

  private def env(k: String, d: String): String = sys.env.getOrElse(k, d)

  // ---- Paths (overridable so the same jobs run against HDFS) ------------
  val SilverDaily: String = env("AGRI_SILVER_DAILY", "data/processed/daily_market_prices")
  val Root: String        = env("AGRI_FORECAST_ROOT", "data/forecast")
  val PanelPath    = s"$Root/panel"
  val EntitiesPath = s"$Root/panel_entities"
  val FeaturesPath = s"$Root/features"
  val ModelsPath   = s"$Root/models"
  val TestPredPath = s"$Root/test_predictions"
  val GoldRoot: String    = env("AGRI_GOLD_ROOT", "data/gold")
  val ResultsRoot: String = env("AGRI_RESULTS_ROOT", "results/forecast")

  // ---- Periods ------------------------------------------------------------
  /** History before TrainStart is read only to warm up lags/rolling windows. */
  /**
   * Overridable for scoring-only rebuilds: origins from 2025 need about 400 days
   * of history (seasonal windows reach t-372), so AGRI_HISTORY_START=2023-10-01
   * reproduces their features exactly with far less shuffle.
   */
  val HistoryStart: String = env("AGRI_HISTORY_START", "2014-10-01")
  // Defaults are the main experiment (fc_main_v3). The retraining experiment
  // overrides them via AGRI_* environment variables; every manifest records
  // the periods actually used.
  val TrainStart: String = env("AGRI_TRAIN_START", "2016-01-01")
  val TrainEnd: String   = env("AGRI_TRAIN_END", "2023-12-31")
  val ValStart: String   = env("AGRI_VAL_START", "2024-01-01")
  val ValEnd: String     = env("AGRI_VAL_END", "2024-12-31")
  val TestStart: String  = env("AGRI_TEST_START", "2025-01-01")

  // ---- Panel eligibility (decided from training data only) -------------
  val EligibilityStart  = "2021-01-01"
  val EligibilityEnd    = "2023-12-31"
  /** ~27% of trading days over three years: roughly "reports most weeks". */
  val MinReportingDays  = 300

  // ---- Horizons ------------------------------------------------------------
  /**
   * A calendar horizon h means: the target is the entity's FIRST observation
   * dated in [t+h, t+h+TargetTolerance]. Mandis do not report every day
   * (holidays, closures, non-reporting), so an exact t+h match would throw
   * away most targets; a tolerance window keeps the definition calendar-based
   * while admitting the next report. If no observation falls in the window
   * the row has no label for that horizon (it is not imputed).
   *
   * "next" is the next available observation, provided it is at most
   * NextObsMaxGap days away. It answers "what will the next report say?".
   */
  final case class Horizon(name: String, days: Int)
  val Horizons: Seq[Horizon] = Seq(Horizon("next", 1), Horizon("h3", 3), Horizon("h7", 7), Horizon("h14", 14))
  val TargetTolerance = 3
  val NextObsMaxGap   = 7

  // ---- Causal sanity rule ----------------------------------------------------
  /**
   * A record whose modal price is more than JumpFactor times (or less than
   * 1/JumpFactor of) the geometric mean of the entity's previous
   * JumpLookback observations is treated as a reporting error (typically a
   * unit or keying slip, e.g. 1500 entered as 150000). The rule looks only
   * backwards, so it can run identically in batch, in streaming and at
   * publication time. Removed counts are written to the panel report.
   */
  val JumpFactor   = 5.0
  val JumpLookback = 10
  val JumpMinHistory = 3

  // ---- Training budget -------------------------------------------------------
  /** Upper bound on training rows per horizon after random sampling. */
  val MaxTrainRows: Long = env("AGRI_MAX_TRAIN_ROWS", "2000000").toLong
  val MaxTuneValRows: Long = env("AGRI_MAX_TUNE_VAL_ROWS", "600000").toLong
  val Seed = 20261022L

  def commodities(path: String = env("AGRI_FORECAST_COMMODITIES", "conf/forecast_commodities.txt")): Seq[String] =
    Files.readAllLines(Paths.get(path)).asScala.map(_.trim).filter(l => l.nonEmpty && !l.startsWith("#")).toSeq
}
