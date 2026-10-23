# 🌾 AGRICULTURAL COMMODITY BIG DATA ANALYTICS: MASTER SYLLABUS, VIVA & DEFENSE GUIDE
### End-to-End Distributed Architecture, Spark DAG Analysis, Engine Optimization, and Faculty Viva Defense

> Corrected 2026-10-23: figures now come from docs/VERIFIED_METRICS.md; original wording preserved in Git commit 3926155.

**Course:** 23AID302 — Big Data Analytics  
**Department:** Department of Artificial Intelligence and Data Science  
**Institution:** School of Artificial Intelligence, Amrita Vishwa Vidyapeetham  
**Faculty Evaluator:** **Dr. Sreeja**  
**Project Team:**  
- **C Rishitha** (`CB.AI.U4AID24109`)  
- **Karthikeya Y** (`CB.AI.U4AID24163`)  
- **Ashwin Tyagi** (`CB.AI.U4AID24167`)  
- **Kaushal S** (`CB.AI.U4AID24168`)  

**Hardware Environment:** Apple Silicon Mac (10 Physical CPU Cores, 16 GB Unified Memory)  
**Distributed Cluster Stack:** Apache Spark 4.2.0, Hadoop HDFS 3.4.1 (Docker 4-Node Cluster), Apache Kafka 4.3, Scala 2.13.18, OpenJDK 21.0.12  

---

# 📑 TABLE OF CONTENTS

1. [PIN-TO-PIN SYLLABUS MAPPING (UNITS 1 TO 4)](#1-pin-to-pin-syllabus-mapping-units-1-to-4)
   - Unit 1: Big Data Fundamentals & Hadoop Ecosystem
   - Unit 2: Functional Programming & Scala Language Core
   - Unit 3: Spark Architecture, RDDs, DataFrames, Tungsten & DAG
   - Unit 4: Spark MLlib Pipelines & Agribusiness Commodity Case Study
2. [STEP-BY-STEP PROJECT EXECUTION: WHAT, HOW & WHY](#2-step-by-step-project-execution-what-how--why)
   - Step 1 to Step 12 Detailed Architectural Rationale
3. [HOW TO PRESENT IN FRONT OF DR. SREEJA (15-MIN PLAYBOOK)](#3-how-to-present-in-front-of-dr-sreeja-15-min-playbook)
   - Slide-by-Slide Script, Verbal Transitions, and Key Academic Emphasis
4. [LIVE DEMO PLAYBOOK & EXACT TERMINAL COMMANDS](#4-live-demo-playbook--exact-terminal-commands)
   - How to Check HDFS, Launch Spark in Local Mode, Run Code & Start Dashboard
5. [SPARK WEB UI, DAG, PARTITIONS & LAPTOP CORE UTILIZATION](#5-spark-web-ui-dag-partitions--laptop-core-utilization)
   - Opening Spark UI (`localhost:4040`)
   - How to Read and Explain the Visual DAG Nodes
   - In-Depth Partitioning Mechanics (Input vs Shuffle Partitions)
   - Mathematical Proof of 10 CPU Core Wave Execution
   - DAG Performance Factors (Skew, Spill to Disk, GC Time, Shuffle)
6. [PORT & LOCALHOST DIRECTORY](#6-port--localhost-directory)
7. [EXHAUSTIVE VIVA VOCE QUESTIONS & DEFENSE REPOSITORY](#7-exhaustive-viva-voce-questions--defense-repository)
   - Detailed, architecturally defensible answers to 17 faculty questions (including the honest forecasting-results questions).

---

# 📚 1. PIN-TO-PIN SYLLABUS MAPPING (UNITS 1 TO 4)

This project was built to implement and validate every single concept in the **23AID302 Big Data Analytics** syllabus. Below is the pin-to-pin mapping of curriculum theory to our project's codebase.

```
========================================================================================================
UNIT 1: INTRODUCTION TO BIG DATA ANALYTICS & HADOOP ECOSYSTEM
========================================================================================================
Syllabus Topic                         Where & How It Is Implemented in AG-DATA Project
-------------------------------------  -----------------------------------------------------------------
1. Definition, Characteristics &       The 5 Vs of Agricultural Market Data:
   Importance of Big Data              - Volume: 75.98M raw archive rows; 75.64M archive silver rows;
   (The 5 Vs)                            82.1M silver v2 rows; 21.06M forecast feature rows.
                                       - Velocity: daily reports through Kafka topic agri.prices.v1; replay demo
                                         of 21,524 messages, producer->sink p50 latency 1.69 s.
                                       - Variety: archive CSVs + official data.gov.in API records (two resources).
                                       - Veracity: quality rules, de-duplication, quarantine; the archive mirror
                                         holds only 30.0% of official reports (2025-10 .. 2026-04).
                                       - Value: evaluated price forecasts and cautious SELL/HOLD/WATCH/COMPARE cards.

2. Tools & Technologies for            - Apache Spark 4.2.0: In-memory distributed query and ML engine.
   Big Data Analytics                  - Hadoop HDFS 3.4.1: Distributed, replicated fault-tolerant block storage.
                                       - Apache Kafka 3.6.0: Distributed publish-subscribe event broker.
                                       - Docker: Containerization for multi-node HDFS cluster isolation.

3. State-of-the-Art Computing          Transition from 1st Gen (Disk-bound MapReduce) to 2nd Gen (In-memory Spark
   Paradigms & Platforms               DAG execution). We demonstrate why iterative 7-day rolling window
                                       features and iterative tree training are a poor fit for MapReduce's disk I/O.

4. Hadoop Ecosystem in Brief           - HDFS: 1 NameNode (metadata master) + 3 DataNodes (distributed block slaves).
                                       - Block Size: 128 MiB blocks tailored for sequential columnar Parquet reads.
                                       - Replication Factor: 3 (692 MB silver layer HEALTHY; readable with 1 DataNode down).
                                       - HDFS RPC: Communication on port `9000` via `hdfs://localhost:9000`.

5. Mapper and Reducer                  - Map-side processing: Projection, date normalization, validity checks.
                                       - Shuffle & Reduce-side processing: Composite business-key window grouping
                                         and partition-wide sorting (`Window.partitionBy(...).orderBy(...)`).
========================================================================================================
UNIT 2: FUNCTIONAL PROGRAMMING (FP) & SCALA CONCEPTS
========================================================================================================
Syllabus Topic                         Where & How It Is Implemented in AG-DATA Project
-------------------------------------  -----------------------------------------------------------------
1. Functional Programming Concepts     Pure functions with zero side-effects during dataset transformations.
                                       Deterministic, reproducible pipeline runs where functions yield identical
                                       results without mutating external state.

2. Mutable vs Immutable Structures    - Pipelines are chains of `val`s (`SparkSetup.scala`, `Deduplicate.scala`,
                                         `forecast/Features.scala`).
                                       - Spark DataFrames and Datasets are strictly immutable; operations produce
                                         new DataFrames, enabling lineage-based fault recovery.

3. Scala Collections & ConsList        - Scala `Seq`, `List`, `Array`, and `Map` used for schema column sequences.
                                       - `ConsList` (`head :: tail`) concept used in recursive parsing of schemas
                                         and dynamically building composite window expressions.

4. Type Hierarchy (Any, AnyVal,        - Domain types are `case class`es (subtypes of `AnyRef`):
   AnyRef, Option, Nothing, Null)        `sealed trait Spec` with `case class GBT(depth, iters, step, loss)`,
                                         `RF(trees, depth)`, `LR(reg, loss)` in `ForecastModels.scala`.
                                       - `Option[T]` (`Some` / `None`) for optional settings, e.g.
                                         `o.getOrElse("maxOffsetsPerTrigger", "50000")`.

5. Higher-Order Functions              - Passing functions as first-class citizens into transformations:
                                         `DataQuality.businessKey.map(col)` -> `map` takes function `col`.
                                       - Call-by-Name parameters in `SparkSetup.timed[T](label)(body: => T)`.
                                       - `foreachBatch(processBatch _)` passes a function to the streaming sink.

6. Closures & Concurrency              - Worker threads execute serialization closures dispatched by the Driver.
                                       - Multi-threaded parallel execution across 10 Apple Silicon CPU cores
                                         via Spark's `local[*]` multithreading execution pool.

7. OOP in Scala                        - Sealed traits and singleton objects (`object SparkSetup`, `object Deduplicate`,
                                         `object Features`).
========================================================================================================
UNIT 3: SPARK ARCHITECTURE, DATASETS/DATAFRAMES & DAG
========================================================================================================
Syllabus Topic                         Where & How It Is Implemented in AG-DATA Project
-------------------------------------  -----------------------------------------------------------------
1. Spark Architecture & Cluster        - Driver Program: Runs on JVM, converts user code into logical DAG.
                                       - Cluster Manager: `local[*]` thread coordinator.
                                       - Executors: 10 worker execution threads hosting memory & task slots.

2. Resilient Distributed Datasets      Fundamental abstraction: partitioned, immutable, lineage-backed distributed
   (RDDs)                              collections. Explaining how RDD partitions recompute on node failure.

3. Transformations vs Actions          - Lazy Evaluation: Transformations (`filter`, `withColumn`, `select`, `join`)
                                         record lineage dependencies without triggering CPU execution.
                                       - Actions (`count()`, `write.parquet()`, `show()`, `pipeline.fit()`) compile
                                         the logical plan into a physical DAG and execute jobs.

4. DataFrames vs Datasets              - DataFrames (`Dataset[Row]`): Used for batch ETL to leverage Catalyst and Tungsten.
                                       - Datasets (`Dataset[T]`): typed API; the legacy v1 stream used them. The
                                         current stream (`PriceEventStream`) uses DataFrames.
                                       - Why not pure RDDs? RDDs bypass Catalyst and Tungsten, incurring heavy GC.

5. Catalyst Query Optimizer &          - Catalyst: Analysis, Logical Optimization, Physical Planning, Code-Gen.
   Tungsten Execution Engine           - Pushdown Predicates (`PushedFilters: [IsNotNull(arrival_date)]`).
                                       - Tungsten: Off-heap binary format (`UnsafeRow`), whole-stage Java bytecode.

6. Directed Acyclic Graph (DAG)        - DAGScheduler breaks the Logical Lineage into physical **Stages** at
                                         shuffle boundaries (Wide Transformations).
                                       - TaskScheduler schedules **Tasks** (1 task per partition) across CPU cores.

7. Narrow vs Wide Transformations      - Narrow: 1-to-1 partition mapping (`filter`, `withColumn`); pipelined.
                                       - Wide: M-to-N partition mapping (`Window.partitionBy`, `groupByKey`);
                                         triggers network/memory **Shuffle Exchange** and creates new stage.
========================================================================================================
UNIT 4: MACHINE LEARNING WITH SPARK MLLIB & AGRIBUSINESS CASE STUDY
========================================================================================================
Syllabus Topic                         Where & How It Is Implemented in AG-DATA Project
-------------------------------------  -----------------------------------------------------------------
1. Spark MLlib & Distributed ML        Distributed training using native Spark MLlib algorithms running across
                                       CPU worker threads without moving data to single-node Python memory.

2. Building ML Pipelines in Spark      `org.apache.spark.ml.Pipeline` per model family, fitted on training rows only:
                                       `VectorAssembler` -> `GBTRegressor` / `RandomForestRegressor`, and
                                       `StringIndexer` + `OneHotEncoder` + `StandardScaler` -> `LinearRegression`.

3. Feature Engineering                 Leakage-safe window features per price series (log scale):
                                       returns (`ret1`, `ret2`, `ret5`), rolling means/stddevs (`mean7/30/90`,
                                       `std30/90`), range position (`hi30`, `lo30`), same-season-last-year
                                       (`ly_dev`), price spread, day-of-year and day-of-week. Every feature window
                                       ends at the current report; every target starts strictly after it.

4. Temporal Splitting & Model Choice   - Train origins 2016-2023, validation 2024 (model choice + conformal
                                         calibration), test 2025-01-01 .. 2026-04-20 scored once.
                                       - Baselines: persistence, moving averages, seasonal naive.
                                       - Selected: absolute-loss GBT (next, 3 d), random forest (7, 14 d).
                                       - Result: relative MAE vs persistence 0.971 / 0.953 / 0.938 / 0.923.

5. Domain Case Study: Agribusiness     - 36 commodities, 11,845 mandi series, 1/3/7/14-day forecasts with
   Farmer Decision Support System        80% conformal intervals (test coverage 78.6-80.5%).
                                       - Cautious market-outlook cards (7-day test):
                                         * WATCH: the default, 98.5% of report-days.
                                         * HOLD: 0.5% of report-days, hit rate 80.0%.
                                         * SELL: 1.0% of report-days, hit rate 67.8%.
                                         * COMPARE: compare nearby mandis before travelling.
========================================================================================================
```

---

# ⚙️ 2. STEP-BY-STEP PROJECT EXECUTION: WHAT, HOW & WHY

When Dr. Sreeja asks you to explain **"What you did, how you did it, and why you did it"**, walk her through this systematic 12-step engineering lifecycle:

```
                                  PIPELINE ARCHITECTURE
                                  
   [Raw archive: 75.98M rows] + [data.gov.in: 7.72M official records]
                                │ (explicit StructType / API adapter)
                                ▼
   [Quality rules + de-duplication] ──> [Silver Parquet, year=]  (75.64M archive; 82.1M silver v2)
                                │                  └──> [Docker HDFS, replication 3: 692 MB silver]
                                ▼
   [Leakage-safe window features (<= t), targets (> t)]   (21.06M feature rows, 11,845 series)
                                ▼
   [Baselines + MLlib LR / RF / GBT] ──> choose on 2024 ──> conformal ──> test 2025-26 once
                                ▼                                   (rel. MAE 0.971 / 0.953 / 0.938 / 0.923)
   [Gold tables] ──> [FastAPI + DuckDB] ──> [PWA: forecasts, intervals, decision cards]

   [Kafka agri.prices.v1] ──> [Structured Streaming] ──> bronze / quarantine / silver / alerts
                                                       (replay: 20,000 to silver, 0 missing, p50 1.69 s)
```

### Step 1: Environment & Toolchain Configuration
- **WHAT:** Configured an enterprise-grade Big Data environment using Apache Spark 4.2.0, Hadoop 3.4.1 in Docker, OpenJDK 21.0.12, and Scala 2.13.18.
- **HOW:** Implemented `SparkSetup.scala` to centralize SparkSession creation with JVM configuration flags (`--add-opens=java.base/java.lang=ALL-UNNAMED`).
- **WHY:** Java 21 enforces strict modular encapsulation. Without explicit reflection permissions, Spark's off-heap memory allocators and Kryo serializers crash on startup with `IllegalAccessException`.

### Step 2: High-Throughput Schema Ingestion (75.98 Million Archive Rows + Official API Back-fill)
- **WHAT:** Ingested the AGMARKNET daily-price archive (Kaggle mirror, 75,984,017 raw rows) and back-filled 7,720,662 official records from data.gov.in for 2025-10-01 → 2026-10-22 (387 days, 0 failed days).
- **HOW:** Defined explicit `StructType` schemas in `Schemas.scala` and enabled RFC-4180 quote-escaping.
- **WHY:** Spark's `inferSchema = true` needs an extra full pass over the raw text before the real read. Supplying an explicit schema avoids that pass, fixes the column types, and prevents malformed row splits on embedded commas (e.g., `"Sesamum (Sesame,Gingelly,Til)"`).

### Step 3: Distributed Replicated Storage in Hadoop HDFS
- **WHAT:** Deployed an HDFS cluster in Docker with 1 NameNode (`agri-namenode`) and 3 DataNodes (`agri-datanode1/2/3`).
- **HOW:** Configured `dfs.replication = 3` and `dfs.blocksize = 134217728` (128 MiB).
- **WHY:** 
  1. *Fault Tolerance:* With one DataNode stopped, a probe file was still read in full with an identical checksum (`results/hdfs/summary.md`). Caveat: all three DataNodes share one physical disk, so this shows HDFS behaviour, not hardware durability.
  2. *Sequential I/O Throughput:* 128 MiB blocks match the batch streaming read profile of Parquet files while minimizing NameNode memory footprint.

### Step 4: Resilient Multi-Format Date Cleansing
- **WHAT:** Reconciled 25 years of conflicting date conventions (`dd MMM yyyy`, `yyyy-MM-dd`, `dd/MM/yyyy`).
- **HOW:** Used Spark SQL `coalesce` wrapping `try_to_date`:
  ```scala
  coalesce(
    try_to_date(col("Reported Date"), "dd MMM yyyy"),
    try_to_date(col("Reported Date"), "yyyy-MM-dd"),
    try_to_date(col("Arrival_Date"), "dd/MM/yyyy")
  )
  ```
- **WHY:** Standard `to_date()` crashes the entire Spark job upon encountering the first corrupt string with an unrecoverable `DateTimeParseException`. `try_to_date` safely yields `null`, allowing our data quality rules to catch and quarantine invalid records.

### Step 5: Composite Business-Key Window Deduplication
- **WHAT:** Removed duplicate reports so that the archive silver layer keeps 75,644,801 of the 75,984,017 raw rows (after quality rules and de-duplication).
- **HOW:** Partitioned over the composite business key (`DataQuality.businessKey`: state, district, market, commodity, variety, arrival date), ordered deterministically by data quality, and kept `row_number() === 1`.
- **WHY:** A whole-row `distinct()` would keep near-duplicates that differ only in non-key columns, and an arbitrary choice between them would make two runs differ. A deterministic `row_number()` over the business key keeps exactly one, reproducible row per report.

### Step 6: Parquet Columnar Serialization & Partition Pruning
- **WHAT:** Converted the raw CSV text into Snappy-compressed columnar Parquet (the silver layer), partitioned by `year`. In HDFS the silver layer occupies 692 MB.
- **HOW:** `df.write.mode("overwrite").partitionBy("year").parquet(outputPath)`
- **WHY:** 
  1. *Storage Efficiency:* columnar compression makes the silver layer far smaller than the CSV source.
  2. *Column Pruning:* queries reading only `modal_price` scan only the relevant column chunks.
  3. *Partition Pruning:* queries filtering for `year >= 2024` skip the directories for earlier years entirely.

### Step 7: Leakage-Safe Window Features and Targets
- **WHAT:** Built 21.06 M feature rows for 11,845 price series (36 commodities): log returns, 7/30/90-day rolling means and standard deviations, 30-day range position, same-season-last-year deviation, spread and calendar terms.
- **HOW:** Spark SQL windows over an integer day number (`forecast/Features.scala`):
  ```scala
  private def byEntity = Window.partitionBy(EntityId).orderBy(col(Day))
  private def days(lo: Long, hi: Long) = byEntity.rangeBetween(lo, hi)
  .withColumn("mean30", avg(lp).over(days(-29, 0)))   // ends at the current report
  ```
  The target is the log return to a report strictly after the origin (`>= +1 day`).
- **WHY:** A feature that reads a later report of the same series is **lookahead leakage**. Every feature window ends at row 0 or earlier, every target starts after it, and `ForecastFeaturesSpec` perturbs future rows and fails if any feature changes.

### Step 8: Distributed MLlib Pipeline Architecture
- **WHAT:** A forecasting benchmark: persistence, moving-average and seasonal-naive baselines against MLlib linear regression, random forests and gradient-boosted trees, for next / 3 / 7 / 14 days.
- **HOW:** Each model is a Spark `Pipeline` (`VectorAssembler` → `GBTRegressor` / `RandomForestRegressor`, or encoders + `StandardScaler` → `LinearRegression`), fitted on a sample of at most 2 M training rows per horizon. Selected: GBT with absolute loss on a percent target (depth 7, 150 iterations, step 0.5) for next and 3 days; random forest (60 trees, depth 10) for 7 and 14 days.
- **WHY:** Tree ensembles handle non-linear, commodity-specific dynamics in one global model. Absolute loss matters because many price changes are exactly zero: squared-loss models do not beat persistence at the next-report horizon.

### Step 9: Strict Temporal Model Validation
- **WHAT:** Scored the selected models once on the 2025-01-01 → 2026-04-20 test period, then on six months of data that did not exist in the archive.
- **HOW:** Train origins 2016–2023, validation 2024 (model choice and conformal calibration), test 2025–26. Relative MAE vs persistence: **0.971 / 0.953 / 0.938 / 0.923** (next / 3 / 7 / 14 days), Diebold–Mariano p between 3.6e-47 and 1.3e-22, 80% interval coverage 78.6–80.5%. Frozen models, prospective 2026-04-22 → 2026-10-22: **0.963 / 0.955 / 0.958 / 0.952**, coverage 76.9–80.1%.
- **WHY:** Random $k$-fold cross-validation or `randomSplit([0.8, 0.2])` leaks future information into training and inflates scores. A chronological split, scored once, plus a prospective check on unseen months, shows how the models behave on the future.

### Step 10: Event Streaming via Apache Kafka & Structured Streaming
- **WHAT:** An incremental path for daily reports: Kafka topic `agri.prices.v1` (6 partitions) → `PriceEventStream` → bronze (raw + offsets), quarantine, silver and alerts.
- **HOW:** Invalid messages are quarantined before a 10-day watermark; exact re-sends are dropped by content hash (`event_id`); the silver sink is a `foreachBatch` that overwrites `batch_id=N`. Replay demo: 21,524 messages = 20,000 to silver + 1,317 duplicates removed + 207 quarantined; 0 missing; batch/stream parity 0 mismatches; producer→sink p50 1.69 s. A live current-day pull (2026-10-23) moved 4/4 records to silver.
- **WHY:** Decouples ingestion from processing and gives effectively-once output per offset range. End-to-end exactly-once from the government source is not claimed. Features and forecasts are computed in batch only, so there is one feature implementation.

### Step 11: Scalability Measurements
- **WHAT:** Timed two workloads: W1 (aggregate commodity × state × month) and W2 (per-entity window features).
- **HOW:** Local (Apple M5, 10 cores), full 75.6 M rows: W1 42.2 s, W2 65.9 s; speed-up at 10 cores 2.4× (W1) and 3.0× (W2). Docker Spark cluster (2 workers × 3 cores, one host), 11.27 M rows: W1 9.2 s, W2 14.4 s.
- **WHY:** Shows how the jobs scale with cores. A v1 synthetic workload (`synthetic_scaled`) exists for scalability only; it was not re-run for AG-DATA 2.0 and is never used for any model.

### Step 12: Farmer Decision Support App
- **WHAT:** An installable six-language PWA (English, Tamil, Telugu, Malayalam, Hindi, Kannada) served by FastAPI + DuckDB from the gold tables (read-only).
- **HOW:** Shows forecasts with 80% intervals and cautious SELL / HOLD / WATCH / COMPARE cards. 7-day test: WATCH on 98.5% of report-days, HOLD 0.5% (hit rate 80.0%), SELL 1.0% (hit rate 67.8%). These are hit rates on published prices, not farm profits.
- **WHY:** Bridges the gap between Big Data analytics and farmers; WATCH is the honest default when the forecast is not decisive. (The older Streamlit dashboard in `src/dashboard/app.py` now shows the verified figures.)

---

# 🎤 3. HOW TO PRESENT IN FRONT OF DR. SREEJA (15-MIN PLAYBOOK)

Use this exact script and timing guide during your team presentation:

| Slide | Target Time | Speaker | What to Say (Verbatim Presenter Script) | Key Academic Terminology |
|:---:|:---:|:---:|---|---|
| **1** | **1.0 min** | Kaushal / Team Lead | *"Good morning Dr. Sreeja. Our project is Agricultural Commodity Price Forecasting and Farmer Decision Support using Hadoop HDFS and Apache Spark. Our team members are Rishitha, Karthikeya, Ashwin, and Kaushal. We built an end-to-end Big Data pipeline over 75.98 million archived mandi reports plus 7.7 million official records, forecasting mandi prices 1 to 14 days ahead with Spark MLlib and streaming daily reports through Kafka."* | Distributed Big Data pipeline, price forecasting. |
| **2** | **1.5 min** | Rishitha | *"Ma'am, a farmer deciding when and where to sell needs to know what the mandi is likely to quote. We forecast the modal price for 36 commodities across 11,845 mandi series, with 80% prediction intervals, and turn the forecasts into cautious SELL, HOLD, WATCH and COMPARE cards. Building leakage-safe window features over tens of millions of reports does not fit single-node Pandas on a 16 GB laptop, so we use HDFS for replicated storage and Spark for parallel compute."* | 5 Vs of Big Data, forecasting target, decision support. |
| **3** | **1.5 min** | Karthikeya | *"The archive has 75.98 million raw rows; after quality rules and de-duplication the silver layer keeps 75.64 million. We back-filled 7.72 million official records from data.gov.in for October 2025 to October 2026, giving a silver v2 layer of 82.1 million rows. The back-fill showed that the archive mirror holds only 30% of official reports after September 2025. The forecast panel has 21.06 million feature rows."* | Bronze/silver/gold layers, data veracity. |
| **4** | **2.0 min** | Ashwin | *"Our architecture is dual-path: a batch path for silver, features, models and gold serving tables, and a streaming path from Kafka through Structured Streaming to bronze, quarantine, silver and alerts. HDFS runs in Docker with 1 NameNode and 3 DataNodes and replication factor 3. Spark executes in `local[*]` mode on all 10 CPU cores of our host. HDFS stores blocks; it does not execute Spark tasks."* | Dual-Path Architecture, Docker HDFS, Spark local[*] Cores. |
| **5** | **2.5 min** | Kaushal | *"In Spark, we use DataFrames rather than RDDs to exploit Catalyst optimization (predicate pushdown, projection pruning) and Tungsten binary memory (`UnsafeRow`). Transformations are lazy; actions compile the DAG into stages at shuffle boundaries. In our feature job, `Window.partitionBy(entity)` creates a ShuffleExchange; we use 64 shuffle partitions, coalesced by AQE. On the full 75.6 million rows, 10 cores give a 2.4 to 3.0× speed-up over one core."* | Catalyst Optimizer, Tungsten, Narrow vs Wide, Stages. |
| **6** | **2.0 min** | Rishitha | *"In Scala, we wrap date parsing in `coalesce(try_to_date(...))` so one malformed value cannot abort a job. Every feature window ends at the current report and every target starts strictly after it, using `rangeBetween` on an integer day number; a perturbation test fails if any feature reads the future. In streaming, invalid messages are quarantined before the 10-day watermark and re-sends are dropped by content hash."* | Functional Programming, Resilient Parsing, Leakage-Safe Windows. |
| **7** | **1.5 min** | Karthikeya | *"We compare persistence, moving-average and seasonal baselines with MLlib linear regression, random forests and gradient-boosted trees. Train origins are 2016 to 2023, models are chosen on 2024, and the January 2025 to April 2026 test is scored once. Absolute-loss GBT is selected for next and 3 days, random forest for 7 and 14 days. Conformal intervals are calibrated on 2024."* | Temporal split, baselines, MLlib Pipelines, conformal intervals. |
| **8** | **2.0 min** | Ashwin | *"Relative MAE against persistence is 0.971, 0.953, 0.938 and 0.923 for next, 3, 7 and 14 days, and every Diebold–Mariano p-value is below 1e-21. 80% intervals cover 78.6 to 80.5%. Frozen models on six months of new data, April to October 2026, still score 0.952 to 0.963. Anomaly flags reach PR-AUC 0.704 on injected corruptions, against 0.352 for the old IQR rule. The Kafka replay delivered 20,000 of 20,000 valid messages with 0 parity mismatches and a 1.69 s median latency."* | Relative MAE, Diebold–Mariano test, interval coverage. |
| **9** | **1.0 min** | Kaushal | *"Persistence is hard to beat: 17 to 34% of price changes are exactly zero, so our gains are modest, about 3 to 8%, but significant. We audited our own v1 work and withdrew its anomaly-classifier metrics, because no code produced them. Spark runs in `local[*]` mode on one laptop, the HDFS replicas share one disk, and there is no public deployment."* | Honest baselines, audit, limitations. |
| **10** | **0.5 min** | Team Lead | *"Our complete code, results files and presentation are on GitHub at `github.com/kaushalrog/AG-DATA`; every number we quoted is listed with its source in `docs/VERIFIED_METRICS.md`. Thank you Dr. Sreeja. We welcome your questions."* | Open-Source Defense, Reproducibility. |

> **What changed and why.** The v1 playbook (Git commit 3926155) presented a Random Forest anomaly classifier with very high accuracy/precision/recall/F1 and Kafka throughput/latency figures. No code or log in the repository produces those figures, so they were withdrawn (`docs/AUDIT_PRIOR_RESULTS.md`, `docs/VERIFIED_METRICS.md` §6). The talk now leads with the price-forecasting results.

---

# 💻 4. LIVE DEMO PLAYBOOK & EXACT TERMINAL COMMANDS

Have these commands tested and ready in separate terminal tabs before your viva begins:

### Command 1: Verify the 4-Container Docker HDFS Cluster
Show Dr. Sreeja that HDFS is genuinely running with 3 DataNodes and replication factor 3:
```bash
# 1. Show all Docker containers running
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 2. Run HDFS dfsadmin report to prove 3 live DataNodes
docker exec -it agri-namenode hdfs dfsadmin -report

# 3. Show block replication factor 3 and Parquet storage in HDFS
docker exec -it agri-namenode hdfs fsck /agri/silver/daily_market_prices -files -blocks -locations
```
*What to point out:* Highlight **"Live datanodes (3)"** and **"Block replication: 3"** in the output.

---

### Command 2: Launch Spark in Local Mode on All 10 Laptop Cores
Show how to start an interactive Spark session leveraging your 10 Apple Silicon cores:
```bash
/opt/miniconda3/bin/spark-shell \
  --master "local[*]" \
  --driver-memory 4g \
  --conf "spark.sql.shuffle.partitions=64" \
  --conf "spark.driver.host=127.0.0.1" \
  --conf "spark.driver.extraJavaOptions=--add-opens=java.base/java.lang=ALL-UNNAMED --add-opens=java.base/java.util=ALL-UNNAMED --add-opens=java.base/sun.util.calendar=ALL-UNNAMED"
```
*What to explain:*
- `--master local[*]`: Automatically detects 10 CPU cores and spawns 10 worker execution threads inside the JVM.
- `--driver-memory 4g`: Allocates 4 GB heap memory to the driver.
- `--conf spark.sql.shuffle.partitions=64`: Configures 64 partitions for wide transformations (as in the forecast jobs; Spark's default is 200).
- `--add-opens`: Bypasses Java 21 module encapsulation.

---

### Command 3: Execute Interactive Spark Code to Demonstrate Catalyst & DAG
Inside the running `spark-shell`, execute this snippet:
```scala
import org.apache.spark.sql.functions._
import org.apache.spark.sql.expressions.Window

// 1. Create in-memory test data
val data = Seq(
  ("Maharashtra", "Pune", "Onion", "2025-01-01", 2500.0),
  ("Maharashtra", "Pune", "Onion", "2025-01-02", 2600.0),
  ("Maharashtra", "Pune", "Onion", "2025-01-03", 4200.0), // Anomaly spike!
  ("Karnataka", "Bangalore", "Tomato", "2025-01-01", 1800.0),
  ("Karnataka", "Bangalore", "Tomato", "2025-01-02", 1200.0)
).toDF("state", "market", "commodity", "date", "modal_price")

// 2. Wide transformation (forces a ShuffleExchange and Stage boundary)
val w = Window.partitionBy("state", "market", "commodity").orderBy("date")
val dfFeatures = data
  .withColumn("prev_price", lag("modal_price", 1).over(w))
  .withColumn("price_jump", col("modal_price") - col("prev_price"))
  .filter(col("modal_price") > 1500.0) // Narrow transformation (Predicate pushdown)

// 3. Inspect the Catalyst physical plan
dfFeatures.explain(mode = "formatted")

// 4. Trigger Action (Executes DAG across local CPU cores!)
dfFeatures.show()
```

---

### Command 4: Serve the App (and the legacy Streamlit dashboard)
In a separate terminal tab:
```bash
PYTHONPATH=py .venv/bin/uvicorn agri.api.app:app --app-dir py --port 8000   # PWA + API
streamlit run src/dashboard/app.py --server.port 8501                       # legacy dashboard
```
Open **`http://localhost:8000`** in your browser.  
*What to show:* a commodity forecast with its 80% interval, the SELL / HOLD / WATCH / COMPARE card, and a language switch. The Streamlit dashboard shows the verified headline figures.

---

# 🔍 5. SPARK WEB UI, DAG, PARTITIONS & LAPTOP CORE UTILIZATION

### A. How to Open the Spark UI
While `spark-shell` or `spark-submit` is running, open your web browser to:
👉 **`http://localhost:4040`**  
*(Note: If port 4040 is occupied by a previous session, Spark automatically increments to 4041 or 4042).*

---

### B. How to Read and Explain the Visual DAG in Spark UI
1. Click on the **"Jobs"** or **"SQL/DataFrame"** tab at the top.
2. Click on any completed Job description (e.g., `Job 0: count at ...` or `Job 1: parquet at ...`).
3. Expand the **"DAG Visualization"** accordion toggle.

#### Visual Elements of the DAG:
- **Blue Rectangles / Outer Containers:** Represent **Stages**. Every wide transformation creates a new blue stage container.
- **Inner Rounded Boxes / Nodes:** Represent individual **RDDs and Transformations** (e.g., `Scan parquet`, `Filter`, `Project`, `Exchange`, `WholeStageCodegen`).
- **Arrows:** Show directional dependency (data flows downwards from parent RDDs to child RDDs).
- **`Exchange` Node:** This is the **ShuffleExchange**. It proves that Spark redistributed data across partitions via hashing.
- **`WholeStageCodegen` Box:** Represents the **Tungsten Engine**. It proves that Spark compiled multiple operations into a single optimized Java bytecode loop.

---

### C. In-Depth Partitioning Mechanics
Partitions are discrete physical chunks of data processed independently by worker threads:
1. **Input File Partitions:** When reading Parquet or CSV, partitions are determined by file size divided by `spark.sql.files.maxPartitionBytes` (default 128 MiB), with small files packed together.
2. **Shuffle Partitions (`spark.sql.shuffle.partitions`):** When a wide transformation occurs (`Window.partitionBy`, `groupBy`, `join`), Spark redistributes data into the configured number of partitions: **64** in our forecast jobs (Spark's default is 200), then AQE coalesces small ones.
3. **Partition Sizing Trade-Off:**
   - *Too Few Partitions:* Data per partition exceeds RAM, causing **Spill to Disk** or OOM crashes.
   - *Too Many Partitions:* Small task scheduling overhead dominates execution time.

---

### D. Mathematical Proof of 10 CPU Core Wave Execution
Dr. Sreeja will ask: *"How exactly did your laptop CPU cores execute these tasks?"*

1. **Hardware Profile:** Apple Silicon (M5) Mac with **10 CPU cores** (`sysctl -n hw.ncpu` = 10).
2. **Worker Threads:** `--master local[*]` allocates **10 concurrent worker threads** inside the single JVM.
3. **Task Wave Calculation (illustration):**
   - In a window-shuffle stage with `spark.sql.shuffle.partitions = 64`, Spark creates **64 Tasks** (before AQE coalescing).
   - The 10 cores run at most **10 tasks in parallel**:
     $$\text{Task Execution Waves} = \left\lceil \frac{64 \text{ Tasks}}{10 \text{ CPU Cores}} \right\rceil = 7 \text{ Waves}$$
4. **Measured effect of cores:** on the full 75.6 M rows, 10 cores give a 2.4× (W1 aggregate) and 3.0× (W2 window features) speed-up over 1 core (`results/scalability/runs.jsonl`). The speed-up is below 10× because of shuffle, I/O and scheduling overhead.
5. **Proving This in the Spark UI:**
   - Click on the **"Executors"** tab in `http://localhost:4040`.
   - In the **"driver"** row, point to **Cores: 10** and up to 10 **Active Tasks**.

---

### E. DAG Performance Factors (What to Tell Dr. Sreeja)
Performance in the DAG depends on four critical metrics visible in the Spark UI:
1. **Data Skew (Straggler Tasks):** In the **"Tasks"** summary table, check the Min, Median, and Max task durations. If Min is 100ms but Max is 45s, a single partition has excessive records (e.g., high-volume commodities like Onion/Potato).
2. **Spill (Memory) and Spill (Disk):** If a partition is too large for its execution memory slot, Spark spills records to disk, which slows the stage considerably. Check the "Spill" columns in the Stages tab.
3. **Shuffle Read / Shuffle Write Size:** Measures network and memory transfer across stage boundaries. Keeping shuffle size low reduces GC pressure.
4. **Garbage Collection (GC) Time:** Visible under Task Metrics. If GC time exceeds 10% of total run time, executor heap memory is under pressure.

---

# 🌐 6. PORT & LOCALHOST DIRECTORY

Memorize this exact directory for viva defense:

| Port | Service / Web UI | Operational Role & Viva Explanation |
|:---:|---|---|
| **`http://localhost:9870`** | **HDFS NameNode Web UI** | Shows HDFS cluster health, 3 connected DataNodes, 128 MB block replication status, and volume capacity. |
| **`http://localhost:4040`** | **Spark Application Web UI** | Live Spark monitor showing the DAG visualization, Jobs, Stages, tasks, 10 CPU executor cores, and Tungsten codegen. |
| **`http://localhost:8000`** | **FastAPI + PWA** | Forecasts, 80% intervals and SELL/HOLD/WATCH/COMPARE cards from the read-only gold tables. |
| **`http://localhost:8501`** | **Streamlit Dashboard (legacy)** | Verified headline figures and historical aggregates. |
| **`localhost:9000`** | **HDFS RPC (`fs.defaultFS`)** | Inter-process socket protocol used by Spark to read/write Parquet files to HDFS (`hdfs://localhost:9000/...`). |
| **`localhost:9092`** | **Apache Kafka Broker** | Event transport for topic `agri.prices.v1` (6 partitions, key = business key). |

These ports must stay on a private network; `docker-compose.yml` publishes them to localhost for development only (`docs/ARCHITECTURE.md`).

---

# 💡 7. EXHAUSTIVE VIVA VOCE QUESTIONS & DEFENSE REPOSITORY

### Q1: What is the difference between Hadoop and DAG?
> **Answer:**  
> "Ma'am, **Hadoop** is an entire distributed ecosystem comprising **HDFS** for storage, **MapReduce** for compute, and **YARN** for resource management.  
> A **DAG (Directed Acyclic Graph)** is a mathematical execution model used by Apache Spark. In Hadoop MapReduce, every job was rigidly hardcoded into a 2-stage cycle: Map $\rightarrow$ Shuffle $\rightarrow$ Reduce, writing all intermediate data to physical disk. Spark replaces this with an arbitrary DAG of multi-stage transformations pipelined in memory where possible, which avoids most intermediate disk I/O and is much faster for iterative and multi-pass workloads."

---

### Q2: What is meant by an RDD?
> **Answer:**  
> "An **RDD (Resilient Distributed Dataset)** is Spark's core low-level abstraction:
> 1. **Resilient:** It is fault-tolerant. If a node fails, Spark recomputes the lost partition using the **Lineage Graph** without restarting the job.
> 2. **Distributed:** Data is partitioned across cluster nodes or CPU cores for parallel execution.
> 3. **Dataset:** An immutable collection of JVM objects."

---

### Q3: What is the difference between a Lineage Graph and a DAG?
> **Answer:**  
> "Ma'am, the **Lineage Graph** is the logical history of all transformations chained from the source RDD (e.g., `TextFile` $\rightarrow$ `Map` $\rightarrow$ `Filter`). It records *what* operations must be performed to reconstruct data for fault tolerance.  
> The **DAG** is the physical execution plan created by Spark's **DAGScheduler**. It translates the lineage graph into physical **Stages** and **Tasks** separated by shuffle boundaries, deciding *how* and *in what order* worker threads execute the code."

---

### Q4: What is the difference between Narrow and Wide Transformations?
> **Answer:**  
> - "**Narrow Transformations:** Each partition of the parent RDD contributes to **at most one** partition of the child RDD. Examples in our code: `filter()`, `select()`, `withColumn()`. They execute entirely within memory inside a single stage with zero network data transfer.
> - **Wide Transformations:** Multiple child partitions depend on data distributed across multiple parent partitions. Examples in our code: `Window.partitionBy()`, `groupByKey()`, `distinct()`. Wide transformations require a **Shuffle Exchange** across the network, which introduces a stage boundary and divides the DAG."

---

### Q5: How many Jobs, Stages, and Tasks are in this project, and how do you find them?
> **Answer:**  
> "We determine them by inspecting the **Spark Web UI (`localhost:4040`)** and executing `.explain(true)` on our DataFrames:
> 1. **Jobs:** A Job is created every time an **Action** is called (`.count()`, `.write.parquet()`, `fit()`). The Jobs tab lists them for each run.
> 2. **Stages:** Stages are created at **Shuffle Boundaries** caused by wide transformations, e.g. `Window.partitionBy(entity)` in `BuildForecastFeatures`. The Stages tab gives the exact count for a run; we read it there rather than quoting a fixed number.
> 3. **Tasks:** Each Stage creates tasks equal to the number of partitions in that stage. The read stage has tasks equal to the input splits; the window shuffle stages start with **64 Tasks** because `spark.sql.shuffle.partitions = 64`, which AQE may coalesce. Our 10 CPU cores run at most 10 of them at a time."

---

### Q6: How many Actions are in this code?
> **Answer:**  
> "Ma'am, in Spark, transformations are lazy and only actions trigger physical computation. Across our main pipeline modules, we invoke the following actions:
> 1. `.count()`: Called during data quality auditing to verify record counts.
> 2. `.write.mode("overwrite").partitionBy("year").parquet(...)`: Called to serialize deduplicated and canonical datasets to HDFS.
> 3. `pipeline.fit(trainDF)`: Called in MLlib to train the GBT, random-forest and linear-regression forecasting pipelines.
> 4. `model.transform(testDF)` followed by `.write.parquet(...)`: Called to score the test period and persist predictions.
> 5. `.start()`: Called on the `writeStream` of `PriceEventStream` to start Structured Streaming."

---

### Q7: Are you using the DataFrame or Dataset API, and why?
> **Answer:**  
> "In Scala, a `DataFrame` is an alias for an untyped `Dataset[Row]`. We use both strategically:
> 1. We use **DataFrames** for our large-scale batch ingestion, deduplication, and windowing because DataFrames leverage Spark's **Catalyst Optimizer** for physical execution planning and the **Tungsten Engine** for off-heap binary memory management (`UnsafeRow`) and whole-stage Java bytecode generation.
> 2. Our current streaming job (`PriceEventStream.scala`) also uses DataFrames, so batch and streaming share the same canonicalisation code (`CanonicalEvent.standardize`). Strongly-typed **Datasets** (`Dataset[MarketEntity]` with `flatMapGroupsWithState`) were used only in the legacy v1 stream (`Phase10StructuredStreamingReal.scala`), kept for history."

---

### Q8: What are Higher-Order Functions, and where did you use them?
> **Answer:**  
> "A **Higher-Order Function** is a functional programming concept in Scala where a function either takes another function as an argument or returns a function.  
> In our project, we used higher-order functions in:
> 1. `.map()` and `.filter()`: Passing anonymous lambda functions to filter negative price spreads (`row => row.getAs[Double]("max_price") >= row.getAs[Double]("min_price")`).
> 2. `SparkSetup.timed[T](label)(body: => T)`: Used Call-by-Name parameters to time execution blocks.
> 3. `foreachBatch(processBatch _)`: In `PriceEventStream` we pass our `processBatch` function to the streaming sink; it writes each micro-batch to silver and alerts."

---

### Q9: Why didn't your team use Hadoop MapReduce?
> **Answer:**  
> "MapReduce is a legacy disk-bound batch paradigm. It forces every computation into a rigid Map $\rightarrow$ Sort $\rightarrow$ Reduce flow, serializing all intermediate data to physical HDFS disks. Multi-pass rolling-window features and iterative tree training over 75 million rows would need many sequential MapReduce jobs, each writing to disk. Apache Spark executes multi-stage DAG pipelines in memory where possible, with Catalyst and Tungsten optimizations, and provides MLlib and Structured Streaming in the same engine."

---

### Q10: What cluster are you using?
> **Answer:**  
> "We use a hybrid distributed architecture:
> 1. **Storage Cluster:** A multi-container **Docker cluster** running **Hadoop HDFS 3.4.1** with 1 NameNode and 3 DataNodes with replication factor 3.
> 2. **Compute Engine:** Apache Spark 4.2.0 executing in `local[*]` mode utilizing all **10 physical CPU cores** of our Apple Silicon host machine as parallel worker threads with 4 GB driver memory.
> 3. **Cluster benchmark:** a 2-worker Docker Spark cluster (3 cores each, same host) ran W1 in 9.2 s and W2 in 14.4 s on 11.27 M rows.
> We do not claim a physical multi-rack YARN cluster; our setup demonstrates genuine distributed block storage, replication, and multi-core parallel compute on one host."

---

### Q11: Your forecasts beat "last price" by only 3–8%. Why is the improvement so small, and is it real?
> **Answer:**  
> "Ma'am, persistence (tomorrow's price = today's price) is a hard baseline for mandi prices: between 17% and 34% of target changes are exactly zero, because mandis re-quote the same price. So the honest measure is relative MAE against persistence on identical rows. On the 2025-01 to 2026-04 test it is **0.971, 0.953, 0.938 and 0.923** for next, 3, 7 and 14 days, i.e. 3–8% lower error.  
> It is real in three ways: (1) Diebold–Mariano tests reject equal accuracy at every horizon (p between 3.6e-47 and 1.3e-22); (2) the model beats persistence on 58.5–76.4% of individual series; (3) the frozen models, never refitted, still score **0.963, 0.955, 0.958 and 0.952** on six months of new data, 2026-04-22 to 2026-10-22. Squared-loss models do not beat persistence at the next-report horizon; absolute-loss GBT does. A per-series exponential smoother matches us at 1–3 days, so our clear advantage is at 7–14 days."

---

### Q12: Did you mix real data and synthetic data during machine learning?
> **Answer:**  
> "No, Ma'am. All features, training, validation and testing use real AGMARKNET data: the archive silver layer (75.64 million rows) and, for the frozen-model checks, the official data.gov.in back-fill (silver v2, 82.1 million rows).  
> A synthetic workload from v1 (`data_source = synthetic_scaled`) exists only for scalability tests. It was not re-run for AG-DATA 2.0 and was never used for any model."

---

### Q13: What is Catalyst Optimizer and what are its 4 phases?
> **Answer:**  
> "The **Catalyst Optimizer** is Spark SQL's rule-based and cost-based query optimization engine. It transforms user code through 4 sequential phases:
> 1. **Analysis:** Resolves column names, table references, and data types against the Catalog to produce an Analyzed Logical Plan.
> 2. **Logical Optimization:** Applies standard relational rules including **Predicate Pushdown** (filtering early to avoid reading unused rows) and **Projection Pruning** (dropping unselected columns).
> 3. **Physical Planning:** Generates multiple physical execution strategies (e.g., Broadcast Hash Join vs Sort Merge Join) and chooses the lowest cost plan using Cost-Based Optimization (CBO).
> 4. **Code Generation (Tungsten):** Compiles physical plan expressions directly into compact Java bytecode using whole-stage code generation, bypassing JVM virtual function dispatch overhead."

---

### Q14: What is the Tungsten Engine and how does it optimize memory?
> **Answer:**  
> "The **Tungsten Engine** is Spark's high-performance memory and execution engine:
> 1. **Off-Heap Binary Memory (`UnsafeRow`):** Bypasses standard JVM object allocation by storing rows in raw C-style byte arrays using `sun.misc.Unsafe`. This eliminates JVM garbage collection (GC) pauses and reduces object header overhead (a 4-byte integer in Java takes 16 to 24 bytes of object overhead; in Tungsten it takes exactly 4 bytes).
> 2. **Cache-Aware Computation:** Aligns data structures to L1/L2/L3 CPU cache lines to maximize CPU memory bandwidth and prevent cache misses.
> 3. **Whole-Stage Code Generation:** Synthesizes the entire pipeline of transformations inside a stage into a single clean Java `for` loop, keeping data inside CPU registers."

---

### Q15: What is Data Skew and how did your project handle it?
> **Answer:**  
> "Data skew occurs when one partition contains disproportionately more records than others, causing 9 out of 10 CPU cores to finish in seconds while the 10th core runs for minutes (the straggler task). In agricultural data, high-volume commodities and large markets can create such skew.  
> We handled data skew using three techniques:
> 1. Enabled **Adaptive Query Execution (AQE)** in `SparkSetup.scala` (`spark.sql.adaptive.skewJoin.enabled = true`), which dynamically splits large shuffle partitions at runtime.
> 2. Partitioned by the composite business key (`state`, `district`, `market`, `commodity`, `variety`, `date`) or by the series id, rather than by commodity alone, which spreads rows across many hash buckets.
> 3. Tuned `spark.memory.fraction = 0.6` to allow graceful spilling to disk rather than crashing with out-of-memory errors."

---

### Q16: What happened to the 95%-accuracy anomaly model in your earlier version?
> **Answer:**  
> "Ma'am, we audited our own v1 results and **withdrew** them. The accuracy, precision, recall, F1 and ROC-AUC figures for the v1 'real-time screening' classifier were not produced by any code or log in the repository; they were introduced by a single commit (`d760677`) that edited only the README and the dashboard. The v1 approach also had real methodological problems: its label was a function of its own features, the outlier bounds were fitted on all years including the test period, and the only logged v1 classifier (72.54% accuracy) was below its own 84.35% all-normal baseline. Details are in `docs/AUDIT_PRIOR_RESULTS.md`. That is why the project now leads with a properly evaluated forecasting benchmark."

---

### Q17: How good are your anomaly alerts, then?
> **Answer:**  
> "We evaluate them only where we have labels: on injected, labelled corruptions. Our production rule (a trailing robust z-score that never uses the report it scores) reaches **PR-AUC 0.704**, against **0.352** for the legacy commodity IQR rule, with precision 0.313, recall 0.846 and a false-positive rate of 0.019. There are no labels for real anomalies, so we claim **no accuracy for real anomalies**."

---

### 🏁 Summary Checklist Before Walking Into the Viva
- [x] Docker HDFS is running with 3 DataNodes (`docker exec -it agri-namenode hdfs dfsadmin -report`).
- [x] Spark can launch in local mode on 10 cores (`spark-shell --master "local[*]" ...`).
- [x] Spark UI opens at `http://localhost:4040` during execution.
- [x] HDFS UI opens at `http://localhost:9870`.
- [x] The app is ready on `http://localhost:8000` (Streamlit dashboard optional on `http://localhost:8501`).
- [x] Slide deck (`Big_Data_Analytics_Final_Presentation.pptx`) is open.
- [x] `docs/VERIFIED_METRICS.md` is open for any number you are asked about.
- [x] All 17 viva answers rehearsed!
