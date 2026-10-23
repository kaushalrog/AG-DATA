# Comprehensive Project Viva, Concept & Defense Master Guide
### Agricultural Commodity Price Forecasting and Farmer Decision Support System

> Corrected 2026-10-23: figures now come from docs/VERIFIED_METRICS.md; original wording preserved in Git commit 3926155.

**Course:** 23AID302 — Big Data Analytics  
**Faculty Guide & Evaluator:** **Dr. Sreeja** | School of Artificial Intelligence, Amrita Vishwa Vidyapeetham  
**Team Members:** C Rishitha (`CB.AI.U4AID24109`), Karthikeya Y (`CB.AI.U4AID24163`), Ashwin Tyagi (`CB.AI.U4AID24167`), Kaushal S (`CB.AI.U4AID24168`)  
**Hardware Profile:** Apple Silicon Mac (10 CPU Cores, 16 GB Unified Memory)  
**Software Toolchain:** Apache Spark 4.2.0, OpenJDK 21.0.12, Scala 2.13.18, Hadoop HDFS 3.4.1, Apache Kafka 4.3  

---

## 📑 Table of Contents
1. [Mapping Project to Course Syllabus (Units 1 to 4)](#1-mapping-project-to-course-syllabus-units-1-to-4)
2. [What We Did, How We Did It & Why: Step-by-Step Engineering Rationale](#2-what-we-did-how-we-did-it--why-step-by-step-engineering-rationale)
3. [Live Viva Presentation Playbook for Dr. Sreeja](#3-live-viva-presentation-playbook-for-dr-sreeja)
4. [Live Terminal Commands & Spark Demo Guide](#4-live-terminal-commands--spark-demo-guide)
5. [In-Depth Spark UI, DAG, Partitions & CPU Core Analysis](#5-in-depth-spark-ui-dag-partitions--cpu-core-analysis)
6. [Port & Localhost Directory](#6-port--localhost-directory)
7. [Comprehensive Viva Voce Q&A Master Repository](#7-comprehensive-viva-voce-qa-master-repository)

---

## 📚 1. Mapping Project to Course Syllabus (Units 1 to 4)

Your faculty evaluator, **Dr. Sreeja**, evaluates projects strictly against the **23AID302 Big Data Analytics** syllabus. Here is the exact, pin-to-pin alignment:

```
┌───────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ UNIT 1: INTRODUCTION TO BIG DATA ANALYTICS & HADOOP ECOSYSTEM                                         │
├──────────────────────────────────┬────────────────────────────────────────────────────────────────────┤
│ Syllabus Topic                   │ Implementation in Our Project                                      │
├──────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
│ Definition & Characteristics     │ The 5 Vs of Mandi Big Data: 75.98M raw / 82.1M silver v2 rows      │
│ (The 5 Vs of Big Data)           │ (Volume), Kafka topic agri.prices.v1 (Velocity), archive CSV +     │
│                                  │ data.gov.in API (Variety), quality rules, dedup, quarantine and    │
│                                  │ 30% archive coverage found (Veracity), price forecasts (Value).    │
│ Tools & Technologies             │ Hadoop HDFS 3.4.1 (storage), Apache Spark 4.2.0 (compute),         │
│                                  │ Apache Kafka (event bus), Docker (reproducible cluster).           │
│ Hadoop Ecosystem & HDFS          │ Distributed block storage (1 NameNode + 3 DataNodes), replication  │
│                                  │ factor 3, 128 MiB block size, 692 MB silver layer, year= pruning.  │
│ MapReduce Conceptual Link        │ How composite business-key deduplication and window aggregations   │
│ (Mapper & Reducer)               │ implement map-side partial combine and reduce-side shuffle sort.   │
└──────────────────────────────────┴────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ UNIT 2: FUNCTIONAL PROGRAMMING (FP) & SCALA CONCEPTS                                                  │
├──────────────────────────────────┬────────────────────────────────────────────────────────────────────┤
│ Syllabus Topic                   │ Implementation in Our Project                                      │
├──────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
│ Immutability vs Mutability       │ Strict usage of `val` over `var` in Spark DataFrame pipelines;     │
│                                  │ immutable transformations prevent multi-threaded race conditions.  │
│ Scala Type Hierarchy             │ `sealed trait Spec` with case classes `GBT`, `RF`, `LR` (AnyRef),  │
│ (`Any`, `AnyVal`, `AnyRef`)      │ pattern matching on model specs and `Option`/`getOrElse` safety.   │
│ Higher-Order Functions           │ `.map(col)`, `.filter()`, `SparkSetup.timed(label)(body)`, and     │
│                                  │ passing `processBatch` into `foreachBatch()`.                      │
│ Closures & Driver-Worker State   │ Driver serializes transformation closures to executor threads.     │
│ OOP in Scala                     │ Singleton objects (`SparkSetup`, `Features`, `Deduplicate`);       │
│                                  │ sealed traits and case classes for model specs and metrics.        │
│ Concurrency & Multithreading     │ JVM thread pools on Apple Silicon 10-core CPU via `local[*]`.      │
└──────────────────────────────────┴────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ UNIT 3: SPARK ARCHITECTURE, DATASETS/DATAFRAMES & DAG                                                 │
├──────────────────────────────────┬────────────────────────────────────────────────────────────────────┤
│ Syllabus Topic                   │ Implementation in Our Project                                      │
├──────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
│ Spark Architecture & Cluster     │ Driver Program coordinates execution; Executor threads run tasks;  │
│ Execution Modes                  │ `local[*]` allocates 1 worker thread per available physical core.  │
│ RDDs vs DataFrames vs Datasets   │ Untyped `DataFrame` (`Dataset[Row]`) for Catalyst SQL code-gen;    │
│                                  │ typed `Dataset[T]` only in the legacy v1 stream.                   │
│ Catalyst Query Optimizer         │ Logical plan analysis, predicate pushdown, projection pruning,     │
│ & Tungsten Engine                │ off-heap binary memory (`UnsafeRow`), whole-stage Java bytecode gen│
│ Transformations vs Actions       │ Lazy evaluation: transformations record DAG lineage; actions       │
│                                  │ (`count`, `write.parquet`, `fit`) trigger physical job execution.  │
│ Narrow vs Wide Transformations   │ Narrow: `filter`, `select`, `withColumn` (in-memory pipeline).     │
│ & Shuffle Boundaries             │ Wide: `Window.partitionBy`, `groupByKey` (network shuffle exchange)│
│ Directed Acyclic Graph (DAG)     │ DAGScheduler breaks logical plans into Stages at shuffle boundaries│
│ & Task Scheduling                │ TaskScheduler dispatches tasks 1:1 per partition across 10 cores.  │
└──────────────────────────────────┴────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ UNIT 4: MACHINE LEARNING WITH SPARK MLLIB & REAL-TIME STREAMING                                       │
├──────────────────────────────────┬────────────────────────────────────────────────────────────────────┤
│ Syllabus Topic                   │ Implementation in Our Project                                      │
├──────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
│ MLlib Pipeline Architecture      │ `Pipeline`s: `VectorAssembler` -> `GBTRegressor` /                 │
│                                  │ `RandomForestRegressor`; encoders + scaler -> `LinearRegression`.  │
│ Feature Engineering              │ Leakage-safe windows per series: returns, 7/30/90-day means and    │
│                                  │ stddevs, 30-day range, last-year deviation, spread, calendar.      │
│ Baselines & Model Choice         │ Persistence, moving average, seasonal naive; chosen on 2024:       │
│                                  │ absolute-loss GBT (next, 3 d), random forest (7, 14 d).            │
│ Strict Temporal Splitting        │ Train origins 2016-23, validation 2024, test 2025-01..2026-04 once;│
│ (purged on target dates)         │ rel. MAE vs persistence 0.971 / 0.953 / 0.938 / 0.923.             │
│ Case Study: Farmer Decision      │ 80% conformal intervals (coverage 78.6-80.5%) and cautious         │
│ Support & Event Streaming        │ SELL/HOLD/WATCH/COMPARE cards; Kafka -> Structured Streaming.      │
└──────────────────────────────────┴────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ 2. What We Did, How We Did It & Why: Step-by-Step Engineering Rationale

When Dr. Sreeja asks: *"Walk me through the pipeline. What did you build, how did you implement it, and why did you choose that design?"*, explain using these 7 sequential stages:

### Stage 1: Raw Ingestion and Official Back-fill
- **What:** Ingested the AGMARKNET daily-price archive (Kaggle mirror, 2001–2026): **75,984,017 raw rows**. Back-filled **7,720,662 official records** from data.gov.in for 2025-10-01 → 2026-10-22 (387 days, 0 failed days).
- **How:** Explicit `StructType` schemas in Scala with RFC-4180 quote-escaping, so embedded commas (e.g., `"Sesamum (Sesame,Gingelly,Til)"`) cannot corrupt column alignment. The API adapter retries, rate-limits and keeps delivery-tied checkpoints.
- **Why:** Schema inference needs an extra full pass over the raw text and can guess wrong types. The back-fill found that the archive mirror holds only **30.0%** of official reports for 2025-10-01 → 2026-04-21; where both have a record, 99.33% of modal prices agree.

### Stage 2: Distributed Replicated Storage in Apache Hadoop HDFS
- **What:** Deployed an HDFS cluster inside Docker container services.
- **How:** Configured 1 NameNode (`agri-namenode` on port 9000/9870) and 3 DataNodes (`agri-datanode1`, `agri-datanode2`, `agri-datanode3`) with **Replication Factor = 3** and **128 MiB block sizes**. The 692 MB silver layer was loaded and reported HEALTHY.
- **Why:** 
  1. *Fault Tolerance:* With one DataNode stopped, a probe file was still read in full with an identical checksum. Caveat: the three DataNodes share one physical disk, so this shows HDFS behaviour, not hardware durability; there is a single NameNode (no HA).
  2. *Block Sizing:* 128 MiB blocks suit sequential columnar reads. Our silver files are small (about 0.4 MB each), so compaction is recommended before production (`results/hdfs/summary.md`).

### Stage 3: Resilient Date Normalization & Multi-Source Cleansing
- **What:** Standardized 25 years of date strings across conflicting formatting conventions.
- **How:** Used Spark SQL's `coalesce` wrapping non-fatal `try_to_date` patterns:
  ```scala
  coalesce(
    try_to_date(col("Reported Date"), "dd MMM yyyy"),
    try_to_date(col("Reported Date"), "yyyy-MM-dd"),
    try_to_date(col("Arrival_Date"), "dd/MM/yyyy")
  )
  ```
- **Why:** Standard `to_date()` throws on malformed strings under the corrected parser policy and aborts the job; `try_to_date` yields `null`, so the quality rules can filter the row instead.

### Stage 4: Composite Business-Key Deduplication
- **What:** Removed duplicate reports: the archive silver layer keeps **75,644,801** of the 75,984,017 raw rows after quality rules and de-duplication.
- **How:** Avoided naive `df.distinct()`. Partitioned over the composite business key (`DataQuality.businessKey`: state, district, market, commodity, variety, date), ordered deterministically by validity, and kept `row_number() === 1`.
- **Why:** A whole-row `distinct()` keeps near-duplicates that differ in non-key columns. A deterministic `row_number()` keeps exactly one reproducible row per report.

### Stage 5: Leakage-Safe Window Features and Targets
- **What:** Built **21.06 M feature rows** for **11,845 price series** across **36 commodities**.
- **How:** Spark SQL windows over an integer day number (`forecast/Features.scala`):
  ```scala
  private def byEntity = Window.partitionBy(EntityId).orderBy(col(Day))
  private def days(lo: Long, hi: Long) = byEntity.rangeBetween(lo, hi)
  .withColumn("mean30", avg(lp).over(days(-29, 0)))   // window ends at the current report
  .withColumn("std90",  stddev_samp(lp).over(days(-89, 0)))
  ```
  The target is the log return to a report strictly after the origin: $y = \ln P_{t+h} - \ln P_t$.
- **Why:** Every feature window ends at the current report or earlier and every target starts after it. `ForecastFeaturesSpec` perturbs future rows and fails if any feature changes, so lookahead leakage is tested, not assumed.

### Stage 6: Distributed Machine Learning with Spark MLlib
- **What:** A forecasting benchmark for next / 3 / 7 / 14 days: persistence, moving-average and seasonal-naive baselines vs MLlib linear regression, random forests and gradient-boosted trees.
- **How:** Each model is a Spark `Pipeline` fitted on a sample of at most 2 M training rows per horizon (train origins 2016–2023); model choice and split-conformal intervals use 2024; the 2025-01-01 → 2026-04-20 test is scored once. Selected: GBT with absolute loss on a percent target (depth 7, 150 iterations, step 0.5) for next and 3 days; random forest (60 trees, depth 10) for 7 and 14 days.
- **Why:** Tree ensembles capture non-linear, commodity-specific dynamics in one global model. Results (relative MAE vs persistence): **0.971 / 0.953 / 0.938 / 0.923**, Diebold–Mariano p ≤ 1.3e-22, 80% coverage 78.6–80.5%. Frozen models on 2026-04-22 → 2026-10-22: **0.963 / 0.955 / 0.958 / 0.952**.

### Stage 7: Event Streaming via Apache Kafka & Structured Streaming
- **What:** An incremental path for daily reports, demonstrated by replaying real archived reports with labelled fault injection, and by one live current-day pull (4/4 records to silver on 2026-10-23).
- **How:** Producer → Kafka topic `agri.prices.v1` (6 partitions, key = business key) → `PriceEventStream`: bronze (raw + offsets), quarantine for invalid messages before a 10-day watermark, de-duplication by `event_id`, `foreachBatch` silver sink, and alerts. Replay: 21,524 messages = 20,000 to silver + 1,317 duplicates removed + 207 quarantined; 0 missing; batch/stream parity 0 mismatches; producer→sink p50 1.69 s.
- **Why:** Decouples ingestion from processing with checkpointed offsets: effectively-once output per offset range. End-to-end exactly-once from the government source to the app is not claimed. Forecasts are recomputed in batch, so there is a single feature implementation.

### What changed and why (v1 anomaly classifier withdrawn)
Earlier versions of this guide described Stage 6 as a Random Forest anomaly classifier and quoted very high test accuracy, precision, recall and F1 on a "2025+ test set", plus Kafka throughput and latency figures. No code or log in the repository produces those figures, so they are **withdrawn** (`docs/AUDIT_PRIOR_RESULTS.md`, `docs/VERIFIED_METRICS.md` §6). The v1 labels were functions of the features and its outlier bounds were fitted on the test years, so it was not leakage-free either. Anomaly flags are now evaluated only on injected corruptions (PR-AUC 0.704 vs 0.352 for the legacy IQR rule), with no accuracy claimed for real anomalies.

---

## 🎤 3. Live Viva Presentation Playbook for Dr. Sreeja

Use this exact timing and structure during your 15-minute presentation:

| Slide / Section | Time | What to Say (Presenter Script) | Core Concept to Emphasize |
|:---:|:---:|---|---|
| **Slide 1: Title & Framing** | 1.0 min | *"Good morning Dr. Sreeja. Our project is Agricultural Commodity Price Forecasting and Farmer Decision Support using Hadoop HDFS and Apache Spark. Our team members are Rishitha, Karthikeya, Ashwin, and Kaushal. We built an end-to-end Big Data pipeline over 75.98 million archived mandi reports and 7.7 million official records, forecasting mandi prices 1 to 14 days ahead and streaming daily reports through Kafka."* | Distributed pipeline, forecasting target. |
| **Slide 2: Problem & 5 Vs** | 1.5 min | *"A farmer deciding when and where to sell needs to know what the mandi is likely to quote. We forecast the modal price for 36 commodities across 11,845 mandi series, with 80% intervals, and turn the forecasts into cautious SELL, HOLD, WATCH and COMPARE cards. Leakage-safe window features over tens of millions of reports do not fit single-node Pandas on a 16 GB laptop, so we use HDFS and Spark."* | Pandas limits vs Distributed HDFS + Spark. |
| **Slide 3: Datasets & Scale** | 1.5 min | *"The archive has 75.98 million raw rows and 75.64 million after quality rules and de-duplication. The official back-fill adds 7.72 million records, giving a silver v2 layer of 82.1 million rows, and showed that the archive mirror holds only 30% of official reports after September 2025. The forecast panel has 21.06 million feature rows."* | Transparent data-layer breakdown. |
| **Slide 4: Architecture** | 2.0 min | *"Our system architecture is dual-path: a batch pipeline for silver, features, models and gold tables, and a streaming pipeline via Kafka and Structured Streaming to bronze, quarantine, silver and alerts. HDFS runs 1 NameNode and 3 DataNodes in Docker with replication factor 3. Spark executes on host CPU cores in `local[*]` mode. HDFS DataNodes store blocks; they are not Spark compute executors."* | Dual-path workflow; Docker HDFS vs local Spark. |
| **Slide 5: Spark DAG & Engine** | 2.5 min | *"We use DataFrames rather than RDDs to exploit Catalyst optimization and Tungsten whole-stage code generation. Transformations are lazy; actions trigger physical DAG execution. Wide transformations like `Window.partitionBy(entity)` create shuffle boundaries; we use 64 shuffle partitions, coalesced by AQE. On the full 75.6 million rows, 10 cores give a 2.4 to 3.0× speed-up over one core."* | Catalyst, Tungsten, Narrow vs Wide, measured scaling. |
| **Slide 6: Scala Implementation** | 2.0 min | *"In Scala, `coalesce` with `try_to_date` stops corrupt dates from aborting batch jobs. A deterministic `row_number()` over the business key removes duplicates. Feature windows end at the current report and targets start after it, and a perturbation test enforces this. In streaming, invalid messages are quarantined before the watermark."* | Resilient parsing, dedup, leakage tests. |
| **Slide 7: ML Pipeline** | 1.5 min | *"We compare persistence, moving-average and seasonal baselines with MLlib LR, random forest and GBT. Train origins are 2016–2023, models are chosen on 2024, and the 2025-01 to 2026-04 test is scored once. Absolute-loss GBT wins at next and 3 days, random forest at 7 and 14 days."* | Temporal split, baselines, model choice. |
| **Slide 8: Results & Metrics** | 2.0 min | *"Relative MAE against persistence is 0.971, 0.953, 0.938 and 0.923; every Diebold–Mariano p-value is below 1e-21; 80% intervals cover 78.6 to 80.5%. Frozen models on six unseen months score 0.952 to 0.963. Anomaly flags reach PR-AUC 0.704 on injected corruptions against 0.352 for the old IQR rule. The Kafka replay delivered all 20,000 valid messages with 0 parity mismatches and a 1.69 s median latency."* | Relative MAE, DM test, coverage, replay. |
| **Slide 9: Challenges & Limits** | 1.0 min | *"Persistence is hard to beat: 17 to 34% of price changes are exactly zero, so our gains are modest, 3 to 8%, but significant. We audited and withdrew our v1 anomaly-classifier metrics. Spark runs in `local[*]` mode on one host, HDFS replicas share one disk, and there is no public deployment."* | Honest baselines, audit, boundaries. |
| **Slide 10: References** | 0.5 min | *"Our project evidence, results files and code are on GitHub at `github.com/kaushalrog/AG-DATA`, and every number is listed with its source in `docs/VERIFIED_METRICS.md`. Thank you, Dr. Sreeja. We are now open for viva questions."* | GitHub link, reproducibility. |

---

## 💻 4. Live Terminal Commands & Spark Demo Guide

Have these exact terminal commands ready to demonstrate live to Dr. Sreeja:

### Command 1: Inspect the Live HDFS Cluster & Replication Factor 3
Show Dr. Sreeja that HDFS is genuinely running with 3 DataNodes and replication factor 3:
```bash
# Check Docker containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Run HDFS admin report to show all 3 DataNodes live
docker exec -it agri-namenode hdfs dfsadmin -report

# Show HDFS block replication and Parquet storage of the silver layer
docker exec -it agri-namenode hdfs fsck /agri/silver/daily_market_prices -files -blocks -locations
```
*What to show her:* Point to **"Live datanodes (3)"** and **"Replication: 3"** in the terminal output.

---

### Command 2: Launch Spark in Local Mode with All 10 Laptop Cores
Show how to start an interactive Spark session leveraging all 10 cores on your Apple Silicon Mac:
```bash
/opt/miniconda3/bin/spark-shell \
  --master "local[*]" \
  --driver-memory 4g \
  --conf "spark.sql.shuffle.partitions=64" \
  --conf "spark.driver.host=127.0.0.1" \
  --conf "spark.driver.extraJavaOptions=--add-opens=java.base/java.lang=ALL-UNNAMED --add-opens=java.base/java.util=ALL-UNNAMED --add-opens=java.base/sun.util.calendar=ALL-UNNAMED"
```
*What to explain:* 
- `--master local[*]`: Tells Spark to use **all 10 CPU cores** as worker execution threads.
- `--driver-memory 4g`: Allocates 4 GB of JVM heap to the driver.
- `--conf spark.sql.shuffle.partitions=64`: Configures 64 partitions for wide transformations (as in the forecast jobs; Spark's default is 200).
- `--add-opens`: Bypasses Java 21 module reflection barriers.

---

### Command 3: Run Interactive Scala Code to Demonstrate Catalyst & DAG
Inside the `spark-shell`, paste this quick snippet to show Dr. Sreeja how Spark creates a DataFrame, optimizes the plan, and builds a DAG:
```scala
import org.apache.spark.sql.functions._
import org.apache.spark.sql.expressions.Window

// 1. Create a dummy market dataset in memory
val data = Seq(
  ("Maharashtra", "Pune", "Onion", "2025-01-01", 2500.0),
  ("Maharashtra", "Pune", "Onion", "2025-01-02", 2600.0),
  ("Maharashtra", "Pune", "Onion", "2025-01-03", 4200.0), // Spike!
  ("Karnataka", "Bangalore", "Tomato", "2025-01-01", 1800.0),
  ("Karnataka", "Bangalore", "Tomato", "2025-01-02", 1200.0)
).toDF("state", "market", "commodity", "date", "modal_price")

// 2. Define Window (Wide Transformation -> forces ShuffleExchange)
val w = Window.partitionBy("state", "market", "commodity").orderBy("date")
val dfFeatures = data
  .withColumn("prev_price", lag("modal_price", 1).over(w))
  .withColumn("price_jump", col("modal_price") - col("prev_price"))
  .filter(col("modal_price") > 1500.0) // Narrow Transformation (Predicate Pushdown)

// 3. Inspect the Catalyst Optimized Physical Plan
dfFeatures.explain(mode = "formatted")

// 4. Trigger Action (Executes DAG on local CPU cores!)
dfFeatures.show()
```

---

### Command 4: Serve the App (and the legacy Streamlit dashboard)
```bash
# In project root
PYTHONPATH=py .venv/bin/uvicorn agri.api.app:app --app-dir py --port 8000   # PWA + API
streamlit run src/dashboard/app.py --server.port 8501                       # legacy dashboard
```
Open your browser to: **`http://localhost:8000`**  
*What to show her:* a forecast with its 80% interval, the SELL / HOLD / WATCH / COMPARE card, and the language switch. The Streamlit dashboard shows the verified headline figures.

---

## 🔍 5. In-Depth Spark UI, DAG, Partitions & CPU Core Analysis

When Dr. Sreeja says: *"Open the Spark UI and explain the DAG, stages, tasks, partitions, and how your laptop cores were utilized"*, here is your complete breakdown:

### A. How to Open the Spark UI
1. While `spark-shell` or `spark-submit` is running, open your web browser to:
   👉 **`http://localhost:4040`**
2. If port 4040 is busy, Spark increments to `http://localhost:4041` or `http://localhost:4042`.

---

### B. What is a DAG and How to Show It in Spark UI
1. In the Spark UI top navigation bar, click on the **"Jobs"** tab or **"SQL/DataFrame"** tab.
2. Click on any completed Job description (e.g., `Job 0: count at ...` or `Job 1: parquet at ...`).
3. Expand the **"DAG Visualization"** accordion toggle.

#### Anatomical Breakdown of the DAG Visualization Boxes:
- **Blue Rectangles / Outer Containers:** Represent **Stages**. Every time a wide transformation occurs, a new blue stage container is drawn.
- **Inner Rounded Dots / Nodes:** Represent individual **RDDs / Transformations** (e.g., `Scan parquet`, `Filter`, `Project`, `Exchange`, `WholeStageCodegen`).
- **Arrows:** Show directional data dependencies (data flows downwards from parent RDDs to child RDDs).
- **`Exchange` Node:** This is the most important node in the DAG. It represents a **ShuffleExchange**, proving where Spark redistributed data across cluster partitions over the network/memory.
- **`WholeStageCodegen` Box:** Represents Spark's **Tungsten Engine**. It indicates that Spark compiled multiple transformation steps into a single optimized Java bytecode loop.

---

### C. In-Detail Analysis: Jobs vs Stages vs Tasks

Dr. Sreeja will specifically ask: *"How many jobs, stages, and tasks are in your code, and how do you know?"*

| Concept | What It Is | What Creates / Triggers It | Formula / Count in Our Project |
|---|---|---|---|
| **Job** | Highest-level execution unit | Triggered whenever an **Action** is invoked (`.count()`, `.write.parquet()`, `.collect()`, `model.fit()`). | **At least 1 Job per Action.** Read the exact count for a run in the Spark UI "Jobs" tab. |
| **Stage** | A sub-unit of a Job | Created at **Shuffle Boundaries** whenever a **Wide Transformation** occurs (`Window.partitionBy`, `groupByKey`, `repartition`). Narrow transformations are pipelined into the same stage. | **Roughly: shuffle exchanges + 1 per job.** In `BuildForecastFeatures`, `Window.partitionBy(entity)` creates the boundaries; the Stages tab gives the exact count. |
| **Task** | Smallest unit of execution | Represents the execution of a stage's logic on a **single data partition**. Dispatched to a worker thread. | **Total Tasks in Stage = Number of Partitions in that Stage.** Read stages follow the input splits; shuffle stages start with **64 tasks** (before AQE coalescing). |

---

### D. Partitions & How Your Laptop Cores Are Utilized

#### How Your Apple Silicon 10-Core CPU Executes Spark:
- **Hardware Cores:** Your Mac has an **Apple Silicon M-series chip with 10 CPU cores**.
- **Worker Threads:** Passing `--master local[*]` tells the JVM:
  $$\text{Execution Threads} = \text{Runtime.getRuntime.availableProcessors()} = 10$$
  Spark launches **1 Driver JVM** containing **10 parallel worker execution threads**.
- **Task Execution Waves (illustration):**
  - In a window-shuffle stage with `spark.sql.shuffle.partitions = 64`, Spark creates **64 Tasks** (before AQE coalescing).
  - Your 10 CPU cores execute at most **10 tasks simultaneously**.
  - Therefore the stage needs about **7 waves**:
    $$\text{Waves} = \left\lceil \frac{64 \text{ Tasks}}{10 \text{ Cores}} \right\rceil = 7$$
- **Measured:** on the full 75.6 M rows, 10 cores give a 2.4× (W1 aggregate) and 3.0× (W2 window features) speed-up over 1 core (`results/scalability/runs.jsonl`); shuffle and I/O keep it below 10×.
- **Proving this in the Spark UI:**
  - Click on the **"Executors"** tab in `http://localhost:4040`.
  - Look at the row named **"driver"**:
    - Under **"Cores"**, it explicitly displays **`10`**.
    - Under **"Active Tasks"**, during job execution, it will show up to **`10`** tasks running concurrently.

---

## 🌐 6. Port & Localhost Directory

Memorize this table for viva voce defense:

| Port | Service / Web UI | What It Shows Dr. Sreeja |
|:---:|---|---|
| **`http://localhost:9870`** | **HDFS NameNode Web UI** | Live cluster health, 3 connected DataNodes, total storage capacity, block replication status. |
| **`http://localhost:4040`** | **Spark Application UI** | Live Spark jobs, DAG visualization, stages, tasks, 10 executor cores, Tungsten whole-stage codegen. |
| **`http://localhost:8000`** | **FastAPI + PWA** | Forecasts, 80% intervals and SELL/HOLD/WATCH/COMPARE cards from read-only gold tables. |
| **`http://localhost:8501`** | **Streamlit Dashboard (legacy)** | Verified headline figures and historical aggregates. |
| **`localhost:9000`** | **HDFS RPC (`fs.defaultFS`)** | Underlying inter-process protocol used by Spark to read/write Parquet files to HDFS (`hdfs://localhost:9000/...`). |
| **`localhost:9092`** | **Apache Kafka Broker** | Event transport for topic `agri.prices.v1` (6 partitions). |

These ports are for a private network only (`docs/ARCHITECTURE.md`, Security boundaries).

---

## 💡 7. Comprehensive Viva Voce Q&A Master Repository

### Q1: What is the difference between Hadoop and DAG?
> **Defensible Answer:**  
> "Ma'am, **Hadoop** is an entire distributed framework consisting of **HDFS** for distributed storage, **MapReduce** for compute, and **YARN** for cluster resource negotiation.  
> A **DAG (Directed Acyclic Graph)**, on the other hand, is a mathematical data structure and execution model used by Apache Spark. In Hadoop MapReduce, every job was strictly hardcoded into a 2-stage cycle: Map $\rightarrow$ Shuffle $\rightarrow$ Reduce, writing all intermediate data to physical disk. Spark replaces this with an arbitrary DAG of multi-stage transformations pipelined in memory where possible, avoiding most intermediate disk I/O."

---

### Q2: What is an RDD?
> **Defensible Answer:**  
> "An **RDD (Resilient Distributed Dataset)** is the fundamental low-level abstraction of Apache Spark:
> 1. **Resilient:** It is fault-tolerant. If a worker node crashes and loses a partition, Spark recomputes that exact partition using the transformation **Lineage Graph** without restarting the entire job.
> 2. **Distributed:** The data is physically sliced into discrete **partitions** distributed across cluster nodes or CPU cores.
> 3. **Dataset:** It is an immutable collection of JVM objects."

---

### Q3: What is the difference between a Lineage Graph and a DAG?
> **Defensible Answer:**  
> "Ma'am, the **Lineage Graph** is the logical history of all transformations called on a dataset (e.g., `TextFile` $\rightarrow$ `Map` $\rightarrow$ `Filter`). It records *what* operations must be performed to reconstruct data for fault tolerance.  
> The **DAG** is the physical execution plan created by Spark's **DAGScheduler**. It translates the lineage graph into physical **Stages** and **Tasks** separated by shuffle boundaries, deciding *how* and *in what order* worker threads execute the code."

---

### Q4: What is the difference between Narrow and Wide Transformations?
> **Defensible Answer:**  
> - "**Narrow Transformations:** Each partition of the parent RDD contributes to **at most one** partition of the child RDD. Examples in our code include `filter()`, `select()`, and `withColumn()`. They execute entirely within memory inside a single stage with zero network data transfer.
> - **Wide Transformations:** Multiple child partitions depend on data distributed across multiple parent partitions. Examples in our code include `Window.partitionBy()`, `groupByKey()`, and `distinct()`. Wide transformations require a **Shuffle Exchange** across the network, which introduces a stage boundary and divides the DAG."

---

### Q5: How many Jobs, Stages, and Tasks are in this project, and how do you find them?
> **Defensible Answer:**  
> "We determine them by inspecting the **Spark Web UI (`localhost:4040`)** and executing `.explain(true)` on our DataFrames:
> 1. **Jobs:** A Job is created every time an **Action** is called (`.count()`, `.write.parquet()`, `fit()`); the Jobs tab lists them for each run.
> 2. **Stages:** Stages are created at **Shuffle Boundaries** caused by wide transformations, e.g. `Window.partitionBy(entity)` in `BuildForecastFeatures`. We read the exact count in the Stages tab rather than quoting a fixed number.
> 3. **Tasks:** Each Stage creates tasks equal to the number of partitions in that stage. Read stages follow the input splits; window shuffle stages start with **64 Tasks** because `spark.sql.shuffle.partitions = 64`, which AQE may coalesce. Our 10 CPU cores run at most 10 at a time."

---

### Q6: How many Actions are in this code?
> **Defensible Answer:**  
> "Ma'am, in Spark, transformations are lazy and only actions trigger computation. Across our main pipeline modules, we invoke the following actions:
> 1. `.count()`: Called during data quality auditing to verify record counts.
> 2. `.write.mode("overwrite").partitionBy("year").parquet(...)`: Called to serialize deduplicated and canonical datasets to HDFS.
> 3. `pipeline.fit(trainDF)`: Called in MLlib to train the GBT, random-forest and linear-regression forecasting pipelines.
> 4. `model.transform(testDF)` followed by `.write.parquet(...)`: Called to score the test period and persist predictions.
> 5. `.start()`: Called on the `writeStream` of `PriceEventStream` to start Structured Streaming."

---

### Q7: Are you using the DataFrame or Dataset API, and why?
> **Defensible Answer:**  
> "In Scala, a `DataFrame` is an alias for a untyped `Dataset[Row]`. We use both strategically:
> 1. We use **DataFrames** for our large-scale batch ingestion, deduplication, and windowing because DataFrames leverage Spark's **Catalyst Optimizer** for physical execution planning and the **Tungsten Engine** for off-heap binary memory management and whole-stage Java bytecode generation.
> 2. Our current streaming job (`PriceEventStream.scala`) also uses DataFrames, so batch and streaming share one canonicalisation function (`CanonicalEvent.standardize`). Strongly-typed **Datasets** (`Dataset[MarketEntity]` with `flatMapGroupsWithState`) appeared only in the legacy v1 stream (`Phase10StructuredStreamingReal.scala`), kept for history."

---

### Q8: What are Higher-Order Functions, and where did you use them?
> **Defensible Answer:**  
> "A **Higher-Order Function** is a functional programming concept in Scala where a function either takes another function as an argument or returns a function.  
> In our project, we used higher-order functions in:
> 1. `.map()` and `.filter()`: Passing anonymous lambda functions to filter negative price spreads (`row => row.getAs[Double]("max_price") >= row.getAs[Double]("min_price")`).
> 2. `SparkSetup.timed[T](label)(body: => T)`: a call-by-name block that times any computation.
> 3. `foreachBatch(processBatch _)`: In `PriceEventStream` we pass our `processBatch` function to the streaming sink, which writes each micro-batch to silver and alerts."

---

### Q9: Why didn't your team use Hadoop MapReduce?
> **Defensible Answer:**  
> "MapReduce is a legacy disk-bound batch paradigm. It forces every computation into a rigid Map $\rightarrow$ Sort $\rightarrow$ Reduce flow, serializing all intermediate data to physical HDFS disks. Multi-pass rolling-window features and iterative tree training over 75 million rows would need many sequential MapReduce jobs, each writing to disk. Apache Spark executes multi-stage DAG pipelines in memory where possible, with Catalyst and Tungsten optimizations, and provides MLlib and Structured Streaming in the same engine."

---

### Q10: What cluster are you using?
> **Defensible Answer:**  
> "We use a hybrid distributed architecture:
> 1. **Storage Cluster:** A multi-container **Docker cluster** running **Hadoop HDFS 3.4.1** with 1 NameNode and 3 DataNodes with replication factor 3.
> 2. **Compute Engine:** Apache Spark 4.2.0 executing in `local[*]` mode utilizing all **10 physical CPU cores** of our Apple Silicon host machine as parallel worker threads with 4 GB driver memory.
> 3. **Cluster benchmark:** a 2-worker Docker Spark cluster (3 cores each, same host) ran W1 in 9.2 s and W2 in 14.4 s on 11.27 M rows.
> We do not claim a physical multi-rack YARN cluster; our setup demonstrates genuine distributed block storage, replication, and multi-core parallel compute on one host."

---

### Q11: Your forecasts beat "last price" by only 3–8%. Why is the improvement so small, and is it real?
> **Defensible Answer:**  
> "Ma'am, persistence (tomorrow's price = today's price) is a hard baseline for mandi prices: between 17% and 34% of target changes are exactly zero, because mandis re-quote prices. So we report relative MAE against persistence on identical rows: **0.971, 0.953, 0.938 and 0.923** for next, 3, 7 and 14 days on the 2025-01 to 2026-04 test, i.e. 3–8% lower error.  
> The gain is real: Diebold–Mariano tests reject equal accuracy at every horizon (p between 3.6e-47 and 1.3e-22); the model beats persistence on 58.5–76.4% of individual series; and the frozen models, never refitted, still score **0.963, 0.955, 0.958 and 0.952** on 2026-04-22 to 2026-10-22, data that did not exist when they were trained. Our 80% intervals cover 78.6–80.5% of outcomes. A per-series exponential smoother matches us at 1–3 days, so our clear advantage is at 7–14 days."

---

### Q12: Did you mix real data and synthetic data during machine learning?
> **Defensible Answer:**  
> "No, Ma'am. All features, training, validation and testing use real AGMARKNET data: the archive silver layer (75.64 million rows) and, for the frozen-model checks, the official back-fill (silver v2, 82.1 million rows).  
> A synthetic workload from v1 (`data_source = synthetic_scaled`) exists only for scalability tests. It was not re-run for AG-DATA 2.0 and was never used for any model."

---

### Q13: What happened to the anomaly classifier and its high accuracy in your earlier version?
> **Defensible Answer:**  
> "Ma'am, we audited our own v1 results and **withdrew** them. The v1 'real-time screening' accuracy, precision, recall and F1 figures were not produced by any code or log in the repository; they were introduced by one commit (`d760677`) that edited only the README and the dashboard. The v1 design was also flawed: its label was a function of its own features, and its outlier bounds were fitted on all years including the test period. The only logged v1 classifier (72.54% accuracy) was below its own 84.35% all-normal baseline. Details are in `docs/AUDIT_PRIOR_RESULTS.md`."

---

### Q14: How good are your anomaly alerts now?
> **Defensible Answer:**  
> "We evaluate them only on injected, labelled corruptions. The production rule (a trailing robust z-score that excludes the report it scores) reaches **PR-AUC 0.704**, against **0.352** for the legacy commodity IQR rule, with precision 0.313, recall 0.846 and a false-positive rate of 0.019. There are no labels for real anomalies, so we claim **no accuracy for real anomalies**."
