# Big Data Analytics Final Project Review & Defense Master Guide
### Agricultural Commodity Price Forecasting and Farmer Decision Support System

This directory contains the presentation deliverables, slide decks, and defense guides formatted strictly according to the **Big Data Analytics Final Review 10-Slide Structure** for evaluator **Dr. Sreeja** (School of Artificial Intelligence, Amrita Vishwa Vidyapeetham).

> 📌 **Comprehensive Syllabus & Viva Guide:** For an exhaustive, pin-to-pin mapping of the entire project to Units 1 to 4 of the Big Data Analytics syllabus, see:  
> 👉 [**`docs/PROJECT_MASTER_SYLLABUS_AND_VIVA_GUIDE.md`**](file:///Users/kaush/Downloads/Agricultural_BigData_Project/docs/PROJECT_MASTER_SYLLABUS_AND_VIVA_GUIDE.md)

---

## 1. Presentation Deliverables & File Locations

| File | Purpose | Format |
|---|---|---|
| [**`Big_Data_Analytics_Final_Presentation.pptx`**](file:///Users/kaush/Downloads/Agricultural_BigData_Project/docs/presentation/Big_Data_Analytics_Final_Presentation.pptx) | **Primary PowerPoint Presentation** (16:9 widescreen, custom forest-dark palette, complete speaker notes on every slide) | PPTX |
| [**`Big_Data_Analytics_Final_Presentation.pdf`**](file:///Users/kaush/Downloads/Agricultural_BigData_Project/docs/presentation/Big_Data_Analytics_Final_Presentation.pdf) | **Vector PDF Presentation** for projection, distribution, or submission | PDF |
| [**`PROJECT_MASTER_SYLLABUS_AND_VIVA_GUIDE.md`**](file:///Users/kaush/Downloads/Agricultural_BigData_Project/docs/PROJECT_MASTER_SYLLABUS_AND_VIVA_GUIDE.md) | **Exhaustive Viva & Syllabus Master Guide** (Units 1–4, DAG analysis, 10 CPU cores, viva Q&A) | Markdown |
| [`generate_deck.py`](file:///Users/kaush/Downloads/Agricultural_BigData_Project/docs/presentation/generate_deck.py) | **Executable Source Script** regenerating the PPTX, PDF, PNG slide previews, and montage | Python (`python-pptx`, PIL) |
| [`AG-DATA-presentation.tex`](file:///Users/kaush/Downloads/Agricultural_BigData_Project/docs/presentation/AG-DATA-presentation.tex) | **LaTeX Beamer Source** (Overleaf-ready, compiles with `pdfLaTeX`) | TeX |
| [`preview/slides_montage.png`](file:///Users/kaush/Downloads/Agricultural_BigData_Project/docs/presentation/preview/slides_montage.png) | **10-Slide High-Resolution Overview Montage** | PNG |
| `preview/slide-01.png` ... `slide-10.png` | **Individual High-Resolution Slide Previews** | PNG |

---

## 2. Pin-to-Pin Syllabus Mapping (Units 1 to 4)

| Syllabus Unit | Core Academic Topics | Implementation in AG-DATA Project |
|---|---|---|
| **Unit 1: Big Data & Hadoop** | 5 Vs of Big Data, State-of-the-Art Platforms, Hadoop HDFS, Mapper/Reducer | 132.86M rows (Volume), Kafka stream (Velocity), 2 CSV schemas (Variety), 535k dedup (Veracity), Farmer distress prevention (Value). 4-container HDFS in Docker with replication 3 and 128 MB blocks. Map-side partial combine and reduce-side window grouping. |
| **Unit 2: Functional Programming in Scala** | Immutability, Type Hierarchy, Higher-Order Functions, Closures, Concurrency | Strict use of `val` over `var`; `case class MarketEntity` extending `AnyRef`; higher-order functions (`.map(col)`, `SparkSetup.timed`, `flatMapGroupsWithState`); driver-to-worker closure serialization; 10 CPU execution threads via `local[*]`. |
| **Unit 3: Spark Architecture & DAG** | RDDs vs DataFrames vs Datasets, Transformations & Actions, Catalyst, Tungsten, DAG | Untyped `DataFrame` for Catalyst optimization and Tungsten off-heap binary memory (`UnsafeRow`); typed `Dataset[T]` for stateful streaming; lazy evaluation (lineage); narrow vs wide transformations; shuffle boundaries dividing DAG into 13 Stages. |
| **Unit 4: Spark MLlib & Case Study** | MLlib Pipeline, Random Forest, Class Imbalance, Temporal Split, Commodity Case Study | Spark `Pipeline` chaining `Imputer`, `VectorAssembler` (9 price features), and `RandomForestClassifier` (100 trees, depth 14). Strict temporal split (<2024 train, 2024 val, 2025+ test, 95.66% accuracy). Agribusiness decision support (SELL/HOLD/WATCH/BUY). |

---

## 3. Strict 10-Slide Rubric Alignment & Presenter Script

**Target Duration:** 15 Minutes Presentation + 10 Minutes Viva Voce

| Slide | Faculty Rubric Requirement | Time | Presenter Script & Key Technical Focus |
|:---:|---|:---:|---|
| **1** | Title, Team Members, Register Numbers, Faculty Name | 1.0 min | *"Good morning Dr. Sreeja. Our project is Agricultural Commodity Price Forecasting and Farmer Decision Support System using Hadoop HDFS and Apache Spark. Our team members are Rishitha, Karthikeya, Ashwin, and Kaushal. We built an end-to-end Big Data pipeline processing 132.86M real market records."* |
| **2** | Problem Statement, Objectives, Why Big Data is Needed | 1.5 min | *"Farmers face 40%+ price crashes during harvest gluts, forcing distress selling. Single-node Pandas crashes with OutOfMemory on 11 GB CSVs when computing multi-year rolling windows. We solve this using distributed storage in HDFS and in-memory parallel compute in Spark, generating actionable SELL, HOLD, WATCH, and BUY advisories."* |
| **3** | Dataset Specifications, Scale & Attributes | 1.5 min | *"We ingested 132.86M raw records from Agmarknet. We purged 535,261 duplicate transactions using a composite window key to produce 132.32M deduplicated rows, compressed to 1.2 GB Snappy Parquet (9:1 ratio). Our quality canonical layer contains 93.41M verified records. All ML models strictly train on this real data. An isolated 350M synthetic dataset in Phase 11 tested 18 GB HDFS scalability."* |
| **4** | System Architecture Diagram | 2.0 min | *"Our system architecture is dual-path: a batch path for data engineering and model training, and a streaming path via Kafka and Structured Streaming. HDFS runs 1 NameNode and 3 DataNodes in Docker with replication factor 3. Spark executes on host CPU cores in `local[*]` mode. HDFS DataNodes store blocks; they do not execute Spark tasks."* |
| **5** | Spark Workflow, DataFrames, DAG, Partitioning & Caching | 2.5 min | *"We use DataFrames rather than RDDs to exploit Catalyst optimization (predicate pushdown, projection pruning) and Tungsten off-heap binary memory with whole-stage code generation. Transformations are lazy; actions compile the DAG into physical Stages at shuffle boundaries. In our feature pipeline, `Window.partitionBy` creates a ShuffleExchange, dividing the DAG into 13 Stages across 200 shuffle partitions."* |
| **6** | Scala Implementation & Core Code Snippets | 2.0 min | *"In Scala, we avoid crashes by wrapping multi-format date strings in `coalesce(try_to_date(...))`. Instead of a driver-crashing `distinct()`, our composite window deduplication executes map-side sorting in 4.2 minutes with zero disk spills. In streaming, `flatMapGroupsWithState` maintains a 7-observation buffer per `MarketEntity` across irregular arrival intervals."* |
| **7** | Spark MLlib Pipeline, Features & Tuning | 1.5 min | *"We engineer 9 price features including 7-day rolling mean, stddev, and z-score. To prevent data leakage, we enforce a strict chronological split: training on pre-2024 data (721k rows), tuning depth and threshold on 2024 validation data, and testing on untouched 2025+ records (48k rows). We differentiate Task 1 (Next-Day Forecasting) from Task 2 (Real-Time Screening)."* |
| **8** | Results, Metrics Table, Confusion Matrix & Business Insight | 2.0 min | *"On 48,354 unseen 2025+ test records, our tuned Random Forest production model achieves 95.66% accuracy, 86.55% precision, 85.47% recall, and an 86.01% F1-score with an ultra-low 2.46% false alarm rate. An All-Normal model gets 84.35% accuracy but 0% recall. Kafka replay validated 1,200 events/sec throughput with sub-800ms latency."* |
| **9** | Challenges, Limitations, Conclusion & Future Work | 1.0 min | *"We solved JDK 21 reflection using `--add-opens`, date crashes via coalesce, and shuffle OOM via composite dedup. We honestly report that Spark runs in `local[*]` mode rather than multi-node YARN, and automated SMS dispatch is future work. In conclusion, the system processes 132.9M real rows and delivers 95.66% accurate alerts."* |
| **10** | References, GitHub Repository & Deliverables | 0.5 min | *"Our project evidence, logs, and code are open-source on GitHub at `github.com/kaushalrog/AG-DATA`. Thank you Dr. Sreeja. We are now open for viva questions."* |

---

## 4. Live Demo Commands for Dr. Sreeja

```bash
# 1. Show 3 live HDFS DataNodes and replication factor 3
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
docker exec -it agri-namenode hdfs dfsadmin -report
docker exec -it agri-namenode hdfs fsck /agri/processed/canonical -files -blocks -locations

# 2. Launch interactive Spark shell on all 10 Apple Silicon CPU cores
/opt/miniconda3/bin/spark-shell \
  --master "local[*]" \
  --driver-memory 4g \
  --conf "spark.sql.shuffle.partitions=200" \
  --conf "spark.driver.host=127.0.0.1" \
  --conf "spark.driver.extraJavaOptions=--add-opens=java.base/java.lang=ALL-UNNAMED --add-opens=java.base/java.util=ALL-UNNAMED --add-opens=java.base/sun.util.calendar=ALL-UNNAMED"

# 3. Launch the Streamlit Analytics Dashboard
streamlit run src/dashboard/app.py --server.port 8501
```

---

## 5. Spark Web UI, DAG, Partitions & CPU Cores (Viva Answers)

- **How to Open Spark UI:** Open `http://localhost:4040` in your web browser while Spark is running.
- **DAG Breakdown in UI:**
  - **Blue Outer Boxes:** Represent **Stages**. A new stage begins whenever a wide transformation (ShuffleExchange) occurs.
  - **Inner Nodes:** Represent RDDs/Operations (`Scan parquet`, `Filter`, `Project`, `Exchange`, `WholeStageCodegen`).
  - **`Exchange` Node:** Indicates a network/memory shuffle where data was hashed and redistributed across partitions.
  - **`WholeStageCodegen` Box:** Represents the **Tungsten Engine**, compiling multiple operations into a single optimized Java loop.
- **Partitions:**
  - File input partitions: Based on 128 MB block size.
  - Shuffle partitions: Default 200 partitions (`spark.sql.shuffle.partitions = 200`).
- **How Laptop CPU Cores Are Used:**
  - Apple Silicon Mac with **10 CPU cores** (`Runtime.getRuntime.availableProcessors()` = 10).
  - Spark spawns **10 parallel worker execution threads** inside the JVM.
  - When a stage has 200 tasks, the 10 cores process them in **20 successive waves of 10 tasks in parallel**:
    $$\text{Waves} = \frac{200 \text{ Tasks}}{10 \text{ Cores}} = 20 \text{ Parallel Batches}$$
  - Visible in Spark UI under the **"Executors"** tab $\rightarrow$ "driver" row shows **Cores: 10** and **Active Tasks: 10**.

---

## 6. Port & Localhost Directory

| Port | Service / Web UI | Operational Role |
|:---:|---|---|
| **`http://localhost:9870`** | **HDFS NameNode Web UI** | Cluster health, 3 DataNodes, 128 MB block replication status. |
| **`http://localhost:4040`** | **Spark Application Web UI** | Live Spark jobs, DAG visualization, stages, tasks, 10 CPU executor cores, Tungsten codegen. |
| **`http://localhost:8501`** | **Streamlit Dashboard** | Real-time geospatial mandi map, commodity price trends, live anomaly alerts. |
| **`localhost:9000`** | **HDFS RPC (`fs.defaultFS`)** | Inter-process socket protocol used by Spark to read/write Parquet files to HDFS. |
| **`localhost:9092`** | **Apache Kafka Broker** | Native event transport broker streaming live micro-batches into topic `agri-market-real-replay`. |

---

## 7. Direct Viva Voce Q&A Cheat Sheet

- **Diff b/w Hadoop and DAG:** Hadoop MapReduce is a rigid 2-stage (Map $\rightarrow$ Reduce) disk-bound model writing intermediate results to HDFS disks. DAG is an arbitrary directed acyclic graph of multi-stage transformations kept entirely in memory by Spark, running up to 100× faster.
- **How many Jobs in this code:** Each Action triggers exactly 1 Job. In `DataPipelineMaster`, there are 6 distinct Jobs corresponding to validation counts and Parquet writes. In `Phase9FinalTestEval`, 7 Jobs are created.
- **How many Stages in this code:** Stages are delimited by shuffle boundaries (wide transformations). In our feature engineering run, there are 13 distinct Stages.
- **How many Tasks in this code:** Tasks = $\sum (\text{Partitions in Stage } i)$. In shuffle stages, there are 200 tasks (1 per partition).
- **How you find Stages or Tasks:** Stage boundary = ShuffleExchange (Wide Transformation). Task count = partition count of that stage (verified in Spark UI under Stages tab).
- **Diff b/w Wide and Narrow Transformations:**
  - Narrow: 1-to-1 partition mapping (`filter`, `select`, `withColumn`), no shuffle, executed in single stage.
  - Wide: M-to-N partition mapping (`Window.partitionBy`, `groupByKey`, `distinct`), requires shuffle exchange across memory/network, forces new stage.
- **How many Actions in this code:** `.count()`, `.write.parquet()`, `.show()`, `.collect()`, `pipeline.fit()`, `model.transform().write()`, `writeStream.start()`.
- **Diff b/w Lineage Graph and DAG:** Lineage Graph is the logical history of transformations (blueprint for fault tolerance). DAG is the physical execution plan created by DAGScheduler breaking lineage into stages and tasks.
- **What cluster you are using:** Single-node Spark in `local[*]` mode with 10 CPU worker execution threads on Apple Silicon Mac, interacting with a 4-container Dockerized Hadoop HDFS cluster (1 NameNode + 3 DataNodes, replication 3).
- **DataFrame vs Dataset API:** DataFrames (`Dataset[Row]`) leverage Catalyst optimizer and Tungsten off-heap binary memory (`UnsafeRow`) for fast batch ETL. Strongly-typed Datasets (`Dataset[MarketEntity]`) are used in Structured Streaming (`flatMapGroupsWithState`) for compile-time type safety.
- **What is an RDD:** Resilient Distributed Dataset. Fault-tolerant (recomputable via lineage), partitioned across CPU cores/nodes, immutable collection of JVM objects.
- **Higher-Order Functions:** Functions taking functions as arguments or returning functions: `.map(col)`, `SparkSetup.timed[T](label)(body: => T)`, `flatMapGroupsWithState(updateMarketState)`.
