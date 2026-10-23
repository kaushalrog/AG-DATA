# AG-DATA 2.0: mandi price forecasting and farmer decision support

> Current paper scope: the **smaller clean-source study is primary**; older national-scale
> results are separate historical supporting material. See [third-review response](docs/THIRD_REVIEW_RESPONSE.md).
> Frozen prototype future-window collection has started locally, with **no outcomes evaluated**.


> Research evidence update: [second-review response](docs/SECOND_REVIEW_RESPONSE.md)
> separates the clean-source smaller-study reproduction from historical full-size
> results. Statistical intervals remain approximate; LightGBM adoption is exploratory.
> The working paper is not yet recommended for submission.


Scala · Apache Spark 4.2 (SQL, MLlib, Structured Streaming) · Kafka 4.3 · Hadoop HDFS 3.4 · FastAPI + DuckDB · a six-language PWA

**Course:** 23AID302 Big Data Analytics, Amrita Vishwa Vidyapeetham. **Guide:** Dr. Sreeja.
**Team:** C Rishitha (CB.AI.U4AID24109), Karthikeya Y (CB.AI.U4AID24163), Ashwin Tyagi (CB.AI.U4AID24167), Kaushal S (CB.AI.U4AID24168).

AG-DATA forecasts the **modal price that an Indian mandi will report** for 36 staple commodities, at 1 (next report), 3, 7 and 14 days ahead. Each forecast comes with **conformal prediction intervals whose test coverage is measured**. The forecasts are served to an installable web app in English, Tamil, Telugu, Malayalam, Hindi and Kannada. The app turns them into cautious **SELL / HOLD / WATCH / COMPARE** market-outlook cards that a farmer can adjust with their own costs.

> **Status of the data (2026-10-23).** The models were trained and tested on the archived AGMARKNET dataset (Kaggle mirror, to 2026-04-21). With a data.gov.in API key the official data was then back-filled: **7.7 M records, 2025-10-01 → 2026-10-22**, from the variety-wise history resource. The gold layer the app serves is now current to **2026-10-22**. The live current-day resource was streamed through Kafka once as a check, and runs only when triggered. The back-fill showed that the Kaggle mirror holds only about 30% of official reports after September 2025. No public deployment exists.

> **Served model (2026-10-23): LightGBM `fc_lgbm_2025`.** It was trained on 2016–2024 and validated on 2025. On the 2026 final test, rows identical to the previous Spark model, it scores rel. MAE 0.944 / 0.933 / 0.934 / 0.922, against 0.965 / 0.955 / 0.958 / 0.946. It is better at every horizon (Holm-adjusted DM p ≤ 4e-16), with 80% coverage of 77.5–79.0%.
>
> It replaced `fc_main_v3` under a rule committed before training ([docs/PREREG_LGBM_SWITCH.md](docs/PREREG_LGBM_SWITCH.md)). The 2026 test had been used before, so this is not an independent confirmation ([docs/VERIFIED_METRICS.md](docs/VERIFIED_METRICS.md) §4b). The tables below are the original `fc_main_v3` study.

## Results

### Main test (2025-01-01 … 2026-04-21, archive data, scored once)

Every number below comes from `results/forecast/fc_main_v3/`; the protocol is in [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md).

| Horizon | Persistence MAE (₹/q) | Selected model | Its MAE | Rel. MAE | Diebold–Mariano p | 80% interval coverage |
|---|---:|---|---:|---:|---:|---:|
| next report | 189.0 | GBT, absolute loss | 183.5 | **0.971** | 1e-22 | 78.6% |
| 3 days | 242.6 | GBT, absolute loss | 231.1 | **0.953** | 4e-47 | 79.4% |
| 7 days | 308.8 | Random forest | 289.7 | **0.938** | 4e-39 | 80.0% |
| 14 days | 397.0 | Random forest | 366.4 | **0.923** | 9e-29 | 80.5% |

* **Honest baselines.** Persistence (last report) is hard to beat. Between 17% and 34% of target changes are exactly zero, because mandis re-quote prices. Squared-loss models do not beat persistence at the next-report horizon; absolute-loss gradient boosting does. Seasonal naive and moving averages are worse than persistence. A per-series exponential smoother, run on a 400-series sample, **matches** the global model at 1–3 days; the learned model is clearly better only at 7–14 days.
* **Breadth.**
  * 11,845 mandi series and 1.5–1.7 M test forecasts per horizon.
  * The model beats persistence on 58–76% of individual series.
  * At 7 days it improves on persistence for all 36 commodities.
* **A data-quality artefact, found and corrected.** On the archive, the gains seemed to shrink and 80% intervals covered only 68–73% after the AGMARKNET 2.0 migration (Nov 2025). Re-scoring the same frozen models on the **complete official data** shows 78.0–78.7% coverage after Nov 2025, and relative MAE of 0.962–0.976. Most of the apparent "shift" was the mirror's missing reports.
* **Decision cards are conservative.**
  * WATCH on about 98% of report-days.
  * HOLD on 0.5%, correct 80% of the time at 7 days; SELL on 1.0%, correct 68%.
  * These are hit rates on published prices, not farm profits.
* **Anomaly flags** are evaluated on injected corruptions: PR-AUC 0.70, against 0.35 for the legacy IQR rule. No accuracy is claimed for real anomalies, because no labels exist.

### Frozen models on new data (no refitting; `results/forecast/fc_main_v3/{test_complete,prospective}/`)

| Evaluation | next | 3 d | 7 d | 14 d | 80% coverage | DM p |
|---|---:|---:|---:|---:|---:|---:|
| Same test period, complete official data (1.8–2.0 M forecasts per horizon) | 0.972 | 0.954 | 0.943 | 0.925 | 79.2–80.3% | ≤ 3e-41 |
| **Prospective: 2026-04-22 → 2026-10-22**, reports absent from the archive and first downloaded after the models were saved (0.27–0.31 M per horizon) | **0.963** | **0.955** | **0.958** | **0.952** | 76.9–80.1% | ≤ 1e-15 |

Values are relative MAE against persistence (lower is better). The prospective period was never seen by any model, tuning step or calibration: models trained on data to 2023 still beat persistence by 4–5% six months past the archive's end.

**Retraining check (`fc_retrain_2025`).** Models were retrained on data to 2024, with 2025 used for selection, and tested on 2026-01-01 → 2026-10-22, a period not used for any retraining choice (it overlaps the main test and the frozen-model hold-out). They score rel. MAE 0.966 / 0.955 / 0.958 / 0.950, against 0.965 / 0.955 / 0.958 / 0.946 for the frozen models on identical rows. No difference is significant (DM p 0.12–0.99), so the frozen models keep serving. They are **not** "current": they encode nothing after 2023.

**A stronger baseline beats the served model.** A global LightGBM (L1 loss, same features, tuned on validation only) reaches 0.944 / 0.926 / 0.915 / 0.892 on the main test (DM p ≤ 1e-8 against the MLlib model). This finding led to the serving switch described at the top of this section. Details: [docs/VERIFIED_METRICS.md](docs/VERIFIED_METRICS.md), `docs/EXPERIMENTS.md` Part E.

> The earlier README claimed "95.66% accuracy / 86.55% precision". No code or log in the repository produces those numbers, so they have been withdrawn. See [docs/AUDIT_PRIOR_RESULTS.md](docs/AUDIT_PRIOR_RESULTS.md). The previous README is kept in [docs/legacy/README_v1.md](docs/legacy/README_v1.md).

## Architecture

```
data.gov.in API --(key)--> ingest adapter --+                 +-> bronze (raw + offsets)
AGMARKNET archive --------> replay ---------+-> Kafka --------+-> quarantine (invalid, before watermark)
                                                agri.prices.v1 +-> silver (stream) -> alerts
raw CSV -> Spark readers -> quality -> dedup -> silver (Parquet) -> harmonise -> features (<= t) -> targets (> t)
        -> baselines + MLlib (LR, Huber, RF, GBT-L2, GBT-L1) -> validation choice -> conformal -> test once
        -> gold (Parquet) -> FastAPI + DuckDB (read-only) -> PWA (6 languages, offline, decision cards)
```

Why each piece exists, the delivery semantics, the HDFS layout and the replay procedure: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Repository map

| Path | Contents |
|---|---|
| `src/main/scala/com/agribigdata/forecast/` | `BuildForecastFeatures`, `ForecastBenchmark`, `ForecastBacktest`, `ForecastProspective` (frozen-model scoring), `ForecastPublish`, plus `Features`, `ForecastModels`, `ForecastEval`, `DecisionRules` |
| `src/main/scala/com/agribigdata/ingestion/IngestLanding.scala` | official back-fill → silver v2, revision report |
| `src/main/scala/com/agribigdata/streaming/` | `PriceEventStream` (Kafka → bronze/quarantine/silver/alerts), `CanonicalEvent` (shared batch/stream canonicalisation), `StreamParityCheck` |
| `src/main/scala/com/agribigdata/bench/` | `ScalabilityBench` |
| `src/main/scala/com/agribigdata/{ingestion,preprocessing,profiling}` | readers, quality rules, de-duplication, profiling (v1, retained) |
| `src/test/scala/` | leakage/perturbation, metric, conformal, decision and streaming tests (ScalaTest) |
| `py/agri/ingest/` | data.gov.in adapter for both resources (retry, rate limit, `Retry-After`, delivery-tied checkpoints, key redaction), resumable back-fill, archive replay, Kafka producer CLI |
| `py/agri/api/` | FastAPI service and decision rule |
| `py/agri/analysis/` | DM tests and report tables/figures, anomaly benchmark, SES baseline, stream summary, demo export |
| `app/` | the PWA (no framework, 69 KB of JS, six languages, service worker, real-data demo snapshot) |
| `conf/` | commodity list, decision rules and shared decision fixtures |
| `docs/` | architecture, data sources, data dictionary, experiments, model card, deployment, security, research gap, red-team review, limitations, farmer guide |
| `paper/` | manuscript draft (LaTeX), references, generated tables and figures |
| `results/` | experiment outputs and registry (`results/experiments/registry.jsonl`) |

## Quick start

```bash
source scripts/env.sh                       # pins Java 21 for Spark
uv venv .venv -p 3.12 && uv pip install -p .venv/bin/python -e ".[test]"
sbt test                                    # Scala tests
.venv/bin/python -m pytest -q tests/python  # Python tests
node --test app/tests/                      # app tests
```

Reproduce the experiment and serve the app. This needs the raw archive in `data/raw/` and the silver layer (`sbt "runMain com.agribigdata.preprocessing.PreprocessDatasets"`).

```bash
scripts/run_forecast_pipeline.sh fc_main_v3
PYTHONPATH=py .venv/bin/uvicorn agri.api.app:app --app-dir py --port 8000   # then open http://localhost:8000
```

Refresh from the official API (key in a git-ignored `.env`, see `.env.example`), then rebuild and republish without retraining:

```bash
set -a; . ./.env; set +a; PYTHONPATH=py .venv/bin/python -m agri.ingest.backfill --from 2025-10-01 --to $(date -v-1d +%F)
```

```bash
scripts/submit.sh com.agribigdata.ingestion.IngestLanding cutoff=2025-10-01
```

```bash
AGRI_HISTORY_START=2023-10-01 AGRI_PANEL_FROM=data/forecast/panel_entities AGRI_SILVER_DAILY=data/processed/daily_market_prices_v2 AGRI_FORECAST_ROOT=data/forecast_v2 scripts/submit.sh com.agribigdata.forecast.BuildForecastFeatures
```

```bash
AGRI_SILVER_DAILY=data/processed/daily_market_prices_v2 AGRI_FORECAST_ROOT=data/forecast_v2 scripts/submit.sh com.agribigdata.forecast.ForecastPublish exp=fc_main_v3 origin=official models=data/forecast/models/fc_main_v3
```

Streaming demonstration (real archived reports replayed through Kafka, with labelled fault injection) and the HDFS check:

```bash
scripts/streaming_demo.sh 20000 2000
scripts/hdfs_verify.sh
```

Offline demo of the app only: `python3 -m http.server -d app 8080`.

## Documentation
* [Architecture](docs/ARCHITECTURE.md), [Data sources](docs/DATA_SOURCES.md), [Data dictionary](docs/DATA_DICTIONARY.md), [API](docs/API.md)
* [Experiments and results](docs/EXPERIMENTS.md), [Model card](docs/MODEL_CARD.md), [Research gap and literature](docs/RESEARCH_GAP.md)
* [Deployment](docs/DEPLOYMENT.md), [Security](docs/SECURITY.md), [Known limitations](docs/KNOWN_LIMITATIONS.md), [Red-team review](docs/RED_TEAM_REVIEW.md)
* [Farmer guide](docs/FARMER_GUIDE.md), [Audit of earlier claims](docs/AUDIT_PRIOR_RESULTS.md)

## Licence and attribution
Price data: AGMARKNET, Directorate of Marketing and Inspection, Ministry of Agriculture and Farmers Welfare, via data.gov.in, under the Government Open Data Licence – India. App icons and illustrations are original (CC0; see `app/ASSETS.md`).
