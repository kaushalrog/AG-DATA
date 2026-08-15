package com.agribigdata.preprocessing

import com.agribigdata.ingestion.Schemas.{Canonical, Quality}
import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions._

/**
 * Extreme-magnitude price treatment.
 *
 * Profiling found VALID modal prices spanning 0.05 … 918,421,086 with a mean
 * of 3,198.99 and a standard deviation of 152,496.41 — a spread 48× the mean.
 * Crucially, these rows pass every data-quality rule: min ≤ modal ≤ max, all
 * positive, dates parse. They are plausible-looking records with implausible
 * magnitudes.
 *
 * Three things follow from that, and they drive the whole design here:
 *
 *  1. This cannot live in DataQuality. A quality flag answers "is this record
 *     well-formed?" and the answer for these rows is yes.
 *
 *  2. The threshold cannot be global. ₹9×10⁸ per quintal is absurd for onions
 *     but the *scale* of a plausible price differs by orders of magnitude
 *     across the ~387 commodities (cardamom and saffron genuinely trade far
 *     above potatoes). A single cutoff would either miss the onion errors or
 *     delete every legitimate spice price. So bounds are learned per
 *     commodity.
 *
 *  3. Outliers are FLAGGED, never dropped. An extreme price may be a
 *     recording error — or it may be the very market event this project
 *     exists to detect. Deleting them would silently delete the target
 *     phenomenon. The anomaly stage decides; preprocessing only labels.
 */
object OutlierTreatment {

  /** Column added by this stage. */
  val PriceOutlier = "price_outlier"

  /**
   * Tukey "far out" multiplier. 1.5×IQR marks ordinary outliers; 3×IQR marks
   * extreme ones. Agricultural prices are legitimately right-skewed and
   * seasonal, so the stricter 3× is used — the goal is to catch the ₹9×10⁸
   * class of value, not to flag every good harvest-season swing.
   */
  private val IqrMultiplier = 3.0

  /** Below this many valid observations, quartiles are too noisy to trust. */
  private val MinObservationsForIqr = 100

  /** Half-width (as a multiple) of the fallback band for rare commodities. */
  private val WideMedianFactor = 10.0

  /**
   * A commodity with fewer than this many observations is left entirely
   * unflagged: with a handful of points there is no defensible notion of
   * "typical" to deviate from.
   */
  private val MinObservationsToFlagAtAll = 10

  /**
   * Learn per-commodity price bounds from VALID rows.
   *
   * Returns one small row per commodity (~387 rows), so it is safe to
   * broadcast back onto the 132.9M-row dataset.
   *
   * Uses `percentile_approx` rather than an exact percentile: the exact
   * version requires a full sort of every commodity's prices, while the
   * approximate version keeps a bounded sketch per partition. With
   * accuracy 10,000 the quantile error is ~0.01%, far tighter than the
   * decision it feeds.
   */
  def learnBounds(df: DataFrame): DataFrame = {
    df.filter(col(Canonical.qualityFlag) === Quality.Valid)
      .groupBy(col(Canonical.commodity))
      .agg(
        percentile_approx(col(Canonical.modalPrice), lit(0.25), lit(10000)).as("p25"),
        percentile_approx(col(Canonical.modalPrice), lit(0.75), lit(10000)).as("p75"),
        percentile_approx(col(Canonical.modalPrice), lit(0.50), lit(10000)).as("median"),
        count(lit(1)).as("n_valid")
      )
      .withColumn("iqr", col("p75") - col("p25"))
      // Which rule applies to this commodity.
      //
      //  "iqr"         - enough observations for stable quartiles.
      //  "wide_median" - either too few observations, or a degenerate IQR
      //                  (every price identical, common for thinly-traded
      //                  goods). Quartiles from 26 points are noisy, and an
      //                  IQR of 0 would flag every row that differs at all.
      //
      // The wide rule is a deliberately blunt order-of-magnitude band around
      // the median. It exists because dropping low-count commodities
      // entirely lets gross errors through: Saffron has only 26 valid
      // records and a median of 66,200, and a 4,000,000 report sits 60× above
      // that. It is obviously wrong, and no amount of small-sample caution
      // makes it right. A ±10× band still tolerates the genuine spread of a
      // rare commodity while catching that.
      .withColumn("bound_type",
        when(col("n_valid") < MinObservationsForIqr || col("iqr") <= 0, lit("wide_median"))
          .otherwise(lit("iqr")))
      .withColumn("lower_bound",
        when(col("bound_type") === "wide_median", col("median") / WideMedianFactor)
          // Prices are strictly positive, so a negative lower bound is
          // meaningless; clamp at zero rather than letting IQR push it below.
          .otherwise(greatest(col("p25") - lit(IqrMultiplier) * col("iqr"), lit(0.0))))
      .withColumn("upper_bound",
        when(col("bound_type") === "wide_median", col("median") * WideMedianFactor)
          .otherwise(col("p75") + lit(IqrMultiplier) * col("iqr")))
  }

  /**
   * Attach `price_outlier` to every row using the learned bounds.
   *
   * Commodities below `MinObservationsToFlagAtAll` are left unflagged rather
   * than judged on the strength of a handful of points; between that floor
   * and `MinObservationsForIqr` the wide median band applies.
   */
  def flag(spark: SparkSession, df: DataFrame, bounds: DataFrame,
           minObservations: Long = MinObservationsToFlagAtAll): DataFrame = {

    val usable = bounds
      .filter(col("n_valid") >= minObservations)
      .select(
        col(Canonical.commodity).as("_b_commodity"),
        col("lower_bound"), col("upper_bound"))

    df.join(broadcast(usable),
            df(Canonical.commodity) <=> col("_b_commodity"), "left")
      .withColumn(PriceOutlier,
        when(col("lower_bound").isNull, lit(false))          // no learned bound
          .when(col(Canonical.qualityFlag) =!= Quality.Valid, lit(false))
          .when(col(Canonical.modalPrice) > col("upper_bound"), lit(true))
          .when(col(Canonical.modalPrice) < col("lower_bound"), lit(true))
          .otherwise(lit(false)))
      .drop("_b_commodity", "lower_bound", "upper_bound")
  }
}
