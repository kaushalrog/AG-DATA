package com.agribigdata.preprocessing

import com.agribigdata.ingestion.Schemas.{Canonical, Quality}
import org.apache.spark.sql.{Column, DataFrame}
import org.apache.spark.sql.functions._

/**
 * DATA-QUALITY layer.
 *
 * This is the "veracity" stage, and it is strictly separate from market
 * anomaly detection. The distinction matters and is easy to get wrong:
 *
 *   Min=0, Max=0, Modal=900   -> an INCOMPLETE PRICE REPORT.
 *                                The market did nothing unusual; the
 *                                reporter only filed the modal price.
 *
 *   Min=6125, Max=0, Modal=6125 -> again a reporting defect, not a
 *                                crash in the price of the commodity.
 *
 * If these rows were fed to the anomaly detector they would dominate the
 * output with findings that say nothing about agriculture. So quality is
 * resolved first, and only VALID rows are eligible for modelling.
 */
object DataQuality {

  /**
   * Classify each row into exactly one quality bucket.
   *
   * Order matters: the checks run most-fundamental first (can we even
   * place this record in time?) down to the subtlest (is the modal price
   * internally consistent with the range?). A row is reported under its
   * first, most serious defect.
   */
  def classify: Column = {
    val minP   = col(Canonical.minPrice)
    val maxP   = col(Canonical.maxPrice)
    val modalP = col(Canonical.modalPrice)

    when(col(Canonical.arrivalDate).isNull, Quality.MissingDate)
      // A record with no modal price carries no signal: modal price is
      // the forecasting target and the anomaly input.
      .when(modalP.isNull || modalP === 0.0, Quality.MissingPrice)
      .when(minP < 0 || maxP < 0 || modalP < 0, Quality.NegativePrice)
      // Both bounds absent but a modal price present: partial report.
      .when((minP.isNull || minP === 0.0) && (maxP.isNull || maxP === 0.0), Quality.ZeroMinMax)
      // Upper bound alone missing.
      .when(maxP.isNull || maxP === 0.0, Quality.ZeroMax)
      .when(minP > maxP, Quality.MinGreaterThanMax)
      // Genuine internal contradiction: the "most common" price fell
      // outside the observed range on the same day in the same market.
      .when(modalP < minP || modalP > maxP, Quality.ModalOutsideRange)
      .otherwise(Quality.Valid)
  }

  /** Attach the quality verdict without dropping anything. */
  def withQualityFlag(df: DataFrame): DataFrame =
    df.withColumn(Canonical.qualityFlag, classify)

  /**
   * The business key that identifies one real-world observation:
   * "this commodity+variety+grade, in this market, on this day".
   *
   * Used for duplicate detection instead of a whole-row distinct().
   * A whole-row `distinct()` on 5.8M rows already produced a Java heap
   * OOM on this machine, because it shuffles every column of every row
   * and hashes the entire record. Grouping on six short key columns
   * shuffles a small fraction of the bytes and lets Spark aggregate with
   * a partial (map-side) count first.
   */
  val businessKey: Seq[String] = Seq(
    Canonical.sourceDataset,
    Canonical.state,
    Canonical.district,
    Canonical.market,
    Canonical.commodity,
    Canonical.variety,
    Canonical.arrivalDate
  )

  /**
   * Count duplicate business keys, distributed.
   *
   * Returns (distinctKeys, keysAppearingMoreThanOnce, surplusRows).
   * Everything is computed with aggregations; nothing lands on the driver
   * except three longs.
   */
  def duplicateStats(df: DataFrame): (Long, Long, Long) = {
    val grouped = df
      .groupBy(businessKey.map(col): _*)
      .agg(count(lit(1)).as("n"))
      // One pass, three scalars out.
      .agg(
        count(lit(1)).as("distinct_keys"),
        sum(when(col("n") > 1, 1).otherwise(0)).as("dup_keys"),
        sum(col("n") - 1).as("surplus_rows")
      )
      .head()

    (
      grouped.getAs[Long]("distinct_keys"),
      Option(grouped.getAs[java.lang.Long]("dup_keys")).map(_.longValue).getOrElse(0L),
      Option(grouped.getAs[java.lang.Long]("surplus_rows")).map(_.longValue).getOrElse(0L)
    )
  }
}
