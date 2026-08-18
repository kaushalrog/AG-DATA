# Synthetic Scaled Workload — Report

**Real-Time Agricultural Market Anomaly Detection and Price Forecasting at Large Scale**
School of AI · Faculty: Dr. Sreeja

Generated: 2026-08-18

> Every figure in this report was measured by running code in this repository.
> Sizes come from the Hadoop `FileSystem.getContentSummary` API (the same call
> that works against `hdfs://`) and from `du`. Nothing is estimated.

---

## 1. What this data is, and what it is not

| | |
|---|---|
| **Is** | A synthetic workload generated from distributions fitted to the real datasets, for evaluating storage, partitioning, shuffle behaviour and throughput at ~18 GB |
| **Is NOT** | Government data, AGMARKNET data, public-source data, or a copy of the real records |

Every generated row carries:

```
data_source = "synthetic_scaled"
```

Every real row continues to carry:

```
data_source = "real"
```

Both were verified programmatically (§5). **No forecasting or anomaly result
will be reported from synthetic data** — it exists for scalability evaluation.

---

## 2. Headline measured result

| Quantity | Measured value |
|---|---:|
| Synthetic records generated | **350,012,867** |
| Synthetic size on disk | **7,786,042,726 bytes = 7.251 GiB** |
| Bytes per row | **22.25** |
| Year partitions | **27** (2000 … 2026) |
| Generation batches | 14 |
| Generation time | ~292 s (≈21 s per 25M-row batch) |

### Total experimental workload

```
Real source data (CSV)                    10.9 GiB    data_source = "real"
Synthetic scaled workload (Parquet)        7.25 GiB   data_source = "synthetic_scaled"
                                          ----------
Total experimental workload               18.15 GiB
```

**Two honest notes on this arithmetic:**

1. **The units are mixed.** The real figure is CSV on disk; the synthetic
   figure is Snappy Parquet. They are not the same format, so the total is a
   *disk-footprint* claim, not a like-for-like data-volume claim. Stated in
   consistent Parquet terms the workload is 1.2 GiB (real) + 7.25 GiB
   (synthetic) = 8.45 GiB; stated in record counts it is 132.3M real +
   350.0M synthetic = **482.3M records**.

2. **`du` and the byte count disagree slightly** — `du -sh` reports 7.4 G
   against the API's 7.251 GiB, because `du` counts filesystem block
   allocation across many Parquet part-files. The byte count is the precise
   figure.

The original target was ~6.5 GB, derived from an earlier estimate that the real
data was 11.5 GB. Verified measurement put the real CSV source at **10.9 GiB**
(the 7.1 GB directory includes a 641 MB pre-existing Parquet copy), so the
target was set to 7.1 GiB to actually reach ~18 GB total. Generation stopped at
7.251 GiB, the first batch boundary past the target.

---

## 3. How the data was generated

Implemented entirely in **Scala + Spark**, in three jobs:

| Job | Role |
|---|---|
| `synthetic/SynthesisProfile.scala` | Fits distributions to the real data; writes only small aggregate tables |
| `synthetic/GenerateSyntheticWorkload.scala` | Generates the workload in measured batches |
| `synthetic/VerifySyntheticWorkload.scala` | Verifies the output against the real data |

### 3.1 What is learned from the real data

Fitted on **VALID rows only** — including partial reports (`min=0, max=0`) would
drag every learned mean toward zero, and the generator would then faithfully
reproduce a reporting defect as if it were market behaviour.

| Profile table | Rows | Content |
|---|---:|---|
| `price_model` | 230,865 | Log-normal (μ, σ) of modal price + spread ratio, per (source, commodity, market) |
| `seasonal` | 4,933 | Monthly price multiplier, per (commodity, month) |
| `arrivals` | 315 | Log-normal (μ, σ) of arrivals, per commodity |
| `quality_rates` | 2 | Measured defect rates, per source |
| `year_shape` | 51 | Record share per (source, year) |

These are **aggregates — parameters of distributions, not observations.** No
individual real price is stored or reused.

**Why log-normal:** agricultural prices are strictly positive and right-skewed.
A normal model would generate negative prices and understate the upper tail.
Fitting mean/stddev of `log(price)` and exponentiating reproduces both
properties.

**Why per-market, not per-commodity:** the same commodity trades at materially
different levels in different mandis. A commodity-level model alone would erase
that structure.

### 3.2 What is taken from the real data, and what is generated

Two things are taken, and they differ in kind:

1. **The dimensional skeleton** — which mandi trades which commodity, in which
   district, in which year/month. Resampled *with replacement* from the real
   market structure. Inventing market names would produce a dataset with no
   realistic commodity–market relationships, which the brief forbids.
   Frequency-weighting comes for free: markets that report often are sampled
   often. The real `(year, month)` is preserved so that **a mandi never
   receives records in a year it did not operate**.

2. **Every measured value** — price, min/max spread, arrivals, day-of-month —
   is newly drawn from the fitted distributions. No price is copied.

So a generated row is *a plausible new observation from a real market*, not a
duplicated government record. This is verified empirically in §5 (copy
detection).

### 3.3 Controlled variation applied

| Variation | Implementation |
|---|---|
| Seasonal price change | Multiplier from the commodity's own monthly median, clamped to [0.4, 2.5] |
| Normal market fluctuation | ±5% Gaussian noise on top of the log-normal draw |
| Rare anomalies | 0.4% of rows: spike ×1.4–2.5, or drop ×0.35–0.70 — **labelled** |
| Realistic missing/noisy values | Reproduced at the *measured* real defect rates |

`min` and `max` are built as multiplicative offsets **below and above** the
already-fixed modal price, so `min ≤ modal ≤ max` holds by construction rather
than by post-hoc repair.

### 3.4 Memory behaviour

Nothing is collected to the driver except scalar counts and sizes. Profile
tables are broadcast (largest is 231k rows); the skeleton streams from Parquet
with column pruning, so price columns are never decoded during sampling. Peak
generation was comfortable within the 8 GB driver on a 16 GB machine.

---

## 4. A bug found by the verifier

The first generated batch **failed verification**, and the failure is worth
recording because it would have silently corrupted the entire workload:

```
[FAIL] min <= modal <= max on complete reports   11,581,679 violations of 14,809,307
   MIN_GT_MAX          real=0.000%   synthetic=40.424%
   VALID               real=97.174%  synthetic=20.170%
```

**Cause.** `rand()`/`randn()` are *nondeterministic* Spark expressions. The
generator reused the same `Column` objects across the `min`, `max` and `modal`
output columns. Reusing a Column does not reuse the *value* — it plants an
independent generator in each output column, so min, max and modal were each
computed from a **different random price**.

**Fix.** Materialise every random draw as a named column first, so each is drawn
once per row and every later reference is an `AttributeReference` to that single
value. Spark does not collapse these projections precisely because the
expressions are nondeterministic.

After the fix: **0 violations of 340,173,220 complete reports.**

---

## 5. Verification results

All checks executed by `VerifySyntheticWorkload` on the full 350M-row output.

### 5.1 Provenance — PASS

| Check | Result |
|---|---|
| Every synthetic row is `data_source='synthetic_scaled'` | ✅ only value present |
| Real data still marked `data_source='real'` | ✅ only value present |

### 5.2 Structural integrity — PASS

| Check | Result |
|---|---|
| `min ≤ modal ≤ max` on complete reports | ✅ **0** violations of 340,173,220 |
| No negative prices | ✅ 0 |
| No null `arrival_date` | ✅ 0 |
| Year coverage | ✅ 27 years (2000–2026), matching real |

### 5.3 Price distribution vs real (VALID rows)

| | n | p25 | p50 | p75 |
|---|---:|---:|---:|---:|
| Real | 128,588,149 | 1,130.00 | 2,000.00 | 3,645.00 |
| Synthetic | 340,173,225 | 1,114.88 | **1,995.76** | 3,683.98 |

Median ratio **0.998**.

### 5.4 Arrivals distribution vs real (tonnes)

| | n | p25 | p50 | p75 |
|---|---:|---:|---:|---:|
| Real (India Mandi) | 56,681,691 | 0.80 | 3.00 | 16.00 |
| Synthetic | 149,830,107 | 0.80 | 3.30 | 14.83 |

### 5.5 Categorical coverage

| Dimension | Real | Synthetic | Coverage |
|---|---:|---:|---:|
| state | 35 | 35 | 100.00% |
| district | 662 | 662 | 100.00% |
| market | 7,377 | 7,359 | 99.76% |
| commodity | 445 | 445 | 100.00% |
| variety | 1,603 | 1,601 | 99.88% |

The small shortfall in `market`/`variety` is expected: the rarest combinations
may not be drawn by random sampling.

### 5.6 Data-quality mix vs real

| Class | Real | Synthetic |
|---|---:|---:|
| VALID | 97.174% | **97.189%** |
| ZERO_MIN_MAX | 2.413% | 2.413% |
| MISSING_PRICE | 0.349% | 0.349% |
| ZERO_MAX | 0.049% | 0.049% |
| MODAL_OUTSIDE_RANGE | 0.015% | 0.000% |
| MIN_GT_MAX | 0.000% | 0.000% |

`MODAL_OUTSIDE_RANGE` is the one class **not** reproduced: it arises in real
data from genuine internal contradictions in a report, and the generator
constructs min/max around modal so it cannot occur. This is a stated gap, not an
oversight — see §7.

### 5.7 Copy detection — PASS

Tested how often a full `(market, commodity, date, modal_price)` tuple appears
in both datasets:

**8,048 collisions out of 349,999,854 distinct synthetic tuples = 0.002%.**

A small overlap is unavoidable — prices are rounded to 2 dp and cheap
commodities have few plausible values. 0.002% confirms the output is not a copy.

### 5.8 Null rates

| Column | Nulls | Share |
|---|---:|---:|
| `grade` | 149,918,067 | 42.83% |
| `arrivals_tonnes` | 200,094,800 | 57.17% |
| `commodity_group` | 200,094,800 | 57.17% |

These **exactly reflect the real structure**: India Mandi has no `grade` column
(42.8% of records) and Daily Market Prices has no `arrivals`/`group` column
(57.2%). No other column contains nulls.

### 5.9 Injected anomaly labels

**1,400,664 labelled anomalies (0.400%)**, in column
`synthetic_injected_anomaly`.

Ratio of price to the row's own commodity–market median:

| | n | p05 | p50 | p95 |
|---|---:|---:|---:|---:|
| Normal | 338,812,017 | 0.437 | 1.000 | 2.283 |
| Injected anomaly | 1,361,208 | 0.266 | 1.000 | 3.634 |

Injected anomalies have visibly wider tails — but **the distributions overlap
substantially**, and this is an important limitation, discussed in §7.

### 5.10 Real data untouched — PASS

| Check | Result |
|---|---|
| `data/raw/.../csv` | 6.5 G — unchanged |
| `data/raw/india_mandi` | 4.4 G — unchanged |
| CSV files modified since session start | **0 of 351** |
| `data/processed/*` | 672 M / 574 M — unchanged |

The generator writes only to `data/scaled/synthetic_market_workload/` and reads
everything else read-only.

---

## 6. Output layout

```
data/scaled/synthetic_market_workload/
├── year=2000/  ...  year=2026/          27 partitions, Snappy Parquet
```

Schema — the canonical schema plus one extra column:

```
state, district, market, commodity, variety, grade,
arrival_date, min_price, max_price, modal_price,
arrivals_tonnes, commodity_group,
source_dataset, data_source, synthetic_injected_anomaly,
quality_flag, year (partition)
```

`synthetic_injected_anomaly` exists only here. Union with the real processed
data using `unionByName(..., allowMissingColumns = true)`.

Note the processed real data also carries `price_outlier`, which the synthetic
set does not: outlier flagging is a downstream step applied when the workload is
used, not part of generation.

---

## 7. Limitations

1. **`MODAL_OUTSIDE_RANGE` is not reproduced** (real: 0.015%). The generator
   constructs min/max around modal, so this contradiction cannot arise. The
   synthetic set is therefore very slightly "cleaner" than reality in one
   specific way.

2. **Injected anomalies are not trivially separable.** Their price ratios
   (p05 0.266 / p95 3.634) overlap the normal range (0.437 / 2.283), because the
   fitted per-market σ is large relative to the injected 1.4–2.5× factor. The
   labels remain valid ground truth for *time-series* anomaly detection —
   deviation from a series' own rolling mean over consecutive days, which is a
   different and sharper signal than deviation from a static market median — but
   they should **not** be used to claim high accuracy against a static
   threshold detector.

3. **Mixed units in the 18 GB figure** (real CSV + synthetic Parquet), as
   stated in §2.

4. **Day-of-month is uniform within a month.** Real reporting has weekday and
   holiday structure that is not modelled.

5. **No cross-day autocorrelation.** Each synthetic record is drawn
   independently, so a synthetic commodity–market series is not a realistic
   *time series* — consecutive days do not trend. This makes the workload
   suitable for storage/throughput evaluation but **not** for training a
   forecasting model. Forecasting is trained on real data only.

---

## 8. Reproducing

```bash
source scripts/env.sh
sbt 'runMain com.agribigdata.synthetic.SynthesisProfile'
AGRI_SHUFFLE_PARTITIONS=64 sbt 'runMain com.agribigdata.synthetic.GenerateSyntheticWorkload --target-gb 7.1 --batch-rows 25000000'
sbt 'runMain com.agribigdata.synthetic.VerifySyntheticWorkload'
```

Generation is seeded per batch (`20260818 + batch × 7919`), so a re-run
reproduces the same workload.
