# Real-Time Agricultural Market Anomaly Detection and Price Forecasting at Large Scale

A distributed Big Data system that processes **132.9 million** Indian agricultural
market records to detect unusual commodity price behaviour and forecast future
prices, built on **Scala + Apache Spark + Hadoop HDFS + Apache Kafka**.

**School of AI** · Faculty: **Dr. Sreeja**

| Team member | Roll number |
|---|---|
| C Rishitha | CB.AI.U4AID24109 |
| Karthikeya Y | CB.AI.U4AID24163 |
| Ashwin Tyagi | CB.AI.U4AID24167 |
| Kaushal S | CB.AI.U4AID24168 |

> **Every number in this README was produced by running the code in this
> repository.** Nothing is estimated, and unfinished work is marked as such in
> the [status table](#project-status). Detailed run logs and per-stage
> statistics live in [`PROJECT_STATUS.md`](PROJECT_STATUS.md) and `results/`.

---

## 1. Problem statement

Indian agricultural commodity prices are reported daily from thousands of
*mandis* (regulated market yards). A price that suddenly departs from its own
recent history may signal a supply shock, a hoarding episode, a transport
failure, or simply a mis-keyed report — and telling these apart matters to
farmers deciding when to sell and to agencies deciding when to intervene.

Doing this at national scale is a **Big Data** problem, not a modelling
problem:

- **Volume** — 132.9M records across 25 years; ~10.9 GB of raw CSV, scaled to a
  ~18 GB experimental workload.
- **Velocity** — prices arrive continuously from thousands of markets.
- **Variety** — two independent sources with different schemas, different date
  formats, and different fields.
- **Veracity** — 2.4% of records carry data-quality defects that look like
  price anomalies but are not.
- **Value** — forecasting and anomaly detection that a market participant could
  act on.

## 2. Motivation

A single machine using Pandas cannot hold, let alone repeatedly join and window,
132.9M records — the original exploration in this project hit a
`java.lang.OutOfMemoryError` on a naive whole-row `distinct()` over just 5.8M of
them. The pipeline therefore has to be genuinely distributed: partitioned
storage, shuffle-aware aggregation, and streaming inference.

## 3. Objectives

1. Ingest and validate two large agricultural datasets with conflicting schemas.
2. Store raw and processed data on **HDFS** with real replication.
3. Implement the entire pipeline in **Scala/Spark** — cleaning, feature
   engineering, modelling, inference.
4. Separate **data-quality anomalies** from genuine **market anomalies**.
5. Forecast next-day modal price per commodity–market series.
6. Stream simulated market events through **Kafka** into **Spark Structured
   Streaming** for real-time inference.
7. Demonstrate and *measure* scalability at ~18 GB.

---

## 4. Datasets

Both are real, downloaded agricultural market datasets. They are **not**
included in this repository (~10.9 GB); see [Getting the data](#82-get-the-data).

### 4.1 Source 1 — Daily Market Prices (2001–2026)

26 CSV files, one per year.

```
State, District, Market, Commodity, Variety, Grade,
Arrival_Date, Min_Price, Max_Price, Modal_Price, Commodity_Code
```

### 4.2 Source 2 — India Mandi

325 CSV files, **one per commodity** — the commodity is the *filename*, not a
column.

```
State Name, District Name, Market Name, Variety, Group,
Arrivals (Tonnes), Min/Max/Modal Price (Rs./Quintal), Reported Date
```

Its distinguishing feature is **`Arrivals`** — the quantity reaching the market,
absent from Source 1 and a genuine forecasting signal (supply volume moves
price).

### 4.3 Verified scale

Measured by running `ProfileDatasets` over the complete datasets:

| | Records | CSV on disk | Date coverage (derived from data) |
|---|---:|---:|---|
| Daily Market Prices | 75,984,017 | 6.5 GB | 2001-01-10 … 2026-04-21 |
| India Mandi | 56,879,072 | 4.4 GB | 2000-10-19 … 2024-02-02 |
| **Combined** | **132,863,089** | **10.9 GB** | 2000-10-19 … 2026-04-21 |

> **Note on sizes.** The Daily Market Prices *directory* is 7.1 GB, but 641 MB of
> that is a pre-existing Parquet copy of the same records. The genuine CSV
> source is 6.5 GB. Real distinct source data is therefore **10.9 GB**, not
> 11.5 GB.

> **Filenames are never trusted.** `2025.csv` actually ends on **2025-12-30**,
> and `2026.csv` begins on 2025-12-30. Every date fact in this project is
> derived from the date column itself.

### 4.4 On AGMARKNET

The official AGMARKNET / data.gov.in source was intended as a third input but
was unavailable during development. **No AGMARKNET data is present in this
repository and none is fabricated.** The two datasets above are the real
sources.

---

## 5. Architecture

### 5.1 Batch pipeline

```
   Daily Market Prices (6.5 GB)      India Mandi (4.4 GB)
              |                              |
              +--------------+---------------+
                             |
                    HDFS  /agri/raw/
                             |
                    Scala + Spark  (explicit schemas, no inferSchema)
                             |
                    Data-quality classification
                             |
                    Deduplication (business key)
                             |
                    Per-commodity outlier flagging
                             |
                    Parquet, partitioned by year  ->  HDFS /agri/processed/
                             |
                    Feature engineering (lags, rolling stats, z-scores)
                             |
              +--------------+---------------+
              |                              |
      Price forecasting            Market anomaly detection
              |                              |
              +--------------+---------------+
                             |
                    HDFS /agri/results/  ->  Dashboard
```

### 5.2 Streaming pipeline

```
   Replayed historical records
              |
      Kafka producer (Scala)
              |
      Kafka topic: agri-market-prices   (6 partitions)
              |
      Spark Structured Streaming
              |
      Parse -> validate -> real-time features
              |
      +-------+-------+
      |               |
  Anomaly        Forecast
  inference      inference
      |               |
      +-------+-------+
              |
        Results -> Dashboard
```

Kafka feeds Spark **directly**. HDFS is the persistent storage layer, not a hop
in the streaming path.

---

## 6. Technology stack — and why each is here

| Technology | Role | Why it is genuinely needed |
|---|---|---|
| **Scala 2.13.18** | Primary language | Spark's native language; the DataFrame API is compile-time checked, and UDF-free transformations stay inside Catalyst |
| **Apache Spark 4.2.0** | Distributed engine | 132.9M rows require partitioned, shuffle-aware processing; window functions compute lags/rolling stats across the whole dataset |
| **Spark SQL / DataFrames** | Transformations | Catalyst optimises the plan; column pruning and predicate pushdown on Parquet |
| **Spark Structured Streaming** | Real-time layer | Same DataFrame code path for batch and stream; event-time windows and watermarks |
| **Spark MLlib** | ML layer | Distributed training — the training set does not fit one machine's memory |
| **Hadoop HDFS** | Distributed storage | Block-level distribution + 3× replication; survives DataNode loss |
| **Apache Kafka** | Event transport | Decouples producers from Spark; partitioned log with replayable offsets |
| **Parquet** | Storage format | Columnar + Snappy: **10.9 GB CSV → 1.2 GB Parquet (~9:1)**, with predicate pushdown CSV cannot offer |
| **Docker** | HDFS cluster | Runs a genuine multi-DataNode cluster on one laptop |

**Kafka is not storage. HDFS does not compute. Spark is not a message broker.**
Kafka moves events; HDFS stores blocks; Spark processes.

> No native Hadoop **MapReduce** job is included — it is not a requirement of
> this course, and all batch aggregation is done in Spark. This is a deliberate
> scope decision, not an omission.

---

## 7. Implementation

### 7.1 Data quality vs market anomalies

The single most important distinction in this project:

| | Data-quality anomaly | Market anomaly |
|---|---|---|
| What it says | the *record* is defective | the *market* did something unusual |
| Example | `Min=0, Max=0, Modal=900` — a partial report | modal price jumps 40% above its 7-day mean |
| Handled by | `DataQuality.scala` | anomaly stage (Phase 10) |
| Timing | **first** | only on clean rows |

`Min=0, Max=0, Modal=900` is an incomplete price *report* — the reporter filed
only the modal price. Feeding such rows to an anomaly detector fills the output
with findings that say nothing about agriculture. Quality is resolved first;
only `VALID` rows are eligible for modelling.

Quality classes: `VALID`, `MISSING_DATE`, `MISSING_PRICE`, `ZERO_MIN_MAX`,
`ZERO_MAX`, `NEGATIVE_PRICE`, `MIN_GT_MAX`, `MODAL_OUTSIDE_RANGE`.

### 7.2 Handling messy input

Problems found by inspecting **all 351 source files**, and how each is handled:

| Problem | Scale | Handling |
|---|---|---|
| Quoted fields with embedded commas (`"Sesamum (Sesame,Gingelly,Til)"`) | 5,307 rows in one file alone | RFC-4180 quoting in the CSV reader; never split on commas manually |
| Two header variants in India Mandi | 293 vs 22 files | Explicit schema + `header=true` binds by **position**; column order is identical |
| Two date formats, mixed | 294 `dd MMM yyyy` vs 21 ISO — and the split does **not** match the header split | `coalesce(try_to_date(f1), try_to_date(f2))` per row |
| Empty files | 10 files, 1 byte each | Tolerated by the reader |
| No commodity column in India Mandi | all 325 files | Recovered from `input_file_name()` |
| Inconsistent numeric formatting (`1400` vs `3200.0`) | across years | Explicit schemas — **no `inferSchema` anywhere** |

`try_to_date` rather than `to_date` is essential: under the `CORRECTED` parser
policy `to_date` **throws**, so a plain `coalesce` never reaches the second
format and one bad row kills a multi-GB job.

### 7.3 Deduplication

Business key = `source + state + district + market + commodity + variety + date`
— "this commodity, in this market, on this day".

Whole-row `distinct()` is never used: it shuffles every column of every row and
hashes the full record, which is exactly what caused the original OOM. Grouping
on seven short key columns lets Spark do a map-side partial aggregation.

Duplicates are resolved deterministically — `VALID` beats defective, then widest
known price range, then price columns as tie-break — so runs are reproducible.

### 7.4 Outlier treatment

Verified modal prices span **0.05 … 918,421,086** with mean 3,198.99 and
stddev 152,496.41. These rows pass *every* quality check: min ≤ modal ≤ max, all
positive, dates parse. They are plausible-looking records with implausible
magnitudes.

So bounds are learned **per commodity**, using `percentile_approx` and a
3×IQR (Tukey "far out") band. The learned bounds show why a global threshold
cannot work:

| Commodity | Lower | Upper |
|---|---:|---:|
| Wheat | 1,817 | 3,294 |
| Onion | 0 | 7,890 |
| **Cardamoms** | 0 | **445,000** |

A single cutoff would either miss the onion errors or delete every legitimate
cardamom price.

Commodities with too few observations for stable quartiles fall back to a wide
±10× median band. This matters: Saffron has only 26 valid records, and three
reports of ₹4,000,000 against a median of ₹66,200 are caught by the fallback —
verified, its 23 legitimate rows (58,000–80,100) stay unflagged.

**Outliers are flagged, never deleted.** An extreme price may be an error — or
it may be the very market event this project exists to detect.

---

## 8. Results so far

### 8.1 Preprocessing (executed on the full 132.9M records)

| | Daily Market Prices | India Mandi |
|---|---:|---:|
| Raw records | 75,984,017 | 56,879,072 |
| Duplicates removed | 339,216 | 196,045 |
| **Records written** | **75,644,801** | **56,683,027** |
| `VALID` after cleaning | 73,859,911 | 54,728,238 |
| Price outliers flagged | 501,432 (0.66%) | 382,538 (0.67%) |
| Undated rows quarantined | 0 | 0 |
| Learn-bounds time | 141.84 s | 154.47 s |
| Parquet write time | 214.46 s | 258.22 s |
| Year partitions | 26 | 25 |

Total written: **132,327,828 records**, 535,261 duplicates removed.
Verified: **0** business keys remain duplicated in the output.

### 8.2 Storage

| | CSV | Parquet (Snappy) | Ratio |
|---|---:|---:|---:|
| Daily Market Prices | 6.5 GB | 672 MB | 9.9 : 1 |
| India Mandi | 4.4 GB | 574 MB | 7.8 : 1 |
| **Total** | **10.9 GB** | **1.2 GB** | **~9 : 1** |

### 8.3 Measured throughput

Profiling 75,984,017 records — read, parse, quality-classify, aggregate —
completed in **80.02 s** on 10 local cores ≈ **950,000 records/s**. The
duplicate scan that previously caused an OOM now completes in **54.48 s**.

*(Full scalability sweeps at 5/10/18 GB are Phase 12 — not yet run, and no
numbers are claimed for them.)*

---

## 9. Data provenance and the ~18 GB workload

The faculty requirement is a ~18 GB workload; the real data is 10.9 GB.

```
Real source data (CSV)          ≈ 10.9 GB   data_source = "real"
Synthetic scaled workload       ≈  7.1 GB   data_source = "synthetic_scaled"
                                  --------
Experimental workload           ≈ 18.0 GB
```

Every row in the canonical schema carries a `data_source` column, populated from
ingestion onward. **Synthetic rows are never presented as government data.**
They are generated from the statistical and categorical distributions of the
real data (commodities, states, markets, price ranges, seasonality) — not by
duplicating rows.

The synthetic workload exists for **scalability evaluation only**: HDFS storage,
partitioning, shuffle behaviour, throughput. No forecasting or anomaly result is
reported from synthetic data.

Kafka replay is a **separate** concern: it demonstrates *velocity* by replaying
historical records as a simulated live stream. It is clearly labelled as a
**simulated/replayed stream**, not a live government feed, and it does not
contribute to the dataset size claim.

---

## 10. Project status

| Phase | Component | Status |
|---|---|---|
| 1–3 | Repository + data inspection, `PROJECT_STATUS.md` | ✅ done |
| 4 | Scala/Spark profiling of both datasets | ✅ **executed, verified** |
| 5–6 | Preprocessing → partitioned Parquet | ✅ **executed on all 132.9M records** |
| 7 | HDFS deployment (Docker, 3 DataNodes) | 🔧 compose + scripts written, **not yet brought up** |
| 7 | Kafka install | ✅ installed natively |
| 8 | Feature engineering | ⬜ next |
| 9 | Price forecasting | ⬜ |
| 10 | Market anomaly detection | ⬜ |
| 11 | Synthetic scaling to ~18 GB | ⬜ |
| 12 | Scalability experiments | ⬜ |
| 13–16 | Kafka producer + Structured Streaming | ⬜ |
| 17 | Dashboard | ⬜ |

---

## 11. Repository layout

```
Agricultural_BigData_Project/
├── build.sbt                   Scala 2.13.18 / Spark 4.2.0, pinned
├── project/
├── src/main/scala/com/agribigdata/
│   ├── ingestion/              Schemas.scala, Readers.scala
│   ├── preprocessing/          DataQuality, Deduplicate,
│   │                           OutlierTreatment, PreprocessDatasets
│   ├── profiling/              ProfileDatasets.scala
│   ├── features/               (Phase 8)
│   ├── forecasting/            (Phase 9)
│   ├── anomaly/                (Phase 10)
│   ├── streaming/              (Phase 13-16)
│   └── utils/                  SparkSetup.scala
├── docker/                     HDFS cluster (1 NameNode + 3 DataNodes)
├── scripts/                    env.sh, hdfs_setup.sh, kafka_setup.sh
├── results/                    profiling/ and preprocessing/ statistics
├── data/                       (git-ignored)
├── PROJECT_STATUS.md           detailed verified state
└── README.md
```

---

## 12. How to run

### 12.1 Prerequisites

Verified on an Apple Silicon MacBook Air (10 cores, 16 GB RAM):

| Component | Version |
|---|---|
| Apache Spark | 4.2.0 |
| Scala | 2.13.18 |
| Java | **21** (OpenJDK 21.0.12) |
| sbt | 1.11.7 |
| Kafka | via Homebrew (KRaft) |
| Docker | for the HDFS cluster |

```bash
brew install apache-spark sbt kafka
brew install openjdk@21
```

> **Java 21 matters.** Spark 4.2.0 is built against Java 21. If a newer JDK is
> first on `PATH`, `scripts/env.sh` pins the forked JVM to 21 — without it,
> Spark fails on JDK-internal access.

### 12.2 Get the data

Place the datasets as:

```
data/raw/Daily_Market_Prices_2001_2026/csv/*.csv
data/raw/india_mandi/*.csv
```

Raw data is never modified by the pipeline.

### 12.3 Run the pipeline

```bash
source scripts/env.sh
```

Profile both datasets:

```bash
sbt 'runMain com.agribigdata.profiling.ProfileDatasets'
```

Test on a single year first (recommended — ~1 minute):

```bash
sbt 'runMain com.agribigdata.preprocessing.PreprocessDatasets --source daily --years 2025 --out data/processed_test'
```

Full preprocessing (~13 minutes for 132.9M records):

```bash
AGRI_SHUFFLE_PARTITIONS=200 sbt 'runMain com.agribigdata.preprocessing.PreprocessDatasets'
```

### 12.4 HDFS

```bash
./scripts/hdfs_setup.sh up
```

Then `load`, `report`, `down`. NameNode UI: <http://localhost:9870>.

### 12.5 Kafka

```bash
./scripts/kafka_setup.sh up
```

Then `status`, `tail`, `down`.

---

## 13. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `EXPRESSION_DECODING_FAILED` / `IllegalAccessException: sun.util.calendar.ZoneInfo` | JDK module system blocks Spark's date conversion | already handled by `--add-opens` in `build.sbt` |
| `CANNOT_PARSE_TIMESTAMP` | `to_date` throws under `CORRECTED` policy | use `try_to_date` |
| `OutOfMemoryError: Java heap space` | whole-row `distinct()` / `collect()` | group on the business key; never collect large results |
| `hostname resolves to a loopback address` | local network config | `SPARK_LOCAL_IP=127.0.0.1` (set by `env.sh`) |
| Docker commands fail | daemon not running | start Docker Desktop first |
| Spark runs on the wrong Java | newer JDK first on `PATH` | `source scripts/env.sh` |

---

## 14. Limitations

Stated honestly, because they are the questions a viva will ask:

1. **Single machine.** Spark runs `local[*]`. Parallelism is real (10 cores,
   partitioned data) but there is no network shuffle between physical nodes.
2. **Kafka replication factor is 1** — one broker on one laptop. HDFS
   replication (3×) *is* genuinely demonstrated. This asymmetry is deliberate:
   container memory was given to HDFS.
3. **Streaming is replayed, not live.** No live government feed was available.
4. **The ~18 GB workload is 10.9 GB real + ~7.1 GB synthetic**, and the two are
   always distinguishable via `data_source`.
5. **The two sources are not joined on price.** Source 2 states `Rs./Quintal`;
   Source 1 carries no unit metadata. Until that is verified empirically,
   India Mandi is a *supporting* source, not a merged one.
6. **India Mandi ends 2024-02-02**, so it cannot supply `Arrivals` features for
   the 2025/26 records used in testing and streaming.
7. **AGMARKNET data is absent**, not substituted.

---

## 15. License / academic use

Coursework for the School of AI. The agricultural datasets belong to their
respective publishers.
