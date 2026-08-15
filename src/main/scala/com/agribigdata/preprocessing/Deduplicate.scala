package com.agribigdata.preprocessing

import com.agribigdata.ingestion.Schemas.{Canonical, Quality}
import org.apache.spark.sql.DataFrame
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.functions._

/**
 * Deduplication on the business key.
 *
 * Profiling found real duplication in both sources:
 *   Daily Market Prices : 251,633 repeated keys -> 339,216 surplus rows
 *   India Mandi         : 136,378 repeated keys -> 196,045 surplus rows
 *
 * A repeated business key means the same commodity+variety, in the same
 * market, on the same day, was reported more than once. The duplicates are
 * not always identical rows — the prices can differ — so this is a genuine
 * choice about which report to believe, not a mechanical row-drop.
 */
object Deduplicate {

  /**
   * Keep exactly one row per business key.
   *
   * Selection order, most important first:
   *   1. VALID rows beat rows with a data-quality defect. If one report of
   *      a day's price is complete and another is missing its bounds, the
   *      complete one is the better record by definition.
   *   2. Then the row with the widest known price range, since a report
   *      carrying both bounds is more informative than a partial one.
   *   3. Then modal, min, max price as a deterministic tie-break.
   *
   * Step 3 exists purely so the pipeline is reproducible: without a total
   * ordering, `row_number` would pick an arbitrary row and two runs over the
   * same input could disagree. That would make every downstream number
   * unreproducible, which is not acceptable for a result anyone has to
   * defend.
   *
   * Implemented as a window rather than `dropDuplicates`, because
   * `dropDuplicates` gives no control over which row survives.
   */
  def byBusinessKey(df: DataFrame): DataFrame = {
    val w = Window
      .partitionBy(DataQuality.businessKey.map(col): _*)
      .orderBy(
        when(col(Canonical.qualityFlag) === Quality.Valid, 0).otherwise(1).asc,
        coalesce(col(Canonical.maxPrice) - col(Canonical.minPrice), lit(-1.0)).desc,
        col(Canonical.modalPrice).asc_nulls_last,
        col(Canonical.minPrice).asc_nulls_last,
        col(Canonical.maxPrice).asc_nulls_last
      )

    df.withColumn("_rn", row_number().over(w))
      .filter(col("_rn") === 1)
      .drop("_rn")
  }
}
