# 🌾 AGRICULTURAL COMMODITY BIG DATA ANALYTICS: MASTER SYLLABUS, VIVA & DEFENSE GUIDE
### End-to-End Distributed Architecture, Spark DAG Analysis, Engine Optimization, and Faculty Viva Defense
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
**Distributed Cluster Stack:** Apache Spark 4.2.0, Hadoop HDFS 3.4.1 (Docker 4-Node Cluster), Apache Kafka 3.6.0, Scala 2.13.18, OpenJDK 21.0.12  

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
   - Detailed, mathematically and architecturally defensible answers to all 15 faculty questions.

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
   Importance of Big Data              - Volume: 132.86M raw records (10.9 GB raw CSVs, 1.2 GB Parquet).
   (The 5 Vs)                          - Velocity: Real-time arrivals streaming via Apache Kafka at 1,200 msg/s.
                                       - Variety: 2 distinct schemas (26 annual Agmarknet CSVs + 325 mandi CSVs).
                                       - Veracity: Purging 535,261 duplicate transactions; handling dirty dates.
                                       - Value: Preventing farmer distress selling and market cartelization.

2. Tools & Technologies for            - Apache Spark 4.2.0: In-memory distributed query and ML engine.
   Big Data Analytics                  - Hadoop HDFS 3.4.1: Distributed, replicated fault-tolerant block storage.
                                       - Apache Kafka 3.6.0: Distributed publish-subscribe event broker.
                                       - Docker: Containerization for multi-node HDFS cluster isolation.

3. State-of-the-Art Computing          Transition from 1st Gen (Disk-bound MapReduce) to 2nd Gen (In-memory Spark
   Paradigms & Platforms               DAG execution). We demonstrate why iterative 7-day rolling window
                                       analytics and Random Forest training fail on MapReduce due to disk I/O.

4. Hadoop Ecosystem in Brief           - HDFS: 1 NameNode (metadata master) + 3 DataNodes (distributed block slaves).
                                       - Block Size: 128 MiB blocks tailored for sequential columnar Parquet reads.
                                       - Replication Factor: 3 (rack-tolerant fault recovery).
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

2. Mutable vs Immutable Structures    - Strict use of `val` throughout `SparkSetup.scala`, `Deduplicate.scala`, etc.
                                       - Zero use of mutable collections (`var`, `ArrayBuffer`).
                                       - Spark DataFrames and Datasets are strictly immutable; operations produce
                                         new DataFrames, enabling lineage-based fault recovery.

3. Scala Collections & ConsList        - Scala `Seq`, `List`, `Array`, and `Map` used for schema column sequences.
                                       - `ConsList` (`head :: tail`) concept used in recursive parsing of schemas
                                         and dynamically building composite window expressions.

4. Type Hierarchy (Any, AnyVal,        - All custom domain models inherit from `AnyRef` via Scala `case class`es:
   AnyRef, Option, Nothing, Null)        `case class MarketEntity(state: String, market: String, commodity: String)`
                                       - `Option[T]` (`Some` / `None`) utilized to handle missing arrival metrics
                                         instead of throwing unhandled `NullPointerException`s.

5. Higher-Order Functions              - Passing functions as first-class citizens into transformations:
                                         `DataQuality.businessKey.map(col)` -> `map` takes function `col`.
                                       - Call-by-Name parameters in `SparkSetup.timed[T](label)(body: => T)`.
                                       - `flatMapGroupsWithState` accepts higher-order state update functions.

6. Closures & Concurrency              - Worker threads execute serialization closures dispatched by the Driver.
                                       - Multi-threaded parallel execution across 10 Apple Silicon CPU cores
                                         via Spark's `local[*]` multithreading execution pool.

7. Tail Recursion & OOP in Scala       - Sealed traits and companion objects (`object SparkSetup`, `object Deduplicate`).
                                       - Tail-recursive retry loops for resilient HDFS socket connections.
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
                                       - Datasets (`Dataset[T]`): Used in Structured Streaming for type-safety.
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

2. Building ML Pipelines in Spark      `org.apache.spark.ml.Pipeline` chaining:
                                       `Imputer` (median) -> `VectorAssembler` (9 features) -> `RandomForestClassifier`

3. Feature Engineering                 Engineered 9 agricultural price indicators:
                                       `previous_modal_price`, `price_change`, `price_change_pct`, `price_range`,
                                       `relative_price_range`, `rolling_7_observation_avg`,
                                       `rolling_7_observation_stddev`, `z_score`, `day_of_week`.

4. Temporal Splitting & Class Tuning   - Strict chronological split: <2024 (train, 721k rows), 2024 (val, 137k rows),
                                         2025+ (untouched test, 48k rows). Zero temporal lookahead leakage.
                                       - Inverse class weighting ($w=1.2$) resolving 84.35% / 15.65% class imbalance.

5. Domain Case Study: Agribusiness     - Agribusiness market manipulation and supply glut detection.
   Farmer Decision Support System      - Actionable farmer recommendations:
                                         * SELL: Positive price spike near historical ceiling before harvest glut.
                                         * HOLD: Short-term panic crash with expected mean-reversion.
                                         * WATCH: High volatility/spread; monitor adjacent district mandis.
                                         * BUY: Procurement advisory for food processors/wholesalers.
========================================================================================================
```

---

# ⚙️ 2. STEP-BY-STEP PROJECT EXECUTION: WHAT, HOW & WHY

When Dr. Sreeja asks you to explain **"What you did, how you did it, and why you did it"**, walk her through this systematic 12-step engineering lifecycle:

```
                                  PIPELINE ARCHITECTURE
                                  
   [Raw CSVs: 132.86M Rows] ──(Explicit StructType Ingestion)──> [Unified DataFrame]
                                                                        │
   [Docker HDFS: 3 Replicas] <──(Distributed Block Storage)─────────────┤
                                                                        ▼
   [Quality Cleansing Layer] <──(try_to_date + positive price filter)───┤
                                                                        ▼
   [Deduplication Layer] <──(Window Composite Key rn=1)───────────────┤ (Purged 535k rows)
                                                                        ▼
   [Snappy Parquet Layer] <──(Columnar 9:1 Compression)────────────────┤ (10.9GB -> 1.2GB)
                                                                        ▼
   [Window Analytics Layer] <──(7-Day Rolling Lag/Mean/StdDev/Z)────────┤ (Zero Data Leakage)
                                                                        ▼
   [MLlib Random Forest] <──(VectorAssembler + Class Weighting)─────────┤ (95.66% Accuracy)
                                                                        ▼
   [Kafka Event Bus] ──(1,200 msg/s)──> [Structured Streaming] ───────> [Streamlit UI]
```

### Step 1: Environment & Toolchain Configuration
- **WHAT:** Configured an enterprise-grade Big Data environment using Apache Spark 4.2.0, Hadoop 3.4.1 in Docker, OpenJDK 21.0.12, and Scala 2.13.18.
- **HOW:** Implemented `SparkSetup.scala` to centralize SparkSession creation with JVM configuration flags (`--add-opens=java.base/java.lang=ALL-UNNAMED`).
- **WHY:** Java 21 enforces strict modular encapsulation. Without explicit reflection permissions, Spark's off-heap memory allocators and Kryo serializers crash on startup with `IllegalAccessException`.

### Step 2: High-Throughput Schema Ingestion (132.86 Million Rows / 10.9 GB)
- **WHAT:** Ingested two massive national datasets: 26 annual CSVs (2001–2026, 75.98M rows) and 325 commodity CSVs (56.88M rows).
- **HOW:** Defined explicit `StructType` schemas in `Schemas.scala` and enabled RFC-4180 quote-escaping.
- **WHY:** Using Spark's `inferSchema = true` forces two complete sequential scans of 11 GB of raw text across disk, taking over 15 minutes. Supplying an explicit schema completes metadata resolution in **under 200 milliseconds** and prevents malformed row splits on embedded commas (e.g., `"Sesamum (Sesame,Gingelly,Til)"`).

### Step 3: Distributed Replicated Storage in Hadoop HDFS
- **WHAT:** Deployed an HDFS cluster in Docker with 1 NameNode (`agri-namenode`) and 3 DataNodes (`agri-datanode1/2/3`).
- **HOW:** Configured `dfs.replication = 3` and `dfs.blocksize = 134217728` (128 MiB).
- **WHY:** 
  1. *Fault Tolerance:* If any DataNode container crashes or experiences block corruption, the remaining two nodes provide seamless data recovery.
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
- **WHAT:** Audited and purged **535,261 duplicate transactions** across the raw corpus.
- **HOW:** Partitioned over a 7-column composite business key (`state`, `district`, `market`, `commodity`, `variety`, `arrival_date`), ranked rows by data quality and price spread, and filtered for `row_number() === 1`.
- **WHY:** A naive `df.distinct()` hashes all 10 columns across 133 million rows, triggering massive shuffle data transfer and JVM OutOfMemory errors. Window-based deduplication executes map-side partial sorting, completing in **4.2 minutes with zero disk spills**.

### Step 6: Parquet Columnar Serialization & Partition Pruning
- **WHAT:** Converted 10.9 GB of bloated, unindexed CSV text into 1.2 GB of Snappy-compressed columnar Parquet, partitioned by `year`.
- **HOW:** `df.write.mode("overwrite").partitionBy("year").parquet(outputPath)`
- **WHY:** 
  1. *Storage Efficiency:* Snappy compression achieved a **9:1 compression ratio**.
  2. *Column Pruning:* Analytical queries reading only `modal_price` scan only the relevant column chunks, skipping 80% of byte I/O.
  3. *Partition Pruning:* Queries filtering for `year >= 2024` skip reading directories from 2001 to 2023 entirely.

### Step 7: In-Memory Window Rolling Analytics (Zero Leakage)
- **WHAT:** Calculated localized 7-day rolling baselines (mean $\mu_{7d}$, standard deviation $\sigma_{7d}$, and $z$-score).
- **HOW:** Applied a Spark SQL Window:
  ```scala
  val w = Window.partitionBy("state", "market", "commodity")
    .orderBy(col("arrival_date").cast("timestamp").cast("long"))
    .rangeBetween(-7 * 86400, -1) // Excludes current day
  ```
- **WHY:** Including the current day's price in its own historical baseline creates severe **lookahead bias (data leakage)**. Excluding current arrival (`rangeBetween(-7*86400, -1)`) ensures mathematical integrity.

### Step 8: Distributed MLlib Pipeline Architecture
- **WHAT:** Built a production-grade ML pipeline classifying price shocks.
- **HOW:** Assembled features with `VectorAssembler`, handled missing values via `Imputer` (median), and trained a `RandomForestClassifier` (100 trees, depth 14, 128 continuous feature bins).
- **WHY:** Random Forest captures non-linear price spread boundaries, is robust against agricultural outliers, and trains trees in parallel across CPU cores.

### Step 9: Strict Temporal Model Validation
- **WHAT:** Evaluated the ML model on completely untouched data from 2025 onwards.
- **HOW:** Enforced a strict chronological split: training (<2024, 721k rows), validation (2024, 137k rows), and test (2025+, 48,354 rows).
- **WHY:** Random $k$-fold cross-validation or random `randomSplit([0.8, 0.2])` leaks future seasonal trends into the past, artificially inflating accuracy. Our chronological split proves genuine real-world generalization (**95.66% test accuracy, 86.55% precision**).

### Step 10: Event Streaming via Apache Kafka & Structured Streaming
- **WHAT:** Built a real-time ingestion and anomaly detection pipeline.
- **HOW:** Streamed 15,000 real records through Kafka topic `agri-market-real-replay`. Spark Structured Streaming consumed micro-batches and maintained a stateful 7-observation window using `flatMapGroupsWithState`.
- **WHY:** Agricultural arrivals occur irregularly. `flatMapGroupsWithState` enables custom stateful session buffers per market entity without rigid tumbling window watermarks.

### Step 11: Scalability Stress Testing (350M Synthetic Workload)
- **WHAT:** Generated and processed 350 million synthetic records (7.25 GiB Parquet) in Phase 11.
- **HOW:** Used statistical distributions derived from real canonical data to stress-test HDFS block allocation and Spark shuffle performance.
- **WHY:** Satisfied the course requirement for ~18 GB scale under extreme load while strictly isolating synthetic data from real ML training.

### Step 12: Farmer Decision Support Dashboard
- **WHAT:** Developed an interactive geospatial dashboard in Streamlit.
- **HOW:** Visualized mandi price anomalies, 7-day trend cones, and actionable advisories (SELL, HOLD, WATCH, BUY).
- **WHY:** Bridges the gap between complex Big Data analytics and non-technical agricultural stakeholders.

---

# 🎤 3. HOW TO PRESENT IN FRONT OF DR. SREEJA (15-MIN PLAYBOOK)

Use this exact script and timing guide during your team presentation:

| Slide | Target Time | Speaker | What to Say (Verbatim Presenter Script) | Key Academic Terminology |
|:---:|:---:|:---:|---|---|
| **1** | **1.0 min** | Kaushal / Team Lead | *"Good morning Dr. Sreeja. Our project is the Agricultural Commodity Price Forecasting and Farmer Decision Support System using Hadoop HDFS and Apache Spark. Our team members are Rishitha, Karthikeya, Ashwin, and Kaushal. Our objective is an end-to-end Big Data pipeline processing 132.86 million real market records, detecting price shocks with Spark MLlib, and streaming live advisories via Kafka."* | Distributed Big Data Pipeline, 132.86M real rows. |
| **2** | **1.5 min** | Rishitha | *"Ma'am, Indian agricultural markets suffer from extreme price volatility. During harvest gluts, localized mandi prices crash by over 40% in days, forcing distress selling. Single-node tools like Pandas fail with OutOfMemory errors on 11 GB CSVs when executing rolling window aggregations. We solve this by implementing distributed storage in HDFS and in-memory parallel computation in Spark, mapping anomaly signals into actionable SELL, HOLD, WATCH, and BUY farmer advisories."* | 5 Vs of Big Data, Pandas OOM, Farmer Distress Selling. |
| **3** | **1.5 min** | Karthikeya | *"We ingested 132.86 million raw records from Agmarknet. We purged 535,261 duplicate transactions using a 7-column composite key window to produce 132.32 million deduplicated rows, compressed to 1.2 GB Snappy Parquet—a 9:1 space reduction. Our quality canonical layer contains 93.41 million records, which is the ONLY dataset used for ML training. An isolated 350M synthetic dataset was created in Phase 11 solely to test 18 GB HDFS scalability."* | 5-Tier Data Scale Disambiguation, 9:1 Compression Ratio. |
| **4** | **2.0 min** | Ashwin | *"Our architecture is dual-path: a batch analytics path for data engineering and ML training, and a real-time streaming path via Kafka and Structured Streaming. Our HDFS cluster runs inside Docker with 1 NameNode and 3 DataNodes with replication factor 3. Spark executes in `local[*]` mode utilizing all 10 physical CPU cores on our host machine. HDFS stores blocks; it does not execute Spark tasks."* | Dual-Path Architecture, Docker HDFS, Spark local[*] Cores. |
| **5** | **2.5 min** | Kaushal | *"In Spark, we use DataFrames rather than RDDs to exploit Catalyst optimization (predicate pushdown, projection pruning) and Tungsten off-heap binary memory (`UnsafeRow`). Transformations are lazy; actions compile the DAG into physical Stages at shuffle boundaries. In our feature engineering job, `Window.partitionBy` creates a ShuffleExchange, dividing execution into 13 distinct Stages across 200 shuffle partitions."* | Catalyst Optimizer, Tungsten, Narrow vs Wide, 13 DAG Stages. |
| **6** | **2.0 min** | Rishitha | *"In Scala, we avoid unhandled exceptions by wrapping multi-format date strings in `coalesce(try_to_date(...))`. Instead of a driver-crashing `distinct()`, our composite window deduplication executes map-side sorting in 4.2 minutes with zero disk spills. In streaming, `flatMapGroupsWithState` maintains a 7-observation buffer per `MarketEntity` across irregular arrival intervals."* | Functional Programming, Resilient Parsing, Stateful Streaming. |
| **7** | **1.5 min** | Karthikeya | *"We engineer 9 price features including 7-day rolling mean, stddev, and z-score. To prevent data leakage, we enforce a strict chronological split: training on pre-2024 data (721k rows), tuning on 2024 validation data, and testing on untouched 2025+ records (48k rows). We differentiate Task 1 (Next-Day Forecasting) from Task 2 (Real-Time Screening)."* | Zero Temporal Leakage, VectorAssembler, Imputer, Class Weights. |
| **8** | **2.0 min** | Ashwin | *"On 48,354 unseen 2025+ test records, our tuned Random Forest model achieves 95.66% accuracy, 86.55% precision, 85.47% recall, and an 86.01% F1-score with an ultra-low 2.46% false positive rate. An All-Normal baseline achieves 84.35% accuracy but 0% recall, proving our model genuinely learns minority anomalies. Kafka replay validated 1,200 events/sec throughput with sub-800ms latency."* | 95.66% Accuracy, 86.55% Precision, Confusion Matrix, AUC. |
| **9** | **1.0 min** | Kaushal | *"We overcame JVM 21 reflection barriers using `--add-opens`, date crashes via coalesce, and shuffle OOM via composite dedup. We honestly report that Spark runs in `local[*]` mode rather than multi-node YARN, and automated SMS dispatch is future work. In conclusion, the system reliably processes 132.9M real rows and delivers 95.66% accurate farmer alerts."* | Engineering Challenges, Honest Academic Transparency. |
| **10** | **0.5 min** | Team Lead | *"Our complete code, evaluation logs, and presentation artifacts are available on GitHub at `github.com/kaushalrog/AG-DATA`. Thank you Dr. Sreeja. We welcome your questions."* | Open-Source Defense, Reproducibility. |

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
docker exec -it agri-namenode hdfs fsck /agri/processed/canonical -files -blocks -locations
```
*What to point out:* Highlight **"Live datanodes (3)"** and **"Block replication: 3"** in the output.

---

### Command 2: Launch Spark in Local Mode on All 10 Laptop Cores
Show how to start an interactive Spark session leveraging your 10 Apple Silicon cores:
```bash
/opt/miniconda3/bin/spark-shell \
  --master "local[*]" \
  --driver-memory 4g \
  --conf "spark.sql.shuffle.partitions=200" \
  --conf "spark.driver.host=127.0.0.1" \
  --conf "spark.driver.extraJavaOptions=--add-opens=java.base/java.lang=ALL-UNNAMED --add-opens=java.base/java.util=ALL-UNNAMED --add-opens=java.base/sun.util.calendar=ALL-UNNAMED"
```
*What to explain:*
- `--master local[*]`: Automatically detects 10 CPU cores and spawns 10 worker execution threads inside the JVM.
- `--driver-memory 4g`: Allocates 4 GB heap memory to the driver.
- `--conf spark.sql.shuffle.partitions=200`: Configures 200 partitions for wide transformations.
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

### Command 4: Launch the Streamlit Analytics Dashboard
In a separate terminal tab:
```bash
streamlit run src/dashboard/app.py --server.port 8501
```
Open **`http://localhost:8501`** in your browser.  
*What to show:* Show the mandi price trend charts, the geospatial volatility heatmap, and the live anomaly alert cards (SELL / HOLD / WATCH / BUY).

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
1. **Input File Partitions:** When reading Parquet or CSV, partitions are determined by file size divided by `spark.sql.files.maxPartitionBytes` (default 128 MiB). For our 26 annual CSVs, Spark initially creates 26 to 52 partitions.
2. **Shuffle Partitions (`spark.sql.shuffle.partitions`):** When a wide transformation occurs (`Window.partitionBy`, `groupBy`, `join`), Spark redistributes data into **200 partitions** (or the configured partition count).
3. **Partition Sizing Trade-Off:**
   - *Too Few Partitions:* Data per partition exceeds RAM, causing **Spill to Disk** or OOM crashes.
   - *Too Many Partitions:* Small task scheduling overhead dominates execution time.

---

### D. Mathematical Proof of 10 CPU Core Wave Execution
Dr. Sreeja will ask: *"How exactly did your laptop CPU cores execute these tasks?"*

1. **Hardware Profile:** Apple Silicon Mac with **10 physical CPU cores** (`sysctl -n hw.ncpu` = 10).
2. **Worker Threads:** `--master local[*]` allocates **10 concurrent worker threads** inside the single JVM.
3. **Task Wave Calculation:**
   - In Stage 1 (Window Aggregation), Spark sets `spark.sql.shuffle.partitions = 200`.
   - Spark creates **200 Tasks**.
   - Your 10 CPU cores execute **exactly 10 tasks in parallel**:
     $$\text{Task Execution Waves} = \frac{200 \text{ Tasks}}{10 \text{ CPU Cores}} = 20 \text{ Successive Waves}$$
4. **Proving This in the Spark UI:**
   - Click on the **"Executors"** tab in `http://localhost:4040`.
   - In the **"driver"** row, point to **Cores: 10** and **Active Tasks: 10**.

---

### E. DAG Performance Factors (What to Tell Dr. Sreeja)
Performance in the DAG depends on four critical metrics visible in the Spark UI:
1. **Data Skew (Straggler Tasks):** In the **"Tasks"** summary table, check the Min, Median, and Max task durations. If Min is 100ms but Max is 45s, a single partition has excessive records (e.g., high-volume commodities like Onion/Potato).
2. **Spill (Memory) and Spill (Disk):** If a partition is too large for its execution memory slot, Spark spills records to disk, degrading speed by 10×. In our pipeline, composite key deduplication eliminated all spills (**0 bytes spilled**).
3. **Shuffle Read / Shuffle Write Size:** Measures network and memory transfer across stage boundaries. Keeping shuffle size low reduces GC pressure.
4. **Garbage Collection (GC) Time:** Visible under Task Metrics. If GC time exceeds 10% of total run time, executor heap memory is under pressure.

---

# 🌐 6. PORT & LOCALHOST DIRECTORY

Memorize this exact directory for viva defense:

| Port | Service / Web UI | Operational Role & Viva Explanation |
|:---:|---|---|
| **`http://localhost:9870`** | **HDFS NameNode Web UI** | Shows HDFS cluster health, 3 connected DataNodes, 128 MB block replication status, and volume capacity. |
| **`http://localhost:4040`** | **Spark Application Web UI** | Live Spark monitor showing the DAG visualization, Jobs, Stages, 200 tasks, 10 CPU executor cores, and Tungsten codegen. |
| **`http://localhost:8501`** | **Streamlit Dashboard** | Interactive geospatial decision support app displaying live mandi anomaly heatmaps and SELL/HOLD/WATCH/BUY advisories. |
| **`localhost:9000`** | **HDFS RPC (`fs.defaultFS`)** | Inter-process socket protocol used by Spark to read/write Parquet files to HDFS (`hdfs://localhost:9000/...`). |
| **`localhost:9092`** | **Apache Kafka Broker** | Native event transport broker streaming live micro-batch arrival records into topic `agri-market-real-replay`. |

---

# 💡 7. EXHAUSTIVE VIVA VOCE QUESTIONS & DEFENSE REPOSITORY

### Q1: What is the difference between Hadoop and DAG?
> **Answer:**  
> "Ma'am, **Hadoop** is an entire distributed ecosystem comprising **HDFS** for storage, **MapReduce** for compute, and **YARN** for resource management.  
> A **DAG (Directed Acyclic Graph)** is a mathematical execution model used by Apache Spark. In Hadoop MapReduce, every job was rigidly hardcoded into a 2-stage cycle: Map $\rightarrow$ Shuffle $\rightarrow$ Reduce, writing all intermediate data to physical disk. Spark replaces this with an arbitrary DAG of multi-stage transformations kept entirely in memory, eliminating disk I/O bottlenecks and running up to 100× faster."

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
> 1. **Jobs:** A Job is created every time an **Action** is called. In `DataPipelineMaster`, there are **6 Jobs** triggered by `.count()` and `.write.parquet()` calls.
> 2. **Stages:** Stages are created at **Shuffle Boundaries** caused by wide transformations. In our feature engineering run, Spark's DAGScheduler created **13 distinct Stages**.
> 3. **Tasks:** Each Stage creates tasks equal to the number of partitions in that stage. In our initial file read stage, there are tasks equal to the input Parquet blocks; in our Window shuffle stages, there are exactly **200 Tasks** because `spark.sql.shuffle.partitions = 200`. Our 10 CPU cores execute these 200 tasks in 20 parallel waves."

---

### Q6: How many Actions are in this code?
> **Answer:**  
> "Ma'am, in Spark, transformations are lazy and only actions trigger physical computation. Across our main pipeline modules, we invoke the following actions:
> 1. `.count()`: Called during data quality auditing to verify record counts.
> 2. `.write.mode("overwrite").partitionBy("year").parquet(...)`: Called to serialize deduplicated and canonical datasets to HDFS.
> 3. `pipeline.fit(trainDF)`: Called in MLlib to train the Random Forest Classifier.
> 4. `model.transform(testDF)` followed by `.write.parquet(...)`: Called to evaluate test data and persist prediction scores.
> 5. `.start()`: Called on `statefulStream.writeStream` to initiate Structured Streaming."

---

### Q7: Are you using the DataFrame or Dataset API, and why?
> **Answer:**  
> "In Scala, a `DataFrame` is an alias for an untyped `Dataset[Row]`. We use both strategically:
> 1. We use **DataFrames** for our large-scale batch ingestion, deduplication, and windowing because DataFrames leverage Spark's **Catalyst Optimizer** for physical execution planning and the **Tungsten Engine** for off-heap binary memory management (`UnsafeRow`) and whole-stage Java bytecode generation.
> 2. We use strongly-typed **Datasets (`Dataset[MarketEntity]`)** in our real-time streaming pipeline (`Phase10StructuredStreamingReal.scala`) because `flatMapGroupsWithState` requires compile-time type safety and custom serialization across state updates."

---

### Q8: What are Higher-Order Functions, and where did you use them?
> **Answer:**  
> "A **Higher-Order Function** is a functional programming concept in Scala where a function either takes another function as an argument or returns a function.  
> In our project, we used higher-order functions in:
> 1. `.map()` and `.filter()`: Passing anonymous lambda functions to filter negative price spreads (`row => row.getAs[Double]("max_price") >= row.getAs[Double]("min_price")`).
> 2. `SparkSetup.timed[T](label)(body: => T)`: Used Call-by-Name parameters to time execution blocks.
> 3. `flatMapGroupsWithState()`: We passed our custom `updateMarketState` function as a parameter to manage stateful rolling window buffers per market entity across Kafka streaming micro-batches."

---

### Q9: Why didn't your team use Hadoop MapReduce?
> **Answer:**  
> "MapReduce is a legacy disk-bound batch paradigm. It forces every computation into a rigid Map $\rightarrow$ Sort $\rightarrow$ Reduce flow, serializing all intermediate data to physical HDFS disks. Executing multi-pass 7-day rolling window aggregations and iterative Random Forest tree training across 133 million rows in MapReduce would require dozens of sequential disk read/write cycles, taking many hours. Apache Spark executes multi-stage DAG pipelines in-memory with Catalyst and Tungsten optimizations, running up to **100× faster** than MapReduce."

---

### Q10: What cluster are you using?
> **Answer:**  
> "We use a hybrid distributed architecture:
> 1. **Storage Cluster:** A multi-container **Docker cluster** running **Hadoop HDFS 3.4.1** with 1 NameNode and 3 DataNodes with replication factor 3.
> 2. **Compute Engine:** Apache Spark 4.2.0 executing in `local[*]` mode utilizing all **10 physical CPU cores** of our Apple Silicon host machine as parallel worker threads with 4 GB driver memory.
> We do not falsely claim a physical multi-rack YARN cluster; our setup demonstrates genuine distributed block storage, replication, and multi-core parallel compute."

---

### Q11: How do you prove your model did not just memorize the majority class?
> **Answer:**  
> "Ma'am, in our dataset, normal transactions represent 84.35% and anomalies represent 15.65%. A naive 'All-Normal' baseline model that simply predicts 0 for every transaction achieves 84.35% accuracy, but its **Recall is 0.00%** and **Precision is 0.00%**.  
> Our tuned Random Forest production model achieves **95.66% accuracy, 86.55% precision, 85.47% recall, and an 86.01% F1-score** on 48,354 completely unseen test records from 2025+. Because both Precision and Recall exceed 85%, the model genuinely captures anomalies while keeping false alarms strictly at 2.46%."

---

### Q12: Did you mix real data and synthetic data during machine learning?
> **Answer:**  
> "No, Ma'am. All feature engineering, model training, validation, and testing strictly used the **93.41 million real canonical agricultural records**.  
> The 350 million synthetic records were generated in Phase 11 solely to test HDFS block allocation, storage scalability, and shuffle performance under extreme scale to satisfy the course's ~18 GB scale requirement. Real data and synthetic data are stored in completely separate HDFS paths and were never mixed into ML training."

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
> "Data skew occurs when one partition contains disproportionately more records than others, causing 9 out of 10 CPU cores to finish in seconds while the 10th core runs for minutes (the straggler task). In agricultural data, high-volume commodities like Onion and Potato in Maharashtra create massive skew.  
> We handled data skew using three techniques:
> 1. Enabled **Adaptive Query Execution (AQE)** in `SparkSetup.scala` (`spark.sql.adaptive.skewJoin.enabled = true`), which dynamically splits large shuffle partitions at runtime.
> 2. Used a **7-column composite key** (`state`, `district`, `market`, `commodity`, `variety`, `date`) rather than grouping by commodity alone, distributing rows evenly across hash buckets.
> 3. Tuned `spark.memory.fraction = 0.6` to allow graceful spilling to disk rather than crashing with out-of-memory errors."

---

### 🏁 Summary Checklist Before Walking Into the Viva
- [x] Docker HDFS is running with 3 DataNodes (`docker exec -it agri-namenode hdfs dfsadmin -report`).
- [x] Spark can launch in local mode on 10 cores (`spark-shell --master "local[*]" ...`).
- [x] Spark UI opens at `http://localhost:4040` during execution.
- [x] HDFS UI opens at `http://localhost:9870`.
- [x] Streamlit dashboard is ready to launch on `http://localhost:8501`.
- [x] Slide deck (`Big_Data_Analytics_Final_Presentation.pptx` or `.pdf`) is open.
- [x] All 15 viva answers memorized and rehearsed!
