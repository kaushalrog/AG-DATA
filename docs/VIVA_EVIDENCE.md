# Viva Evidence Guide

This document maps core concepts to their concrete usage within the project, serving as direct evidence for viva/project defense.

## HDFS (Hadoop Distributed File System)
- **1 NameNode** → Used to manage metadata and namespace → Configured via `docker-compose.yml` (`agri-namenode` listening on port 9000).
- **3 DataNodes** → Used to store the actual Parquet blocks → Defined in `docker-compose.yml` (`agri-datanode1`, `agri-datanode2`, `agri-datanode3`).
- **Replication factor 3** → Used to ensure high availability and fault tolerance of datasets → Enforced in `hdfs-site.xml` (`dfs.replication=3`).
- **Healthy fsck** → Used to prove zero missing or corrupt blocks → Verified via running `hdfs fsck /` inside the namenode container.

## Spark
- **DataFrames** → Used universally across all pipelines for structured data processing → Evidenced in `Phase4Standardization.scala` where raw CSVs are mapped to strong schema DataFrames.
- **Lazy evaluation** → Used to delay execution until an action is called → Evidenced in `Phase5FeatureEngineering.scala` where complex window transforms are stacked before the final `.write.parquet()` action triggers Catalyst.
- **Catalyst optimization** → Used to optimize physical execution plans automatically → Evidenced by `df.explain(true)` displaying physical query plans for window specs.
- **Shuffle** → Used to redistribute data across partitions for aggregations → Evidenced when applying `.groupBy("state", "district", "market", "commodity")` and window partitions.
- **Window functions** → Used to generate temporal features (7-day rolling averages) → Evidenced in `Phase5FeatureEngineering.scala` using `Window.partitionBy(entityCols).orderBy("arrival_date").rowsBetween(-7, -1)`.
- **Structured Streaming** → Used to process real-time Kafka events as unbounded DataFrames → Evidenced in `Phase10StructuredStreaming.scala` using `spark.readStream` and `flatMapGroupsWithState`.

## Scala
- **Spark implementation** → Used as the primary JVM language for maximum Spark API compatibility → Evidenced by the `.scala` files throughout `src/main/scala/com/agribigdata/`.
- **Functional/data-processing usage** → Used for immutable transformations → Evidenced by leveraging Scala's case classes (e.g. `case class MarketEvent`) and pure map functions in stateful processing.

## Kafka
- **Producer/consumer flow** → Used to decouple data ingestion from ML scoring → Evidenced by native Mac producer pushing JSON to `localhost:9092` and Spark streaming consuming from `host.docker.internal:29092`.
- **Topic** → Used as the distributed commit log → Evidenced by the `agri-market-transactions` topic retaining ordered market events.

## MLlib
- **Random Forest** → Used for robust, non-linear classification of market anomalies → Evidenced in `Phase8RandomForest.scala` using `RandomForestClassifier`.
- **Class weighting** → Used to penalize misclassifications of rare anomalies (weight=5) → Evidenced by `.setWeightCol("instance_weight")` in the pipeline.
- **Train/validation/test split** → Used for strict temporal evaluation to prevent data leakage → Evidenced by `year < 2024` (Train), `year == 2024` (Validation), and `year >= 2025` (Test) splits on the deterministic 1% entity sample.
- **Evaluation metrics** → Used to comprehensively assess model performance beyond simple accuracy → Evidenced by calculating F1, Balanced Accuracy, Precision, Recall, PR-AUC, and ROC-AUC via `MulticlassClassificationEvaluator` and `BinaryClassificationEvaluator`.

## Dashboard
- **Real-time prediction visualization** → Used to make HDFS predictions actionable for end-users → Evidenced by Streamlit (`src/dashboard/app.py`) reading the structured streaming parquet sink `/agri/streaming/anomaly_predictions` and rendering real-time KPI cards and charts.
