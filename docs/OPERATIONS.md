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
* The serving experiment is set by `AGRI_SERVING_MODEL`. The default has been `fc_lgbm_2025` since 2026-10-23 (`docs/PREREG_LGBM_SWITCH.md`); before that it was `fc_main_v3`.
* The models directory is taken from the experiment's `manifest.json` (`models_path`).
* If any horizon selects `lgbm`, the plan inserts a **`score_lgbm`** step before `publish_staged`. That step runs `python -m agri.forecast.lgbm score` on the refreshed features. The publish then joins the predictions and refuses to run if any origin row is unscored. A failed scoring step is handled like any other failed step (`test_failed_lgbm_scoring_never_changes_served_gold`).
* Each release's `meta.json` records `model_version` and `selected_models`.
* The status file records the version actually being served.
* Changing the serving model is a deliberate edit, made after the evaluation in `docs/EXPERIMENTS.md` Part E. The refresh never retrains.

## End-to-end run (2026-10-23)
`scripts/refresh.sh --skip-fetch` ran for real in 4 min 39 s (`logs/refresh_e2e.log`), with run id `20261023T062346924428Z` and `ok: true`.
* **First run.** The existing `data/gold` directory was adopted as `data/gold_releases/adopted_20261023T115826`, and `data/gold` became a symlink to the new release.
* **Release checks.** `data_as_of` 2026-10-22, `model_version` fc_main_v3, 58,637 latest prices, 10,422 supported forecasts.
* **API.** It was started on the switched symlink and `/api/v1/meta` returned `refresh.last_run_ok: true`. `days_since_data` was 1.

This run did not exercise network fetching (`--skip-fetch`). Fetching was exercised separately by the back-fill (`results/ingest/backfill_*.json`). A failure in a real run is covered only by the unit tests above.

**Known side effect.** Step 3 rewrites `results/ingest/revision_report.json` and `results/forecast_v2/panel_report.json` in the working tree. The row counts were unchanged, but hand-added fields (the 2025-10-01..2026-04-21 overlap window) were dropped. These files were restored from Git. Until the job writes run-scoped report copies, do not commit those two files after a refresh. The 30.0% share is also recorded in `results/ingest/mirror_monthly_share.json`.

**Serving switch (2026-10-23).**
* First, a candidate release was staged outside the live path (`data/gold_releases/candidate_fc_lgbm_2025`) and validated.
* Then `scripts/refresh.sh --skip-fetch` with the new default switched the live gold: run `20261023T083639194149Z`, 5 min 26 s, `ok: true`.
* The API reported `model_version: fc_lgbm_2025` and `model: lgbm` per horizon.
* The demo snapshot `app/demo/` was regenerated from it.

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

## Public links
| Link | Data | Availability |
|---|---|---|
| **https://kaushalrog.github.io/AG-DATA/** (GitHub Pages) | **The complete served release:** all 3,899 markets and 58,637 series, with prices, charts, forecasts, comparisons and alerts | **Always on.** Static files: no server, no sleep, nothing running on the laptop |
| `scripts/demo_tunnel.sh` → `https://<random>.trycloudflare.com` | The same data through the real API | Only while the script runs on the laptop. Optional |

**How the always-on site works.**
* `scripts/publish_snapshot.sh` runs `py/agri/analysis/export_snapshot.py`, which re-packs every API response of the served release as static files (about 4 min, 211 MB, with a 29 MB archive).
* The script uploads the archive to the GitHub Release **`data-snapshot`**, replacing the previous one, so the data never enters the Git history.
* It then re-runs the Pages workflow, which unpacks the archive into the site.
* When no API is reachable, the app reads the snapshot (`app/js/api.js`, "snapshot" mode). If none is deployed, it falls back to the small bundled demo.
* Data age is computed from the viewer's date. After 3 days the usual "These are not today's prices" banner appears, and forecasts expire as on the live server.

**Parity.**
* `node tests/snapshot_parity.mjs build/snapshot http://127.0.0.1:7861/api/v1 --sample 2000` compares snapshot mode with a running API container (start it with a high `AGRI_API_RATE_PER_MIN`).
* On 2026-10-24: **46,489 comparisons, 0 differences**. Items tied in the API's sort order are compared as sets.
* The same check found that unstable sort ties made API pages skip or repeat rows. Total orders were added.

**Updating the public data** (on the laptop, which has the data.gov.in key):
```bash
scripts/refresh.sh && scripts/publish_snapshot.sh
```
Nothing runs on a schedule. The site shows exactly the release published last, with its date.

**Hosts tried.** Hugging Face Docker Spaces now need a paid PRO plan (HTTP 402 on create), so no Space was created. The server bundle (`deploy/hf-space/Dockerfile`, port 7860, about 190 MB RAM) still runs on any Docker host.
