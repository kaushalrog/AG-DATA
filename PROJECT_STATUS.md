# PROJECT STATUS

**Real-Time Agricultural Market Anomaly Detection and Price Forecasting at Large Scale**

School of AI · Faculty: Dr. Sreeja

| Team member | Roll number |
|---|---|
| C Rishitha | CB.AI.U4AID24109 |
| Karthikeya Y | CB.AI.U4AID24163 |
| Ashwin Tyagi | CB.AI.U4AID24167 |
| Kaushal S | CB.AI.U4AID24168 |

Last updated: 2026-08-15

> Every number in this file was produced by running code in this repository.
> Nothing here is estimated or assumed. Where a fact is not yet established,
> it is marked **UNVERIFIED** rather than guessed.

---

## 1. Where the project stood at the start of this session

The repository contained **three files** in total:

```
.DS_Store
data/.DS_Store
scripts/profile_2025.py
```

- No build definition, no Scala source, no version control, no documentation.
- `scripts/profile_2025.py` is a **Pandas** chunked profiler for the 2025 file.
  It is retained for reference but is **not** part of the pipeline: §3 of the
  project brief makes Scala/Spark the mandatory implementation language, and
  Pandas cannot address the full workload on this machine.
- There was **no git repository**. `git status` run from the project directory
  resolved upward to `/Users/kaush`, meaning a `git add .` here would have
  targeted the home directory. A repository has now been initialised locally
  with a `.gitignore` that excludes all of `data/`.

---

## 2. Verified environment

Measured on this machine, not assumed:

| Component | Status | Version / detail |
|---|---|---|
| Apache Spark | ✅ installed | **4.2.0** (`/opt/homebrew/bin/spark-submit`) |
| Scala | ✅ via Spark | **2.13.18** (Spark's bundled compiler) |
| Java (Spark runtime) | ✅ | **OpenJDK 21.0.12** (`openjdk@21`) |
| Java (system default) | ⚠️ mismatch | **26.0.1** is first on `PATH` |
| sbt | ✅ **installed this session** | 1.11.7 |
| Hadoop / HDFS | ❌ **not installed** | `hadoop`, `hdfs` not on PATH |
| Apache Kafka | ❌ **not installed** | no Kafka binaries on PATH |
| Docker | ⚠️ client only | client 29.6.1, compose 5.3.0, **daemon not running** |
| Machine | — | Apple Silicon MacBook Air, **10 cores, 16 GB RAM** |
| Free disk | — | **217 GB** available |

### 2.1 Two environment issues found and resolved

**Java version mismatch.** The system default `java` is 26.0.1, but Spark 4.2.0
is built and tested against Java 21. sbt launches under Java 26, so the forked
JVM would have inherited it. `scripts/env.sh` now pins `AGRI_JAVA_HOME` to
Java 21 and `build.sbt` uses it for `run` and `Test`, so Spark code always
executes on the same JVM `spark-shell` uses. Verified in the run log:
`Executor: Java version 21.0.12`.

**Missing `--add-opens`.** The first profiling run failed with
`EXPRESSION_DECODING_FAILED`, caused by
`IllegalAccessException: sun.util.calendar.ZoneInfo`. Spark's
`DateTimeUtils.toJavaDate` reaches into that JDK-internal class via a
MethodHandle, which the module system blocks on JDK 17+. Any action returning
a date column to the driver hits it. Fixed by adding
`--add-opens=java.base/sun.util.calendar=ALL-UNNAMED` (plus `java.text`,
`java.time`) to the forked JVM options.

**Hostname warning.** The brief notes a loopback-resolution warning. It is
non-fatal, and is now removed by pinning `spark.driver.host` / `SPARK_LOCAL_IP`
to `127.0.0.1`.

---

## 3. Verified dataset state

### 3.1 Actual sizes on disk (`du -sh`)

```
data/raw/Daily_Market_Prices_2001_2026/     7.1 GB   <- as stated in the brief
    ├── csv/                                6.5 GB   <- 26 CSV files, 2001..2026
    └── parquet/                            641 MB   <- pre-existing Parquet copy
data/raw/india_mandi/                       4.4 GB   <- 325 CSV files
                                           -------
TOTAL data/raw                              12 GB
```

**Correction to the brief.** The brief states Daily Market Prices is ~7.1 GB of
source data. That 7.1 GB figure includes a **641 MB Parquet copy of the same
records** that already existed in the directory. The genuine CSV source is
**6.5 GB**, so the real distinct source data is:

> **6.5 GB (CSV) + 4.4 GB (India Mandi) ≈ 10.9 GB**, not 11.5 GB.

The provenance of the pre-existing Parquet copy is unknown; it was not produced
by this pipeline. It is **not** counted as source data and will not be used
until it is verified against the CSVs.

This changes the scaling arithmetic for the ~18 GB target — see §7.

### 3.2 Source 1 — Daily Market Prices (fully profiled by Spark ✅)

All 26 files, 6.5 GB, profiled end to end:

| Metric | Verified value |
|---|---|
| Records (all files) | **75,984,017** |
| Actual date range | **2001-01-10 … 2026-04-21** |
| Unparseable dates | **0** |
| Overview pass runtime | **80.02 s** |
| Duplicate scan runtime | **54.48 s** |

| Class | Records | Share |
|---|---:|---:|
| VALID | 74,197,761 | 97.65% |
| ZERO_MIN_MAX | 1,730,599 | 2.28% |
| ZERO_MAX | 37,670 | 0.05% |
| MODAL_OUTSIDE_RANGE | 17,912 | 0.02% |
| MIN_GT_MAX | 75 | 0.00% |
| **Total** | **75,984,017** | |

- Duplicates: **251,633 repeated business keys, 339,216 surplus rows** (0.45%).
- Cardinality (HLL++): ~33 states, ~639 districts, **~6,804 markets**,
  ~387 commodities, ~1,514 varieties, ~18 grades.
- Nulls do exist at full scale even though 2025 had none: `min_price` 1 row,
  `max_price` 60 rows.
- Records per calendar year rise from 11,603 (2001) to 5,830,699 (2025);
  2026 holds 582,322 (partial, to 22 Apr).

> **Throughput note:** 75.98M records scanned, parsed, quality-classified and
> aggregated in **80 s** on 10 local cores ≈ **950k records/s**. This is a real
> measured baseline for the scalability chapter, not an estimate.

#### Verification against the brief (2025 file only)

Re-running the profiler restricted to `2025.csv` reproduces the brief's
previously recorded figures **exactly**, via a new independent Scala
implementation:

| Metric | Verified value |
|---|---|
| Records (2025.csv) | **5,819,482** |
| Actual date range | **2025-01-01 … 2025-12-30** |
| Unparseable dates | **0** |
| Nulls in any core column | **0** |

| Class | Records | Share |
|---|---:|---:|
| VALID | 5,814,762 | 99.92% |
| ZERO_MIN_MAX | 3,821 | 0.07% |
| ZERO_MAX | 897 | 0.02% |
| MODAL_OUTSIDE_RANGE | 2 | 0.00% |
| **Total** | **5,819,482** | |

These match the figures in the project brief exactly, reached through a new
Scala implementation rather than the earlier ad-hoc session — so the brief's
numbers are now independently confirmed.

**New findings not previously recorded:**

- **Duplicates: 84,935 business keys occur more than once, giving 90,236
  surplus rows (1.55%).** Business key =
  `source + state + district + market + commodity + variety + date`. Found
  without a whole-row `distinct()` — see §5.
- Dimension cardinality (HyperLogLog++, ~2% error): ~29 states, ~570 districts,
  **~5,437 markets**, ~338 commodities, ~879 varieties, ~17 grades.
- Modal price on VALID rows: mean 4478.12, stddev 6548.74, min **0.05**,
  max **4,000,000**. The extremes need review before modelling — a 0.05 modal
  price is not plausible for a quintal of produce, and the spread means raw
  prices are unusable as a model target without per-commodity treatment.
- **Filenames do not determine coverage**, confirmed: `2025.csv` stops at
  **2025-12-30**, while `2026.csv` starts at 2025-12-30 and the dataset ends
  **2026-04-21**. Every date fact in this project is derived from
  `Arrival_Date`.
- **Extreme price outliers exist and must be handled.** Across all years the
  VALID modal price runs 0.05 … **918,421,086**, with mean 3,198.99 and
  stddev **152,496.41**. A standard deviation 48× the mean means the raw price
  distribution is dominated by a small number of extreme values. These pass
  every data-quality check (min ≤ modal ≤ max, all positive) — they are
  *plausible-looking records with implausible magnitudes*, and they are exactly
  what would wreck an unguarded z-score or regression target. Handling will be
  per-commodity, since ₹9×10⁸/quintal is absurd for onions but the correct
  order of magnitude for nothing in this dataset.

**CSV parsing hazard found.** 5,307 rows in `2026.csv` alone contain quoted
fields with embedded commas, e.g. `"Sesamum (Sesame,Gingelly,Til)"`. Naive
comma splitting mis-parses them (a raw `awk -F,` scan of column 7 returned
commodity names where dates should be). The readers use RFC-4180 quoting.

### 3.3 Source 2 — India Mandi (profiled with Spark ✅)

| Metric | Verified value |
|---|---|
| Records | **56,879,072** |
| Actual date range | **2000-10-19 … 2024-02-02** |
| Unparseable dates | **0** (after the date fix in §3.4) |
| Overview pass runtime | 201.88 s |
| Duplicate scan runtime | 30.79 s |

**Data-quality breakdown:**

| Class | Records | Share |
|---|---:|---:|
| VALID | 54,918,727 | 96.55% |
| ZERO_MIN_MAX | 1,464,445 | 2.57% |
| MISSING_PRICE | 465,784 | 0.82% |
| ZERO_MAX | 27,634 | 0.05% |
| MODAL_OUTSIDE_RANGE | 2,481 | 0.00% |
| MIN_GT_MAX | 1 | 0.00% |
| **Total** | **56,879,072** | |

- Duplicates: **136,378 repeated business keys, 196,045 surplus rows** (0.34%).
- Cardinality (HLL++): ~33 states, ~585 districts, ~3,407 markets,
  ~317 commodities, ~1,254 varieties. `grade` is **100% null** — this source
  has no grade column, as expected.
- Modal price on VALID rows: mean 2877.01, stddev 6610.99, min 0.05,
  max **11,600,000**.

**Two findings that reshape the project plan:**

1. **This source is 10× larger in rows than its size suggests.** 4.4 GB holds
   **56.9M records** — nearly ten times the 5.8M rows in the 573 MB 2025 file
   of Source 1. Row count, not gigabytes, drives Spark shuffle cost, so India
   Mandi is the heavier processing workload despite being the smaller dataset
   on disk.

2. **The two sources barely overlap at the recent end.** India Mandi stops at
   **2024-02-02** while Source 1 runs into 2026. So India Mandi cannot supply
   `Arrivals` features for the 2025/2026 records used for testing and the
   streaming demo. It is usable as a supporting/enrichment source for the
   historical period only — which independently supports the brief's §19
   caution against forcing a join.

Also note 2024 has only 346,466 records (a partial year to 02 Feb), so it must
not be treated as a full year in any split or trend.

### 3.4 A parsing bug found and fixed by running the code

The first India Mandi run **failed**, and the failure is worth recording
because it is the kind of thing that only surfaces by executing:

```
SparkDateTimeException: [CANNOT_PARSE_TIMESTAMP]
Text '2005-08-20' could not be parsed at index 2
```

The reader tried `coalesce(to_date(…,"dd MMM yyyy"), to_date(…,"yyyy-MM-dd"))`
to cope with the two date formats. But under the `CORRECTED` time-parser policy
`to_date` **throws** on a non-matching value rather than returning null, so
`coalesce` never reached the second format — the first ISO-formatted row
aborted the whole job. Replaced with `try_to_date`, which returns null and lets
`coalesce` fall through. Source 1's date parse was hardened the same way, so a
single malformed date in 6.5 GB is flagged as `MISSING_DATE` instead of killing
the job. Result after the fix: **0 unparseable dates across all 56.9M rows.**

### 3.5 India Mandi structure (all 325 files inspected)

The source is materially messier than the brief describes:

- **10 files are empty** (1 byte each): `Betelnuts.csv`,
  `Broomstick(Flower Broom).csv`, `Camel Hair.csv`, `Fig(Anjura-Anjeer).csv`,
  `Goat Hair.csv`, `Jaggery.csv`, `Ladies Finger.csv`, `Nargasi.csv`,
  `Saffron.csv`, `Seegu.csv`. **315 files carry data.**

- **Two different header variants exist:**

  | Variant | Files | Header |
  |---|---:|---|
  | A | 293 | `… Arrivals (Tonnes),Min Price (Rs./Quintal),Max Price (Rs./Quintal),Modal Price (Rs./Quintal),Reported Date` |
  | B | 22 | `… Arrivals,Min Price,Max Price,Modal Price,Reported Date` |

  Column **order** is identical in both, so the reader supplies an explicit
  schema with `header=true`; Spark then skips the header line and binds by
  position, handling both variants with no per-file branching.

- **Two different date formats are mixed:** 294 files use `19 Aug 2013`
  (`dd MMM yyyy`), 21 use `2005-08-24` (`yyyy-MM-dd`). **The date split does
  not line up with the header split** (293/22 vs 294/21), so format cannot be
  inferred from the header. The reader `coalesce`s both parse attempts per row.

- **There is no commodity column.** The commodity is the *filename*; the
  `Variety` column holds values like `Tomato` or `Other`. The reader recovers
  the commodity from `input_file_name()` (percent-decoding `%20`).

- This source has **`Arrivals`**, the quantity feature Source 1 lacks.

> **UNVERIFIED — price unit compatibility.** Source 2 states `Rs./Quintal`
> explicitly. Source 1 (`Min_Price`/`Max_Price`/`Modal_Price`) carries **no
> unit metadata**. Per §19 of the brief the two sources will **not** be joined
> on price until this is settled empirically.

---

## 4. What has been implemented and verified

| Component | File | Status |
|---|---|---|
| Build definition (Scala 2.13.18 / Spark 4.2.0) | `build.sbt` | ✅ compiles |
| Pinned toolchain env | `scripts/env.sh` | ✅ verified |
| Spark session factory + timing helper | `utils/SparkSetup.scala` | ✅ runs |
| Explicit source + canonical schemas | `ingestion/Schemas.scala` | ✅ |
| Raw→canonical readers, both sources | `ingestion/Readers.scala` | ✅ Source 1 verified |
| Data-quality classifier + duplicate scan | `preprocessing/DataQuality.scala` | ✅ verified |
| Distributed profiling job | `profiling/ProfileDatasets.scala` | ✅ **executed** |

Reproduce:

```bash
source scripts/env.sh && sbt 'runMain com.agribigdata.profiling.ProfileDatasets --source daily --years 2025'
```

Outputs land in `results/profiling/<dataset>/`.

Measured runtime (2025, 5.8M rows, local[*], 10 cores): overview pass
**21.37 s**, duplicate scan **12.89 s**.

---

## 5. Design decisions already locked in

**No `inferSchema` anywhere.** Inference costs an extra full pass over ~11 GB
and is unstable across files: `2001.csv` writes prices as `1400`, `2025.csv`
writes `3200.0`, so inference can yield Integer for one year and Double for
another, and the union then fails. All schemas are declared.

**Duplicate detection never uses whole-row `distinct()`.** The brief records a
Java heap OOM from `df.distinct().count()` on 5.8M rows: that shuffles every
column of every row and hashes the whole record. Instead, `duplicateStats`
groups on seven short key columns and aggregates, so Spark can do a map-side
partial count and shuffle a small fraction of the bytes. It completed in
**12.89 s** on the same data that previously OOMed.

**Cardinalities use `approx_count_distinct` (HLL++)** rather than exact counts,
trading ~2% error for a few KB of sketch per partition instead of a full
shuffle per column.

**Data quality is resolved strictly before market-anomaly detection**, and the
two are separate concepts throughout the code. `Min=0, Max=0, Modal=900` is an
incomplete price *report*, not a market event; feeding such rows to an anomaly
detector would fill the output with findings that say nothing about agriculture.

**Raw data is never modified.** Readers only rename and derive; cleaning writes
to separate paths.

---

## 6. Known issues / blockers

1. **Hadoop/HDFS not installed.** Blocks Phase 7 and the HDFS layout in §17.
   *Decision taken: HDFS will run in Docker with 2–3 DataNodes so replication
   and DataNode-failure can genuinely be demonstrated.*
2. **Kafka not installed.** Blocks Phases 13–16 (streaming).
   *Decision taken: Kafka installs natively via Homebrew (single broker,
   KRaft mode) to keep container memory available for HDFS and Spark.*
3. **Docker daemon not running.** Docker Desktop is installed but its daemon
   socket is absent; it must be started before the HDFS containers come up.
4. **Price unit of Source 1 unverified** — gates dataset integration (§19).
5. **India Mandi coverage ends 2024-02-02**, so it cannot enrich the 2025/2026
   records used for testing and streaming.

**Scope decision:** native Hadoop MapReduce is **not required** for this course
and will **not** be implemented. All batch aggregation is done in Spark.
5. **Extreme modal prices** (0.05 … 4,000,000) need per-commodity review before
   they reach a model.
6. **Pre-existing Parquet copy** of Source 1 has unknown provenance.

---

## 6a. Combined verified scale of the real data

| | Records | CSV on disk | Date coverage |
|---|---:|---:|---|
| Daily Market Prices | 75,984,017 | 6.5 GB | 2001-01-10 … 2026-04-21 |
| India Mandi | 56,879,072 | 4.4 GB | 2000-10-19 … 2024-02-02 |
| **Combined** | **132,863,089** | **10.9 GB** | **2000-10-19 … 2026-04-21** |

Both sources are now fully profiled with Spark. Every figure above came from an
executed job, and the underlying CSVs are written to
`results/profiling/<dataset>/`.

This also settles the chronological split (brief §24). Source 1 alone supports
it; the proposed 2001–2023 / 2024 / 2025 boundaries are viable because every
year from 2002 onward has ≥ 299k records, and 2024 (5.54M) and 2025 (5.83M) are
both complete. 2026 (582k, partial to 22 Apr) is reserved for inference and the
streaming demonstration, as the brief intends.

---

## 7. Revised ~18 GB workload arithmetic

Because the real CSV source is 10.9 GB rather than 11.5 GB:

```
Real source data (CSV, both datasets)     ≈ 10.9 GB
Synthetic scaled workload required        ≈  7.1 GB
                                            --------
Target experimental workload              ≈ 18.0 GB
```

The synthetic portion will carry `data_source = "synthetic_scaled"` while all
original rows carry `data_source = "real"` — the column already exists in the
canonical schema and is populated by both readers today. The final size will be
**measured with `du -sh` and recorded**, not asserted.

> Note: 18 GB of CSV becomes far smaller as Snappy Parquet (the existing
> Parquet copy compresses Source 1's CSV roughly 10:1). Volume claims will
> therefore always state the format they refer to.

---

## 8. Next recommended action

Phases 1–4 are complete and verified. Next, in order:

1. **Phase 5–6 — preprocessing → partitioned Parquet** under `data/processed/`,
   written to local disk first. Deduplication on the business key, quality
   flagging, per-commodity outlier treatment, partitioning by year. Not blocked
   by anything.
2. **Settle the Source 1 price-unit question** empirically, by comparing modal
   prices for the same commodity/market/date across both sources during their
   overlap period (2001 – Feb 2024). This is now possible because both sources
   are profiled and their overlap is known.
3. **Phase 7 — HDFS.** Start the Docker daemon, bring up HDFS with 2–3
   DataNodes, load raw + processed data, verify replication.
4. **Phase 8 onward** — feature engineering, then forecasting and anomaly
   detection.

Nothing above is blocked. Phases 5–6 write to local disk and are repointed at
`hdfs://` by changing a path prefix, so the HDFS work in step 3 can proceed in
parallel without stalling the pipeline.
