package com.agribigdata.ml

import com.agribigdata.utils.SparkSetup
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.functions._
import org.apache.spark.ml.feature.{Imputer, VectorAssembler}
import org.apache.spark.ml.classification.RandomForestClassifier
import org.apache.spark.ml.Pipeline
import com.agribigdata.ingestion.Schemas.Canonical
import java.security.MessageDigest

object Phase9FinalPersistence {
  def main(args: Array[String]): Unit = {
    val spark = SparkSetup.session("Phase9FinalPersistence")
    spark.sparkContext.setLogLevel("WARN")
    import spark.implicits._

    val inputPath = sys.env.getOrElse("AGRI_INPUT_PATH", "data/features/engineered")
    val fullData = spark.read.parquet(inputPath)

    val entityCols = Seq(Canonical.state, Canonical.district, Canonical.market, Canonical.commodity, Canonical.variety)
    val allEntities = fullData.select(entityCols.map(col): _*).distinct()
    
    val sampledEntities = allEntities.sample(withReplacement = false, fraction = 0.01, seed = 42L)
    
    val data = fullData.join(sampledEntities, entityCols, "inner")

    val wEntity = Window.partitionBy(entityCols.map(col): _*).orderBy(Canonical.arrivalDate)
    val dataWithNextZ = data.withColumn("next_z_score", lead(col("z_score"), 1).over(wEntity))
    val targetDefinition = dataWithNextZ.withColumn("target_anomaly", when(abs(col("next_z_score")) > 2.0, 1.0).otherwise(0.0))
      .filter(col("next_z_score").isNotNull)

    val trainValData = targetDefinition.filter(year(col(Canonical.arrivalDate)) < 2025)
    val testData = targetDefinition.filter(year(col(Canonical.arrivalDate)) >= 2025)
    
    val featureCols = Array(
      "previous_modal_price", "price_change", "price_change_pct", 
      "price_range", "relative_price_range", "previous_to_current_ratio", 
      "rolling_7_observation_avg", "rolling_7_observation_stddev", "z_score"
    )
    val imputedCols = featureCols.map(_ + "_imputed")
    val imputer = new Imputer().setInputCols(featureCols).setOutputCols(imputedCols).setStrategy("median")
    val assembler = new VectorAssembler().setInputCols(imputedCols).setOutputCol("features").setHandleInvalid("skip")

    val w1 = 5.0
    val trainDataWeighted = trainValData.withColumn("classWeight", when(col("target_anomaly") === 1.0, w1).otherwise(1.0))
    
    val rfWeight = new RandomForestClassifier().setLabelCol("target_anomaly").setFeaturesCol("features").setNumTrees(20).setMaxDepth(8).setSeed(42L).setWeightCol("classWeight")

    val pipeline = new Pipeline().setStages(Array(imputer, assembler, rfWeight))
    val model = pipeline.fit(trainDataWeighted)
    
    val modelLocalPath = "data/final_model/anomaly_prediction_rf"
    model.write.overwrite().save(modelLocalPath)
    println("MODEL ARTIFACT LOCAL: PASS")

    val predictions = model.transform(testData)
    val predsLocalPath = "data/final_predictions/anomaly_predictions"
    predictions.repartition(10).write.mode("overwrite").parquet(predsLocalPath)
    println("PREDICTIONS LOCAL: PASS")

    spark.stop()
  }
}
