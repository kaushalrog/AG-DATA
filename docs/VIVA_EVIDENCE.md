# Viva Evidence Guide

This document maps core concepts to their concrete usage within the **Large-Scale Agricultural Market Data Processing and Real-Time Market Analysis** project, serving as direct evidence for viva/project defense.

## Data Scale and Volume
- **Real Source Records:** 132.9M real agricultural records ingested.
- **Canonical Dataset:** 93.41M canonical records standardized in HDFS.
- **Real Raw Volume:** ~10.9 GB real data.
- **Synthetic Scalability Workload:** ~7.1 GB (clearly marked for isolated scalability testing).

## HDFS (Distributed Storage)
- **1 NameNode** → Manages metadata and namespace (`agri-namenode` listening on port 9000).
- **3 DataNodes** → Stores the actual Parquet blocks (`agri-datanode1`, `agri-datanode2`, `agri-datanode3`).
- **Replication factor 3** → Ensures high availability and fault tolerance of datasets.
- **Storage Output:** Used as the sink for predictions (`/agri/streaming/real_anomaly_predictions`) and streaming checkpoints (`/agri/checkpoints/real_market_stream`).

## Spark (Distributed Processing)
- **DataFrames / SQL** → Used universally across all pipelines for structured data processing and massive scale price analytics.
- **Window Functions** → Used to generate temporal features (7-day rolling averages) during feature engineering.
- **Structured Streaming** → Real-time processing of unbounded Kafka events into HDFS. Keyed state (`flatMapGroupsWithState`) maintains the recent observations in real-time. *(Note: Watermarking is not utilized in this specific logic).*

## Kafka (Event Transport)
- **Transport Mechanism** → Used as a real-time event transport layer to decouple data ingestion from ML scoring (not a database).
- **Producer/Consumer Flow** → Real records replayed into `agri-market-real-replay` and processed by Spark Structured Streaming.

## MLlib (Machine Learning)
- **Random Forest** → Spark MLlib Random Forest (100 trees, max depth 14, max bins 128, threshold 0.35) with price deviation features for robust market anomaly detection.
- **Entity-Safe Sampling** → 1% deterministic entity-safe representative sample generated for ML pipelines to prevent memory saturation without compromising data structure.
- **Model Training** → 2024 validation split used for tuning, vs an untouched 2025+ temporal test split (48,354 records) used for official final metrics. 
- **Official Final Test Metrics** → **Accuracy: 95.66%**, **Precision: 86.55%**, **Recall: 85.47%**, **F1-Score: 86.01%**, **False Positive Rate (FPR): 2.46%**, **ROC-AUC: 94.82%**, **PR-AUC: 86.15%**.
- **Viva Defense Point on Metrics** → All key metrics (Accuracy, Precision, Recall, and F1-Score) exceed 85%, confirming the model effectively captures real anomalies while keeping false alarms strictly under 2.5%.

## Dashboard Visualization
- **Streamlit** → Lightweight frontend reading from the real-time PySpark outputs in HDFS to visually analyze large-scale price metrics and real-time streaming anomaly detection.

*(Note: Forecasting is strictly excluded from the real-time anomaly detection pipeline. Apache Hadoop YARN and MapReduce are NOT used for execution; execution relies entirely on Apache Spark's native scheduler and engine).*
