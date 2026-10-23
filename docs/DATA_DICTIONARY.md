# Data dictionary

All prices are **INR per quintal (100 kg)**. That is the unit stated by the source archive's publisher and by AGMARKNET/data.gov.in (see `docs/DATA_SOURCES.md` §Units). No unit conversion is applied anywhere in the pipeline. Dates are calendar dates in Indian Standard Time as published (`arrival_date` = date the price was reported). Timestamps produced by the pipeline (`ingest_ts`, `generated_at`) are UTC ISO-8601.

## Layers

| Layer | Local path (HDFS path) | Format / partitioning | Producer | Contents |
|---|---|---|---|---|
| raw | `data/raw/` (`/agri/raw/`) | CSV as downloaded | manual download | untouched source files; never modified |
| bronze (stream) | `data/stream/bronze/prices_raw` (`/agri/bronze/prices_raw`) | Parquet, `ingest_date=` | `PriceEventStream` | every Kafka record as received (raw JSON, topic, partition, offset, broker timestamp) |
| silver (batch) | `data/processed/daily_market_prices` (`/agri/silver/daily_market_prices`) | Parquet, `year=` | `PreprocessDatasets` | canonical columns, quality flag, deduplicated on the business key |
| silver (stream) | `data/stream/silver/prices_stream` (`/agri/silver/prices_stream`) | Parquet, `batch_id=` | `PriceEventStream` | canonicalised, de-duplicated events (same `standardize` as batch) |
| quarantine | `data/stream/quarantine/prices` | Parquet, `batch_id=` | `PriceEventStream` | unparsable / unknown-schema messages with offsets |
| features | `data/forecast/features` (`/agri/features/forecasting`) | Parquet, `year=` | `BuildForecastFeatures` | one row per (entity, report date) with features and targets |
| models | `data/forecast/models/<exp>/<horizon>/<family>` (`/agri/models/`) | Spark ML PipelineModel | `ForecastBenchmark` | fitted pipelines, versioned by experiment id |
| predictions | `data/forecast/test_predictions/<exp>/horizon=` (`/agri/predictions/`) | Parquet | `ForecastBenchmark` | test-period predictions of every candidate + intervals |
| gold | `data/gold/*` (`/agri/gold/`) | Parquet + `meta.json` | `ForecastPublish` | small tables served by the API |
| checkpoints | `data/stream/checkpoints` (`/agri/checkpoints/`) | Spark checkpoint | streaming queries | offsets, commits, dedup state |
| metadata | `results/`, `results/experiments/registry.jsonl` (`/agri/metadata/`) | JSON / CSV | all jobs | manifests, metrics, run reports |

## Canonical price record (silver)

| Column | Type | Definition |
|---|---|---|
| state, district, market | string | as published, whitespace-collapsed |
| commodity | string | as published (never translated or merged) |
| variety | string | as published |
| grade | string | as published (FAQ, Local, Medium, …) — an **attribute**, not part of the entity key (see below) |
| arrival_date | date | report date |
| min_price, max_price, modal_price | double | INR/quintal; modal = most common transaction price of the day |
| arrivals_tonnes | double | only in the India Mandi source (≤ 2024-02-02); null for Daily Market Prices |
| source_dataset | string | `daily_market_prices` \| `india_mandi` |
| data_source | string | `real` \| `synthetic_scaled` |
| quality_flag | string | first failing rule of: MISSING_DATE, MISSING_PRICE, NEGATIVE_PRICE, ZERO_MIN_MAX, ZERO_MAX, MIN_GT_MAX, MODAL_OUTSIDE_RANGE; else VALID |
| price_outlier | boolean | legacy per-commodity IQR flag (bounds fitted on all years — **not used** by forecasting; see AUDIT) |

Only `VALID` rows enter forecasting. Quality flags describe the **record**; they never delete genuine price spikes.

## Identifier harmonisation

Two changes to how the source publishes identifiers would otherwise break series in the test period. Both were measured on the silver layer:

1. **Grade relabel.** From 2025-01-27 many series switch from grade `FAQ` to `Local` with no overlap. Across every (state, district, market, commodity, variety, date) from 2023 on, the number of keys with more than one grade on the same day is **0**. Grade is therefore not part of the entity key.
2. **AGMARKNET 2.0 market rename.** From Nov–Dec 2025, 95–97% of reports carry an ` APMC` suffix (`Lasalgaon` → `Lasalgaon APMC`). The suffix is removed (`Features.normalizeMarket`). The original spelling is kept in `market_raw`.

If both spellings report on the same day, the collision is resolved deterministically (shortest original name wins). The number of collisions is written to `results/forecast/panel_report.json`.

**Entity** = `state | district | market (normalised) | commodity | variety`. `entity_id = xxhash64` of that string. It is identical in batch and streaming (`Features.entityIdCol`, tested in `StreamingSpec`).

## Causal sanity rule

A report is treated as a reporting error and excluded from forecasting when it differs from the geometric mean of the entity's previous 10 reports by more than ×5 (or ÷5), given at least 3 previous reports. The rule looks only backwards, so it runs the same way in batch, in streaming and when forecasts are published. The number of rows removed is in `panel_report.json`.

## Kafka event (`agri.prices.v1`, schema_version 1)

Key: business key `state|district|market|commodity|variety|grade|arrival_date` (UTF-8). Value: JSON with the fields `schema_version, event_id, state, district, market, commodity, variety, grade, arrival_date (ISO), min_price, max_price, modal_price, price_unit, source, source_record_ts, ingest_ts, data_origin (live|replay|fixture|synthetic), quality_flag`.

* `event_id` is a content hash. An exact re-send has the same id and is dropped. A corrected price for the same key gets a new id and is kept, which makes it a revision.
* **Schema evolution:** consumers accept `schema_version ∈ {1}`. Any other version goes to quarantine. Adding optional fields is backward compatible because `from_json` ignores unknown fields. Renaming or removing a field requires a new version and a new topic suffix (`.v2`).

## Feature table (`data/forecast/features`)

One row per entity and report date (`origin` t). Every feature uses only reports dated ≤ t; tests in `ForecastFeaturesSpec` enforce this.

| Column | Definition |
|---|---|
| lp | ln(modal_price) at t |
| ret1, ret2, ret5 | lp − lp of the 1st/2nd/5th previous report |
| gap1 | days since the previous report |
| mean7/30/90, dev7/30/90 | mean of lp over the calendar windows [t−6,t], [t−29,t], [t−89,t]; dev = lp − mean |
| std30, std90 | sample standard deviation of lp over 30/90 days (volatility) |
| cnt30, cnt90 | number of reports in 30/90 days (reporting density) |
| hi30, lo30 | lp − max / min of lp over 30 days |
| spread | (max_price − min_price) / modal_price on day t |
| ly_dev, has_ly | lp − mean lp within ±3 days of t−365; indicator that this exists |
| ly_chg_<h> | last year's change from t−365 to t+h−365 (both windows ≥ 348 days old) |
| cs_dev30, cs_ret1, cs_n | same-day average of dev30 / ret1 across all markets of the commodity; number of reporting markets |
| sc_dev30 | same as cs_dev30 within the state |
| doy_sin, doy_cos, dow | calendar position |
| commodity_idx | StringIndexer index (fitted on training rows only) |
| y_<h> | target: ln P(target) − lp; see horizons |
| tday_<h> | day number of the target report |
| snaive_<h> | seasonal-naive forecast (log return) |
| in_panel | entity eligible for training/evaluation (≥ 300 report days in 2021–2023) |

Missing feature values are set to 0. Every such feature has a companion indicator (`has_ly`) or a count (`cnt30`), so the model can tell that a value was missing.

### Horizons

| Name | Target |
|---|---|
| next | the next report, if within 7 days |
| h3, h7, h14 | the first report dated in [t+h, t+h+3]; no label if none |

## Gold tables (API)

* `latest_prices`: one row per entity with a report in the last 120 days of data, plus days_old, change_7d_pct, cnt30 and std30.
* `price_history`: 180 days of reports for those entities.
* `latest_forecasts`: one row per (entity, horizon), with these columns:
  * origin_date and origin_price;
  * the target window (target_from, target_to);
  * median, lo80, hi80, lo90 and hi90 in INR/quintal, plus the log-scale versions;
  * model, supported and unsupported_reason;
  * explanation inputs: std30, cs_dev30 and ly_chg.
* `alerts`: reports in the last 30 days of data flagged as price_spike, price_drop or suspect_data_error. Each is scored against the previous 30 days only.
* `entity_stats`: trailing mean and std of lp as of each entity's last report. It is the reference for streaming alerts.
* `meta.json`: data_as_of, model_version, selected models, source and licence.
