# Big Data Analytics Final Project Review & Defense Master Guide
### Agricultural Commodity Price Forecasting and Farmer Decision Support System

> Corrected 2026-10-23: figures now come from docs/VERIFIED_METRICS.md; original wording preserved in Git commit 3926155.

This directory contains the presentation deliverables, slide decks, and defense guides formatted strictly according to the **Big Data Analytics Final Review 10-Slide Structure** for evaluator **Dr. Sreeja** (School of Artificial Intelligence, Amrita Vishwa Vidyapeetham).

> 📌 **Comprehensive Syllabus & Viva Guide:** For an exhaustive, pin-to-pin mapping of the entire project to Units 1 to 4 of the Big Data Analytics syllabus, see:  
> 👉 [**`docs/PROJECT_MASTER_SYLLABUS_AND_VIVA_GUIDE.md`**](file:///Users/kaush/Downloads/Agricultural_BigData_Project/docs/PROJECT_MASTER_SYLLABUS_AND_VIVA_GUIDE.md)

---

## 1. Presentation Deliverables & File Locations

| File | Purpose | Format |
|---|---|---|
| [**`Big_Data_Analytics_Final_Presentation.pptx`**](file:///Users/kaush/Downloads/Agricultural_BigData_Project/docs/presentation/Big_Data_Analytics_Final_Presentation.pptx) | **Primary PowerPoint Presentation** (16:9 widescreen, complete speaker notes on every slide), regenerated 2026-10-23 with verified figures | PPTX |
| `Big_Data_Analytics_Final_Presentation.pdf` | Vector PDF for projection/submission. **Removed from the working tree on 2026-10-23** because the old export contained withdrawn figures; regenerate it (see below). The old file remains in Git history | PDF |
| [**`PROJECT_MASTER_SYLLABUS_AND_VIVA_GUIDE.md`**](file:///Users/kaush/Downloads/Agricultural_BigData_Project/docs/PROJECT_MASTER_SYLLABUS_AND_VIVA_GUIDE.md) | **Exhaustive Viva & Syllabus Master Guide** (Units 1–4, DAG analysis, 10 CPU cores, viva Q&A) | Markdown |
| [`generate_deck.py`](file:///Users/kaush/Downloads/Agricultural_BigData_Project/docs/presentation/generate_deck.py) | **Executable Source Script** regenerating the PPTX; with `--pdf` also the PDF, PNG slide previews and montage | Python (`python-pptx`, PIL) |
| [`AG-DATA-presentation.tex`](file:///Users/kaush/Downloads/Agricultural_BigData_Project/docs/presentation/AG-DATA-presentation.tex) | **LaTeX Beamer Source** (Overleaf-ready; compiles with `pdfLaTeX` or `tectonic`) | TeX |
| `preview/slide-01.png` ... `slide-10.png`, `preview/slides_montage.png` | Slide previews. **Removed from the working tree on 2026-10-23** (they showed withdrawn figures); regenerate with `--pdf` | PNG |

### Regenerating the deck, PDF and previews

```bash
cd docs/presentation
python3 generate_deck.py          # PPTX only (non-interactive; python-pptx is in system python3, not .venv)
python3 generate_deck.py --pdf    # also PDF via Apple Keynote (opens Keynote through AppleScript), then
                                  # preview/slide-NN.png via /opt/homebrew/bin/pdftoppm and preview/slides_montage.png
```

Alternatively, open the PPTX in Keynote or PowerPoint, export to `Big_Data_Analytics_Final_Presentation.pdf`, and run
`pdftoppm -png -r 150 Big_Data_Analytics_Final_Presentation.pdf preview/slide`.

---

## 2. Pin-to-Pin Syllabus Mapping (Units 1 to 4)

| Syllabus Unit | Core Academic Topics | Implementation in AG-DATA Project |
|---|---|---|
| **Unit 1: Big Data & Hadoop** | 5 Vs of Big Data, State-of-the-Art Platforms, Hadoop HDFS, Mapper/Reducer | 75.98M raw archive rows, 82.1M silver v2 rows (Volume); daily reports through Kafka (Velocity); archive CSV + official data.gov.in API records (Variety); quality rules, de-duplication, quarantine, and the finding that the archive mirror holds only 30% of official reports after Sept 2025 (Veracity); evaluated price forecasts and decision cards for farmers (Value). 4-container HDFS in Docker with replication 3 and 128 MB blocks. Map-side partial aggregation and reduce-side window grouping. |
| **Unit 2: Functional Programming in Scala** | Immutability, Type Hierarchy, Higher-Order Functions, Closures, Concurrency | Immutable DataFrame pipelines built from `val`s; case classes for model specs (`ForecastModels.GBT`, `RF`, `LR`), metrics (`ForecastEval.Metric`) and horizons (`ForecastConfig.Horizon`); higher-order functions (`.map(col)`, `SparkSetup.timed`, `foreachBatch`); driver-to-worker closure serialization; 10 CPU execution threads via `local[*]`. |
| **Unit 3: Spark Architecture & DAG** | RDDs vs DataFrames vs Datasets, Transformations & Actions, Catalyst, Tungsten, DAG | Untyped `DataFrame` for Catalyst optimization and Tungsten binary memory (`UnsafeRow`); lazy evaluation (lineage); narrow vs wide transformations; `Window.partitionBy(entity)` creates the shuffle boundaries in the feature job; AQE coalesces the 64 shuffle partitions. |
| **Unit 4: Spark MLlib & Case Study** | MLlib Pipeline, regression models, temporal split, commodity case study | Spark `Pipeline`s (`VectorAssembler` + `LinearRegression` / `RandomForestRegressor` / `GBTRegressor`), fitted on training rows only. Chronological split: train origins 2016–2023, validation 2024, test 2025-01 → 2026-04 scored once. Relative MAE vs persistence 0.971 / 0.953 / 0.938 / 0.923 (next / 3 / 7 / 14 days), 80% intervals cover 78.6–80.5%. Decision cards SELL / HOLD / WATCH / COMPARE. |

---

## 3. Strict 10-Slide Rubric Alignment & Presenter Script

**Target Duration:** 15 Minutes Presentation + 10 Minutes Viva Voce

| Slide | Faculty Rubric Requirement | Time | Presenter Script & Key Technical Focus |
|:---:|---|:---:|---|
| **1** | Title, Team Members, Register Numbers, Faculty Name | 1.0 min | *"Good morning Dr. Sreeja. Our project is Agricultural Commodity Price Forecasting and Farmer Decision Support using Hadoop HDFS and Apache Spark. Our team members are Rishitha, Karthikeya, Ashwin, and Kaushal. We built an end-to-end Big Data pipeline over 75.98 million archived mandi reports plus 7.7 million official records, and we forecast mandi prices 1 to 14 days ahead."* |
| **2** | Problem Statement, Objectives, Why Big Data is Needed | 1.5 min | *"A farmer deciding when and where to sell needs to know what the mandi is likely to quote. We forecast the modal price for 36 commodities across 11,845 mandi series, with 80% prediction intervals, and turn the forecasts into cautious SELL, HOLD, WATCH and COMPARE cards. Computing leakage-safe window features over tens of millions of reports does not fit single-node Pandas on a 16 GB laptop; we use HDFS for replicated storage and Spark for parallel compute."* |
| **3** | Dataset Specifications, Scale & Attributes | 1.5 min | *"The archive has 75.98 million raw rows; after quality rules and de-duplication the silver layer has 75.64 million. We back-filled 7.72 million official records from data.gov.in for 2025-10-01 to 2026-10-22, giving a silver v2 layer of 82.1 million rows. The back-fill showed the archive mirror holds only 30% of official reports after September 2025. The forecast panel has 21.06 million feature rows."* |
| **4** | System Architecture Diagram | 2.0 min | *"Our system is dual-path: a batch path for silver, features, models and the gold serving tables, and a streaming path from Kafka through Structured Streaming to bronze, quarantine, silver and alerts. HDFS runs 1 NameNode and 3 DataNodes in Docker with replication factor 3. Spark runs on host CPU cores in `local[*]` mode; HDFS DataNodes store blocks, they do not execute Spark tasks."* |
| **5** | Spark Workflow, DataFrames, DAG, Partitioning & Caching | 2.5 min | *"We use DataFrames rather than RDDs to exploit Catalyst optimization (predicate pushdown, projection pruning) and Tungsten whole-stage code generation. Transformations are lazy; actions compile the DAG into stages at shuffle boundaries. In the feature job, `Window.partitionBy(entity)` creates a ShuffleExchange; we use 64 shuffle partitions, coalesced by AQE."* |
| **6** | Scala Implementation & Core Code Snippets | 2.0 min | *"Every feature window ends at the current report or earlier and every target starts strictly after it, expressed with `rangeBetween` on an integer day number. A perturbation test fails if any feature reads the future. In streaming, invalid messages are quarantined before the 10-day watermark, and re-sends are dropped by content hash."* |
| **7** | Spark MLlib Pipeline, Features & Tuning | 1.5 min | *"We compare persistence, moving-average and seasonal baselines with MLlib linear regression, random forests and gradient-boosted trees. Train origins are 2016–2023, models are chosen on 2024, and the 2025-01 to 2026-04 test is scored once. Absolute-loss GBT is selected for next and 3 days, random forest for 7 and 14 days. Conformal intervals are calibrated on 2024."* |
| **8** | Results, Metrics Table & Business Insight | 2.0 min | *"Relative MAE against persistence is 0.971, 0.953, 0.938 and 0.923 for next, 3, 7 and 14 days; all Diebold–Mariano p-values are below 1e-21. 80% intervals cover 78.6 to 80.5%. Frozen models on six months of new data, April to October 2026, still score 0.952 to 0.963. Anomaly flags reach PR-AUC 0.704 on injected corruptions versus 0.352 for the old IQR rule. The Kafka replay delivered 20,000 of 20,000 valid messages with 0 parity mismatches and a 1.69 s median latency."* |
| **9** | Challenges, Limitations, Conclusion & Future Work | 1.0 min | *"Persistence is hard to beat: 17 to 34% of price changes are exactly zero, so our gains are modest, 3 to 8%, but significant. We audited and withdrew the v1 anomaly-classifier metrics, which no code produced. Spark runs in `local[*]` mode on one laptop; HDFS replicas share one disk; there is no public deployment."* |
| **10** | References, GitHub Repository & Deliverables | 0.5 min | *"Our project evidence, results files and code are on GitHub at `github.com/kaushalrog/AG-DATA`; every number we quoted is in `docs/VERIFIED_METRICS.md`. Thank you Dr. Sreeja. We are now open for viva questions."* |

> **What changed and why.** The v1 script (Git commit 3926155) presented an anomaly classifier with very high accuracy/precision/recall figures and Kafka throughput/latency numbers. No code or log in the repository produces those figures, so they were withdrawn (see `docs/AUDIT_PRIOR_RESULTS.md` and `docs/VERIFIED_METRICS.md` §6). The slides now lead with the price-forecasting results.

---

## 4. Live Demo Commands for Dr. Sreeja

```bash
# 1. Show 3 live HDFS DataNodes and replication factor 3
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
docker exec -it agri-namenode hdfs dfsadmin -report
docker exec -it agri-namenode hdfs fsck /agri/silver/daily_market_prices -files -blocks -locations

# 2. Launch interactive Spark shell on all 10 Apple Silicon CPU cores
/opt/miniconda3/bin/spark-shell \
  --master "local[*]" \
  --driver-memory 4g \
  --conf "spark.sql.shuffle.partitions=64" \
  --conf "spark.driver.host=127.0.0.1" \
  --conf "spark.driver.extraJavaOptions=--add-opens=java.base/java.lang=ALL-UNNAMED --add-opens=java.base/java.util=ALL-UNNAMED --add-opens=java.base/sun.util.calendar=ALL-UNNAMED"

# 3. Serve the PWA (FastAPI + DuckDB, read-only gold tables), then open http://localhost:8000
PYTHONPATH=py .venv/bin/uvicorn agri.api.app:app --app-dir py --port 8000

# 4. (Legacy) Streamlit dashboard showing the verified figures
streamlit run src/dashboard/app.py --server.port 8501
```

---

## 5. Spark Web UI, DAG, Partitions & CPU Cores (Viva Answers)

- **How to Open Spark UI:** Open `http://localhost:4040` in your web browser while Spark is running.
- **DAG Breakdown in UI:**
  - **Blue Outer Boxes:** Represent **Stages**. A new stage begins whenever a wide transformation (ShuffleExchange) occurs.
  - **Inner Nodes:** Represent RDDs/Operations (`Scan parquet`, `Filter`, `Project`, `Exchange`, `WholeStageCodegen`).
  - **`Exchange` Node:** Indicates a shuffle where data was hashed and redistributed across partitions.
  - **`WholeStageCodegen` Box:** Represents the **Tungsten Engine**, compiling multiple operations into a single optimized Java loop.
- **Partitions:**
  - File input partitions: based on `spark.sql.files.maxPartitionBytes` (128 MB by default).
  - Shuffle partitions: 64 in the forecast jobs (`spark.sql.shuffle.partitions = 64`), coalesced at runtime by AQE. Spark's default is 200.
- **How Laptop CPU Cores Are Used:**
  - Apple Silicon (M5) Mac with **10 CPU cores** (`Runtime.getRuntime.availableProcessors()` = 10).
  - Spark spawns **10 parallel worker execution threads** inside the JVM.
  - Illustration: a stage with 64 tasks runs in ⌈64 / 10⌉ = 7 waves (six full waves of 10 tasks and one of 4).
  - Visible in Spark UI under the **"Executors"** tab → "driver" row shows **Cores: 10**.
  - Measured: on the full 75.6 M rows, 10 cores give a 2.4× (W1 aggregate) and 3.0× (W2 window features) speed-up over 1 core (`results/scalability/runs.jsonl`).

---

## 6. Port & Localhost Directory

| Port | Service / Web UI | Operational Role |
|:---:|---|---|
| **`http://localhost:9870`** | **HDFS NameNode Web UI** | Cluster health, 3 DataNodes, block replication status. |
| **`http://localhost:4040`** | **Spark Application Web UI** | Live Spark jobs, DAG visualization, stages, tasks, 10 CPU executor cores, Tungsten codegen. |
| **`http://localhost:8000`** | **FastAPI + PWA** | Forecasts, intervals, decision cards and alerts from the gold tables (read-only). |
| **`http://localhost:8501`** | **Streamlit Dashboard (legacy)** | Verified headline figures and historical aggregates. |
| **`localhost:9000`** | **HDFS RPC (`fs.defaultFS`)** | Inter-process protocol used by Spark to read/write Parquet files to HDFS. |
| **`localhost:9092`** | **Apache Kafka Broker** | Event transport for topic `agri.prices.v1` (6 partitions). |

These ports are for a private network only (`docs/ARCHITECTURE.md`, Security boundaries).

---

## 7. Direct Viva Voce Q&A Cheat Sheet

- **Diff b/w Hadoop and DAG:** Hadoop MapReduce is a rigid 2-stage (Map → Reduce) disk-bound model writing intermediate results to disk. A DAG is an arbitrary directed acyclic graph of multi-stage transformations that Spark pipelines in memory where possible, which is much faster for iterative and multi-pass workloads.
- **How many Jobs in this code:** Each Action triggers at least one Job (`count`, `write.parquet`, `fit`, ...). Read the exact count for a run in the Spark UI "Jobs" tab.
- **How many Stages in this code:** Stages are delimited by shuffle boundaries (wide transformations such as `Window.partitionBy(entity)` in `BuildForecastFeatures`). Read the exact count for a run in the Spark UI "Stages" tab.
- **How many Tasks in this code:** Tasks = Σ (partitions in stage i). Shuffle stages start with 64 tasks (before AQE coalescing).
- **How you find Stages or Tasks:** Stage boundary = ShuffleExchange (Wide Transformation). Task count = partition count of that stage (Spark UI, Stages tab).
- **Diff b/w Wide and Narrow Transformations:**
  - Narrow: 1-to-1 partition mapping (`filter`, `select`, `withColumn`), no shuffle, executed in a single stage.
  - Wide: M-to-N partition mapping (`Window.partitionBy`, `groupBy`, `distinct`), requires a shuffle exchange, forces a new stage.
- **How many Actions in this code:** `.count()`, `.write.parquet()`, `.show()`, `.collect()`, `pipeline.fit()`, `model.transform().write()`, `writeStream.start()`.
- **Diff b/w Lineage Graph and DAG:** Lineage Graph is the logical history of transformations (blueprint for fault tolerance). DAG is the physical execution plan created by the DAGScheduler, breaking lineage into stages and tasks.
- **What cluster you are using:** Spark in `local[*]` mode with 10 CPU worker threads on an Apple Silicon Mac, with a 4-container Dockerized HDFS (1 NameNode + 3 DataNodes, replication 3). A 2-worker Docker Spark cluster on the same host was also benchmarked (11.27 M rows: W1 9.2 s, W2 14.4 s).
- **DataFrame vs Dataset API:** DataFrames (`Dataset[Row]`) leverage the Catalyst optimizer and Tungsten binary memory (`UnsafeRow`); the project uses DataFrames throughout, including Structured Streaming (`PriceEventStream`).
- **What is an RDD:** Resilient Distributed Dataset. Fault-tolerant (recomputable via lineage), partitioned across CPU cores/nodes, immutable collection of JVM objects.
- **Higher-Order Functions:** Functions taking functions as arguments or returning functions: `.map(col)`, `SparkSetup.timed[T](label)(body: => T)`, `foreachBatch(processBatch _)` in `PriceEventStream`.
- **Why is the improvement over persistence only 3–8%?** Persistence ("last price") is a hard baseline: 17–34% of target changes are exactly zero because mandis re-quote prices. Squared-loss models do not beat it at the next-report horizon; absolute-loss GBT does. The gains are small but significant (DM p ≤ 1.3e-22) and hold on 58.5–76.4% of series and on six months of unseen data.
- **What happened to the 95%-accuracy anomaly model?** It was withdrawn. No code or log produces those figures, the v1 labels were functions of the features, and its outlier bounds were fitted on the test years (`docs/AUDIT_PRIOR_RESULTS.md`). Anomaly flags are now evaluated only on injected corruptions (PR-AUC 0.704 vs 0.352 for the legacy IQR rule); no accuracy on real anomalies is claimed.

## Corrected PDF deck
`AG-DATA-presentation.pdf` (10 slides) is compiled headlessly from `AG-DATA-presentation.tex` with `tectonic -X compile AG-DATA-presentation.tex`, and `preview/beamer-*.png` with `pdftoppm -png -r 80`. Both contain only figures from `docs/VERIFIED_METRICS.md`. The PowerPoint deck is regenerated with `python3 generate_deck.py`; its PDF export (`--pdf`) needs Keynote.
