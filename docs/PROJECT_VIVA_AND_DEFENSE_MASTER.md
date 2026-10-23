# Comprehensive Project Viva, Concept & Defense Master Guide
### Agricultural Commodity Price Forecasting and Farmer Decision Support System
**Course:** 23AID302 — Big Data Analytics  
**Faculty Guide & Evaluator:** **Dr. Sreeja** | School of Artificial Intelligence, Amrita Vishwa Vidyapeetham  
**Team Members:** C Rishitha (`CB.AI.U4AID24109`), Karthikeya Y (`CB.AI.U4AID24163`), Ashwin Tyagi (`CB.AI.U4AID24167`), Kaushal S (`CB.AI.U4AID24168`)  
**Hardware Profile:** Apple Silicon Mac (10 CPU Cores, 16 GB Unified Memory)  
**Software Toolchain:** Apache Spark 4.2.0, OpenJDK 21.0.12, Scala 2.13.18, Hadoop HDFS 3.4.1, Apache Kafka 3.6.0  

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
│ Definition & Characteristics     │ The 5 Vs of Mandi Big Data: 132.86M rows (Volume), Kafka stream    │
│ (The 5 Vs of Big Data)           │ (Velocity), 2 CSV schemas (Variety), 535k dedup (Veracity),        │
│                                  │ Farmer distress-selling prevention (Value).                        │
│ Tools & Technologies             │ Hadoop HDFS 3.4.1 (storage), Apache Spark 4.2.0 (compute),         │
│                                  │ Apache Kafka (event bus), Docker (reproducible cluster).           │
│ Hadoop Ecosystem & HDFS          │ Distributed block storage (1 NameNode + 3 DataNodes), replication  │
│                                  │ factor 3, 128 MiB block size, rack awareness, and partition pruning│
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
│ Scala Type Hierarchy             │ Case classes inheriting from `AnyRef` (`MarketEntity`,             │
│ (`Any`, `AnyVal`, `AnyRef`)      │ `ArrivalRecord`), safe pattern matching and `Option`/`None` safety.│
│ Higher-Order Functions           │ `.map()`, `.filter()`, `.reduce()`, `.groupByKey()`, and passing   │
│                                  │ `updateMarketState` into `flatMapGroupsWithState()`.               │
│ Closures & Driver-Worker State   │ Driver serializes transformation closures across JVM threads;      │
│                                  │ handling broadcast variables and accumulator metrics.              │
│ OOP in Scala                     │ Companion objects for `SparkSession` builders; traits for data     │
│                                  │ loaders; case classes for strongly-typed streaming schemas.        │
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
│                                  │ Typed `Dataset[T]` for stateful streaming with case classes.       │
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
│ MLlib Pipeline Architecture      │ `Pipeline` encapsulating `Imputer`, `VectorAssembler`, and         │
│                                  │ `RandomForestClassifier` (100 parallel trees, depth 14, bins 128). │
│ Feature Engineering              │ 9 price features: modal, min, max, spread, spread ratio, rolling   │
│                                  │ 7-day mean, rolling 7-day stddev, statistical z-score, day of week.│
│ Class Imbalance & Tuning         │ Inverse class weighting ($w=1.2$) balancing 15.6% anomaly rate;    │
│                                  │ decision threshold calibrated to 0.35 on validation split.         │
│ Strict Temporal Splitting        │ Chronological split (<2024 train, 2024 val, 2025+ test) eliminating│
│ (Zero Data Leakage)              │ time-series lookahead bias; verified 95.66% test accuracy.         │
│ Case Study: Agribusiness Finance │ Detecting market manipulation, harvest gluts, and generating       │
│ & Real-Time Event Streaming      │ practical SELL/HOLD/WATCH/BUY farmer decision support advisories.  │
└──────────────────────────────────┴────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ 2. What We Did, How We Did It & Why: Step-by-Step Engineering Rationale

When Dr. Sreeja asks: *"Walk me through the pipeline. What did you build, how did you implement it, and why did you choose that design?"*, explain using these 7 sequential stages:

### Stage 1: Heterogeneous Raw Ingestion (132.86 Million Rows / 10.9 GB)
- **What:** Ingested two massive national agricultural datasets:
  1. *Daily Market Prices (Agmarknet 2001–2026):* 26 annual CSVs (75,984,017 records, 6.5 GB).
  2. *India Mandi Dataset:* 325 commodity-specific CSVs (56,879,072 records, 4.4 GB).
- **How:** Implemented explicit `StructType` schema definitions in Scala with RFC-4180 quote-escaping to prevent embedded commas (e.g., `"Sesamum (Sesame,Gingelly,Til)"`) from corrupting column alignment.
- **Why:** Avoided Spark's automatic schema inference (`inferSchema = true`), which forces two full sequential scans of 11 GB of raw text, cutting ingestion initialization time from minutes to milliseconds.

### Stage 2: Distributed Replicated Storage in Apache Hadoop HDFS
- **What:** Deployed an enterprise-grade HDFS cluster inside Docker container services.
- **How:** Configured 1 NameNode (`agri-namenode` on port 9000/9870) and 3 independent DataNodes (`agri-datanode1`, `agri-datanode2`, `agri-datanode3`) with **Replication Factor = 3** and **128 MiB block sizes**.
- **Why:** 
  1. *Fault Tolerance:* If any DataNode crashes, the remaining two containers retain complete block replicas.
  2. *Block Sizing:* 128 MiB blocks match the sequential streaming read profile of columnar Snappy Parquet while preventing NameNode namespace heap bloat.

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
- **Why:** Using standard `to_date()` throws unrecoverable runtime exceptions upon hitting dirty or malformed strings, causing 2-hour batch jobs to abort. `try_to_date` safely yields `null`, allowing graceful filtering.

### Stage 4: Map-Side Composite Business-Key Deduplication
- **What:** Audited and purged **535,261 duplicate transactions** across the raw corpus.
- **How:** Avoided naive `df.distinct()`. Instead, partitioned over a 7-column composite business key (`state`, `district`, `market`, `commodity`, `variety`, `date`) ordered by validity and price spread, filtering for `row_number() === 1`.
- **Why:** A whole-row `distinct()` hashes all 10 columns across 133 million rows, triggering catastrophic shuffle skew and JVM driver OutOfMemoryError. Our window-based composite approach enabled map-side partial combine, finishing in **4.2 minutes with zero disk spills**.

### Stage 5: In-Memory Window Rolling Analytics & Anomaly Labelling
- **What:** Generated localized 7-day statistical price baselines across 3,000+ mandis.
- **How:** Applied Spark SQL Window specifications:
  ```scala
  val w7d = Window.partitionBy("state", "market", "commodity")
    .orderBy(col("date").cast("timestamp").cast("long"))
    .rangeBetween(-7 * 86400, -1) // Excludes current day
  ```
  Computed rolling mean, rolling standard deviation, and statistical $z$-score:
  $$z = \frac{\text{modal\_price} - \mu_{7d}}{\sigma_{7d}}$$
- **Why:** Window partitioning parallelizes rolling calculations per commodity. Excluding the current arrival (`rangeBetween(-7 * 86400, -1)`) guarantees **zero lookahead bias and zero data leakage**.

### Stage 6: Distributed Machine Learning with Spark MLlib Random Forest
- **What:** Trained a high-precision real-time transaction anomaly screening model.
- **How:** Assembled 9 price features into dense vectors via `VectorAssembler`, applied inverse class weighting ($w=1.2$) to counteract the 15.6% anomaly prevalence, and trained a `RandomForestClassifier` (100 trees, depth 14, 128 continuous feature bins).
- **Why:** Random Forest handles non-linear price spread boundaries, is resilient against extreme agricultural price outliers, and trains trees in parallel across CPU threads. Evaluated on **48,354 untouched 2025+ records**, achieving **95.66% accuracy and 86.55% precision**.

### Stage 7: Stateful Event Streaming via Apache Kafka & Structured Streaming
- **What:** Replayed real market transactions through an event bus to simulate live daily arrivals.
- **How:** Produced 15,000 real records into Kafka topic `agri-market-real-replay`. Spark Structured Streaming consumed micro-batches, maintaining a per-market 7-day rolling state buffer via `flatMapGroupsWithState`, scoring transactions against the frozen MLlib model, and persisting alerts to HDFS with fault-tolerant checkpoints.
- **Why:** Decouples high-velocity ingestion from ML scoring. `flatMapGroupsWithState` enables custom state management across irregular arrival intervals without rigid tumbling window watermarks.

---

## 🎤 3. Live Viva Presentation Playbook for Dr. Sreeja

Use this exact timing and structure during your 15-minute presentation:

| Slide / Section | Time | What to Say (Presenter Script) | Core Concept to Emphasize |
|:---:|:---:|---|---|
| **Slide 1: Title & Framing** | 1.0 min | *"Good morning Dr. Sreeja. Our project is Agricultural Commodity Price Forecasting and Farmer Decision Support System using Hadoop HDFS and Apache Spark. Our team members are Rishitha, Karthikeya, Ashwin, and Kaushal. Our objective is an end-to-end Big Data pipeline processing 132.86M real market records, detecting price shocks with MLlib, and streaming real-time alerts."* | Distributed infrastructure over 132.86M real rows. |
| **Slide 2: Problem & 5 Vs** | 1.5 min | *"Farmers face 40%+ price collapses during seasonal harvest gluts, forcing distress selling. Single-node Pandas crashes with OutOfMemoryError on 10.9 GB CSVs when computing multi-year rolling windows. We solve this using distributed storage in HDFS and parallel compute in Spark. Our domain actions translate anomaly signals into practical SELL, HOLD, WATCH, and BUY advisories."* | Pandas OOM vs Distributed HDFS + Spark. |
| **Slide 3: Datasets & Scale** | 1.5 min | *"We ingest 132.86M raw rows across 26 annual CSVs and 325 commodity files. We eliminate 535k duplicate transactions to produce 132.32M deduped rows (1.2 GB Parquet, 9:1 compression). Our quality canonical layer contains 93.41M verified records. All ML models strictly train on this real data. An isolated 350M synthetic workload in Phase 11 was used exclusively to test 18 GB HDFS scalability."* | Transparent 5-tier data scale breakdown. |
| **Slide 4: Architecture** | 2.0 min | *"Our system architecture is dual-path: a batch pipeline for data engineering and model training, and a streaming pipeline via Kafka and Structured Streaming. HDFS runs 1 NameNode and 3 DataNodes in Docker with replication factor 3. Spark executes on host CPU cores in `local[*]` mode. HDFS DataNodes store blocks; they are not Spark compute executors."* | Dual-path workflow; Docker HDFS vs local Spark. |
| **Slide 5: Spark DAG & Engine** | 2.5 min | *"We use DataFrames rather than RDDs to exploit Catalyst optimization (predicate pushdown, projection pruning) and Tungsten off-heap binary memory with whole-stage code generation. Transformations are lazy; actions trigger physical DAG execution. Wide transformations like `Window.partitionBy` create shuffle boundaries, dividing the DAG into 13 distinct stages. We partition across 200 shuffle partitions."* | Catalyst, Tungsten, Narrow vs Wide, 13 DAG Stages. |
| **Slide 6: Scala Implementation** | 2.0 min | *"In Scala, we use `coalesce` with `try_to_date` to prevent corrupt dates from aborting batch jobs. We replace full-row `distinct()` with a 7-column composite window deduplication, avoiding driver memory exhaustion. In streaming, `flatMapGroupsWithState` maintains a stateful 7-observation buffer per `MarketEntity` across irregular arrivals."* | Resilient parsing, composite dedup, stateful streaming. |
| **Slide 7: ML Pipeline** | 1.5 min | *"We engineer 9 price features. To prevent time-series data leakage, we enforce a strict chronological split: training on pre-2024 data (721k rows), tuning depth and threshold on 2024 validation data, and testing on untouched 2025+ records (48k rows). Task A is next-day forecasting, while Task B is real-time anomaly screening."* | Temporal split, zero data leakage, Task A vs Task B. |
| **Slide 8: Results & Metrics** | 2.0 min | *"On 48,354 unseen 2025+ test records, our production model achieves 95.66% accuracy, 86.55% precision, 85.47% recall, and an 86.01% F1-score with an ultra-low 2.46% false alarm rate. An All-Normal model gets 84.35% accuracy but 0% recall. Our Kafka replay validated 1,200 events/sec throughput with sub-800ms latency."* | 95.66% Acc, 86.55% Prec, 4-card confusion matrix. |
| **Slide 9: Challenges & Limits** | 1.0 min | *"We solved JDK 21 reflection using `--add-opens`, date crashes via coalesce, and shuffle OOM via composite dedup. We honestly report that Spark runs in `local[*]` mode rather than a multi-node YARN cluster, streaming uses historical replay, and automated SMS dispatch is future work. In conclusion, the system processes 132.9M real rows and delivers 95.66% accurate alerts."* | JVM reflection, OOM resolution, honest boundaries. |
| **Slide 10: References** | 0.5 min | *"Our project evidence, logs, and code are open-source on GitHub at `github.com/kaushalrog/AG-DATA`. Thank you, Dr. Sreeja. We are now open for viva questions."* | GitHub link, project deliverables, open defense. |

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

# Show HDFS block replication and Parquet storage in /agri/processed/canonical
docker exec -it agri-namenode hdfs fsck /agri/processed/canonical -files -blocks -locations
```
*What to show her:* Point to **"Live datanodes (3)"** and **"Replication: 3"** in the terminal output.

---

### Command 2: Launch Spark in Local Mode with All 10 Laptop Cores
Show how to start an interactive Spark session leveraging all 10 cores on your Apple Silicon Mac:
```bash
/opt/miniconda3/bin/spark-shell \
  --master "local[*]" \
  --driver-memory 4g \
  --conf "spark.sql.shuffle.partitions=200" \
  --conf "spark.driver.host=127.0.0.1" \
  --conf "spark.driver.extraJavaOptions=--add-opens=java.base/java.lang=ALL-UNNAMED --add-opens=java.base/java.util=ALL-UNNAMED --add-opens=java.base/sun.util.calendar=ALL-UNNAMED"
```
*What to explain:* 
- `--master local[*]`: Tells Spark to use **all 10 CPU cores** as worker execution threads.
- `--driver-memory 4g`: Allocates 4 GB of JVM heap to the driver.
- `--conf spark.sql.shuffle.partitions=200`: Configures 200 partitions for wide transformations.
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

### Command 4: Launch the Streamlit Analytics Dashboard
Show the interactive geospatial dashboard:
```bash
# In project root
streamlit run src/dashboard/app.py --server.port 8501
```
Open your browser to: **`http://localhost:8501`**  
*What to show her:* Point to the price trend charts, the mandi anomaly detection heatmaps, and the real-time alert logs.

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
| **Job** | Highest-level execution unit | Triggered whenever an **Action** is invoked (`.count()`, `.write.parquet()`, `.collect()`, `model.fit()`). | **1 Job per Action.** In `DataPipelineMaster`, there are **6 distinct Jobs** corresponding to validation counts and Parquet writes. |
| **Stage** | A sub-unit of a Job | Created at **Shuffle Boundaries** whenever a **Wide Transformation** occurs (`Window.partitionBy`, `groupByKey`, `repartition`). Narrow transformations are pipelined into the same stage. | **Number of Stages = Number of Shuffle Exchanges + 1.** In our feature engineering run, there were **13 distinct completed Stages**. |
| **Task** | Smallest unit of execution | Represents the execution of a stage's logic on a **single data partition**. Dispatched to a worker thread. | **Total Tasks in Stage = Number of Partitions in that Stage.** Initial read stage has tasks equal to input files/blocks; shuffle stages have **200 tasks**. |

---

### D. Partitions & How Your Laptop Cores Are Utilized

#### How Your Apple Silicon 10-Core CPU Executes Spark:
- **Hardware Cores:** Your Mac has an **Apple Silicon M-series chip with 10 CPU cores**.
- **Worker Threads:** Passing `--master local[*]` tells the JVM:
  $$\text{Execution Threads} = \text{Runtime.getRuntime.availableProcessors()} = 10$$
  Spark launches **1 Driver JVM** containing **10 parallel worker execution threads**.
- **Task Execution Waves:**
  - In Stage 2 (Window Aggregation), Spark sets `spark.sql.shuffle.partitions = 200`.
  - Spark creates **200 Tasks**.
  - Your 10 CPU cores can execute **exactly 10 tasks simultaneously in parallel**.
  - Therefore, Spark executes the 200 tasks in **20 successive waves of 10 tasks**:
    $$\text{Waves} = \frac{200 \text{ Tasks}}{10 \text{ Cores}} = 20 \text{ Parallel Batches}$$
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
| **`http://localhost:8501`** | **Streamlit Dashboard** | Real-time geospatial mandi map, commodity price trends, live anomaly alerts. |
| **`localhost:9000`** | **HDFS RPC (`fs.defaultFS`)** | Underlying inter-process protocol used by Spark to read/write Parquet files to HDFS (`hdfs://localhost:9000/...`). |
| **`localhost:9092`** | **Apache Kafka Broker** | Native event transport broker streaming micro-batch messages into topic `agri-market-real-replay`. |

---

## 💡 7. Comprehensive Viva Voce Q&A Master Repository

### Q1: What is the difference between Hadoop and DAG?
> **Defensible Answer:**  
> "Ma'am, **Hadoop** is an entire distributed framework consisting of **HDFS** for distributed storage, **MapReduce** for compute, and **YARN** for cluster resource negotiation.  
> A **DAG (Directed Acyclic Graph)**, on the other hand, is a mathematical data structure and execution model used by Apache Spark. In Hadoop MapReduce, every job was strictly hardcoded into a 2-stage cycle: Map $\rightarrow$ Shuffle $\rightarrow$ Reduce, writing all intermediate data to physical disk. Spark replaces this with an arbitrary DAG of multi-stage transformations kept entirely in memory, eliminating iterative disk I/O."

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
> 1. **Jobs:** A Job is created every time an **Action** is called. In `DataPipelineMaster`, there are **6 Jobs** triggered by `.count()` and `.write.parquet()` calls.
> 2. **Stages:** Stages are created at **Shuffle Boundaries** caused by wide transformations. In our feature engineering run, Spark's DAGScheduler created **13 distinct Stages**.
> 3. **Tasks:** Each Stage creates tasks equal to the number of partitions in that stage. In our initial file read stage, there are tasks equal to the input Parquet blocks; in our Window shuffle stages, there are exactly **200 Tasks** because `spark.sql.shuffle.partitions = 200`. Our 10 CPU cores execute these 200 tasks in 20 parallel waves."

---

### Q6: How many Actions are in this code?
> **Defensible Answer:**  
> "Ma'am, in Spark, transformations are lazy and only actions trigger computation. Across our main pipeline modules, we invoke the following actions:
> 1. `.count()`: Called during data quality auditing to verify record counts.
> 2. `.write.mode("overwrite").partitionBy("year").parquet(...)`: Called to serialize deduplicated and canonical datasets to HDFS.
> 3. `pipeline.fit(trainDF)`: Called in MLlib to train the Random Forest Classifier.
> 4. `model.transform(testDF)` followed by `.write.parquet(...)`: Called to evaluate test data and persist prediction scores.
> 5. `.start()`: Called on `statefulStream.writeStream` to initiate Structured Streaming."

---

### Q7: Are you using the DataFrame or Dataset API, and why?
> **Defensible Answer:**  
> "In Scala, a `DataFrame` is an alias for a untyped `Dataset[Row]`. We use both strategically:
> 1. We use **DataFrames** for our large-scale batch ingestion, deduplication, and windowing because DataFrames leverage Spark's **Catalyst Optimizer** for physical execution planning and the **Tungsten Engine** for off-heap binary memory management and whole-stage Java bytecode generation.
> 2. We use strongly-typed **Datasets (`Dataset[MarketEntity]`)** in our real-time streaming pipeline (`StreamingAnomalyDetector.scala`) because `flatMapGroupsWithState` requires compile-time type safety and custom serialization across state updates."

---

### Q8: What are Higher-Order Functions, and where did you use them?
> **Defensible Answer:**  
> "A **Higher-Order Function** is a functional programming concept in Scala where a function either takes another function as an argument or returns a function.  
> In our project, we used higher-order functions in:
> 1. `.map()` and `.filter()`: Passing anonymous lambda functions to filter negative price spreads (`row => row.getAs[Double]("max_price") >= row.getAs[Double]("min_price")`).
> 2. `flatMapGroupsWithState()`: We passed our custom `updateMarketState` function as a parameter to manage stateful rolling window buffers per market entity across Kafka streaming micro-batches."

---

### Q9: Why didn't your team use Hadoop MapReduce?
> **Defensible Answer:**  
> "MapReduce is a legacy disk-bound batch paradigm. It forces every computation into a rigid Map $\rightarrow$ Sort $\rightarrow$ Reduce flow, serializing all intermediate data to physical HDFS disks. Executing multi-pass 7-day rolling window aggregations and iterative Random Forest tree training across 133 million rows in MapReduce would require dozens of sequential disk read/write cycles, taking many hours. Apache Spark executes multi-stage DAG pipelines in-memory with Catalyst and Tungsten optimizations, running up to **100× faster** than MapReduce."

---

### Q10: What cluster are you using?
> **Defensible Answer:**  
> "We use a hybrid distributed architecture:
> 1. **Storage Cluster:** A multi-container **Docker cluster** running **Hadoop HDFS 3.4.1** with 1 NameNode and 3 DataNodes with replication factor 3.
> 2. **Compute Engine:** Apache Spark 4.2.0 executing in `local[*]` mode utilizing all **10 physical CPU cores** of our Apple Silicon host machine as parallel worker threads with 4 GB driver memory.
> We do not falsely claim a physical multi-rack YARN cluster; our setup demonstrates genuine distributed block storage, replication, and multi-core parallel compute."

---

### Q11: How do you prove your model did not just memorize the majority class?
> **Defensible Answer:**  
> "Ma'am, in our dataset, normal transactions represent 84.35% and anomalies represent 15.65%. A naive 'All-Normal' baseline model that simply predicts 0 for every transaction achieves 84.35% accuracy, but its **Recall is 0.00%** and **Precision is 0.00%**.  
> Our tuned Random Forest production model achieves **95.66% accuracy, 86.55% precision, 85.47% recall, and an 86.01% F1-score** on 48,354 completely unseen test records from 2025+. Because both Precision and Recall exceed 85%, the model genuinely captures anomalies while keeping false alarms strictly at 2.46%."

---

### Q12: Did you mix real data and synthetic data during machine learning?
> **Defensible Answer:**  
> "No, Ma'am. All feature engineering, model training, validation, and testing strictly used the **93.41 million real canonical agricultural records**.  
> The 350 million synthetic records were generated in Phase 11 solely to test HDFS block allocation, storage scalability, and shuffle performance under extreme scale to satisfy the course's ~18 GB scale requirement. Real data and synthetic data are stored in completely separate HDFS paths and were never mixed into ML training."
