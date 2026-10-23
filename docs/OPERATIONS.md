# Operations: scheduled refresh, freshness and failure handling

## What the refresh does (`scripts/refresh.sh` → `py/agri/ops/refresh.py`)

| # | Step | Command | Retries |
|---|---|---|---|
| 1 | Fetch new official days | `agri.ingest.backfill --from 2025-10-01 --to <yesterday>` (completed days are skipped) | 2 (plus per-request retries) |
| 2 | Re-fetch the revision window | `agri.ingest.backfill --refresh` for the last 3 days | 2 |
| 3 | Silver v2 | `IngestLanding cutoff=2025-10-01` | 1 |
| 4 | Features (scoring scope) | `BuildForecastFeatures` with `AGRI_HISTORY_START=2023-10-01`, `AGRI_PANEL_FROM=data/forecast/panel_entities` | 1 |
| 5 | Publish to a **new** release directory | `ForecastPublish exp=$AGRI_SERVING_MODEL origin=official` → `data/gold_releases/<run_id>/` | 1 |
| 6 | Validate the release | the checks below | — |
| 7 | Switch | atomic `os.replace` of the `data/gold` symlink | — |

**Validation, which blocks the switch:**
* `meta.json` exists.
* `model_version` equals the serving experiment, and that experiment's model artifacts exist.
* `data_as_of` is not older than the live release's.
* There are at least `AGRI_REFRESH_MIN_PRICES` latest prices (default 10,000) and `AGRI_REFRESH_MIN_FORECASTS` supported forecast rows (default 4,000).
* Every supported forecast satisfies lo90 ≤ lo80 ≤ median ≤ hi80 ≤ hi90.

## Guarantees and how they are tested
| Guarantee | Test (`tests/python/test_refresh.py`) |
|---|---|
| A failure in any step leaves the served gold untouched, deletes the half-built release and writes an alert | `test_failed_step_never_changes_served_gold_and_alerts` (one case per step) |
| Older data, mis-ordered intervals or a wrong model version are never published | `test_validation_rejects_*` |
| One run at a time (exit code 75 otherwise) | `test_concurrent_run_is_refused` |
| Back-to-back runs never share a directory or delete the live release | `test_back_to_back_runs_never_share_or_delete_the_live_release`. This caught a real defect: run ids originally had one-second resolution |
| The API serves the new release without a restart and reports the refresh outcome | `test_api_reloads_when_release_switches_and_reports_refresh` |
| The last 3 days are re-fetched to pick up source revisions | `test_dry_run_plan_refetches_revision_window` |

## Freshness and stale-data indicators
* **Status file.** `results/refresh/status.json` holds `ok`, `failed_step`, `last_success`, `last_failure`, `serving_data_as_of` and `serving_model_version`. `history.jsonl` keeps every run.
* **API.** `/api/v1/meta` returns `data_as_of`, `days_since_data`, and `refresh: {last_run_ok, last_success, last_failure, failed_step}`. Error text and paths are not exposed.
* **App.** The stale-data banner appears when `days_since_data > 3`. Decision cards switch to `WATCH / forecast_expired` when the 7-day target window has passed, or when the dataset is more than 3 days old.

A failing refresh therefore degrades **visibly**: the data date stops advancing, the banner appears after 3 days, and cards stop giving present-tense advice. Stale forecasts are never relabelled as fresh.

## Alerts
Every failure is appended to `results/refresh/alerts.log`. In addition:
* **Webhook.** `AGRI_ALERT_WEBHOOK=<https URL>` posts JSON `{"text": …}`, compatible with Slack and Teams incoming webhooks.
* **macOS notification.** Set `AGRI_ALERT_MACOS=1`.

An alert that fails to send is logged and never hides the refresh failure.

## Model-version tracking
* The serving experiment is set by `AGRI_SERVING_MODEL` (default `fc_main_v3`).
* Each release's `meta.json` records `model_version` and `selected_models`.
* The status file records the version actually being served.
* Changing the serving model is a deliberate edit, made after the evaluation in `docs/EXPERIMENTS.md` Part E. The refresh never retrains.

## Scheduling (not installed)
`ops/launchd/com.agdata.refresh.plist` runs `scripts/refresh.sh` daily at 07:30. The install and remove commands are in the file. It was **not** installed during development, because installing it is a persistent change to the user's machine. On Linux, the equivalent cron line is:
```
30 7 * * * cd /path/to/AG-DATA && scripts/refresh.sh >> logs/refresh_cron.log 2>&1
```

## Manual operations
```bash
scripts/refresh.sh --dry-run          # show the plan
scripts/refresh.sh                    # full run
scripts/refresh.sh --skip-fetch       # rebuild and publish from the landed data only
```

To roll back, point the symlink at a previous release; the last 3 releases are kept:
```bash
ln -sfn "$PWD/data/gold_releases/<run_id>" data/gold.tmp && mv -f data/gold.tmp data/gold
```
