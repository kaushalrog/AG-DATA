# Response to the red-team review (`docs/RED_TEAM_REVIEW.md`)

Status: **FIXED** (code or docs changed and verified by a test or a rerun), **DISCLOSED** (a limitation stated in docs/paper, not removable here), **OPEN**.

| ID | Sev. | Status | What changed | Verification |
|---|---|---|---|---|
| RT-01 | CRITICAL | FIXED | Unusable messages go to a separate quarantine query **before** the watermark, so broker time is never used as event time. Parity now also compares sent vs received ids in both directions | `StreamingSpec` "…never move the watermark (RT-01)". Demo: 20,000/20,000 events delivered, 207 quarantined, 0 dropped by the watermark (`results/streaming/demo_summary.json`) |
| RT-02 | HIGH | FIXED | One canonical rule (`conf/decision_rules.json` v2026-10-23.1): primary horizon h7 and a fixed precedence. API, app and Spark backtest all implement it | Shared `conf/decision_fixtures.json` (17 cases) run by pytest, node and ScalaTest. The app also reproduces every exported server decision |
| RT-03 | HIGH | FIXED | New `forecast_expired`: WATCH whenever today is past the h7 window or the dataset is more than 3 days old. The rule's verdict on the data date is kept as `decision.at_snapshot`, labelled history in 6 languages | `test_forecast_payload_and_decision`, app fixture tests. Checked in the browser in Tamil |
| RT-04 | HIGH | FIXED | The pipeline script stops on any failed step. The manifest has a `completed` flag, and Publish refuses partial experiments. The invalid fallback spec was removed | script review; `ForecastPublish` `require(completed)` |
| RT-05 | HIGH | FIXED | NameNode UI and RPC ports, and the Spark master UI, bound to `127.0.0.1`. RPC moved to host port 19000 (9000 was in use by php-fpm) | `docker/docker-compose.yml` |
| RT-06 | HIGH | FIXED | README rewritten. Every number points to `results/`. The old README is kept in `docs/legacy/` and the withdrawn claims are explained | `README.md`, `docs/AUDIT_PRIOR_RESULTS.md` |
| RT-07 | MEDIUM | FIXED/DISCLOSED | EXPERIMENTS A.4/A.8/A.10 describe the actual 8-spec space. The note that v1 touched the test set is now disclosed, and the v1-space selection is reported as a sensitivity row | `docs/EXPERIMENTS.md` B.2 |
| RT-08 | MEDIUM | DISCLOSED | The same-day cross-section assumption is stated. Ablation shows it is the only feature group that matters (h7 rel. MAE 0.944 → 0.960 without it) | KNOWN_LIMITATIONS #24, paper §6 |
| RT-09 | MEDIUM | FIXED | The actual commodity-selection rule is written out in `conf/forecast_commodities.txt`, EXPERIMENTS A.1 and the paper §4 | — |
| RT-10 | MEDIUM | FIXED/DISCLOSED | Streaming reference statistics now exclude the entity's last report (`mean30_prev`). Replay-window overlap is disclosed, and demo alerts are described as pipeline evidence only | `ForecastPublish`, EXPERIMENTS C.2 |
| RT-11 | MEDIUM | FIXED/DISCLOSED | Parity adds a two-way id comparison against the producer's sent list. That the replay reads batch silver (so the raw-CSV readers are not tested) is stated | `results/streaming/parity.json` |
| RT-12 | MEDIUM | DISCLOSED / OPEN | Backfill is described as a manual procedure; there is no automated job | KNOWN_LIMITATIONS #25 |
| RT-13 | MEDIUM | FIXED | The live adapter yields `PageEnd`. The CLI commits the checkpoint only after the producer flushes with 0 errors, and delivery errors give exit code 3 | `test_deferred_checkpoint_is_committed_only_after_delivery` |
| RT-14 | MEDIUM | FIXED/DISCLOSED | The rate limiter evicts the least-recently-seen half instead of clearing everyone. Per-worker and proxy limits are documented; use edge rate limiting | `docs/SECURITY.md` |
| RT-15 | MEDIUM | FIXED | Forecast `origin` comes from the forecast row, with a `forecast_origin_differs` warning. Forecast commodities without a forecast now get `insufficient_history` | API tests |
| RT-16 | MEDIUM | FIXED | Demo replaced by a real-data export (74 series, 10 states). The test enforces a provenance label | `app/demo/README.md`, `demo.test.mjs` |
| RT-17 | MEDIUM | FIXED | Service-worker `VERSION` is a content hash of the shell (`app/tools/stamp-sw.mjs`). The shell is stale-while-revalidate, and the offline badge resets once back online | `static.test.mjs` fails on a stale hash |
| RT-18 | LOW | FIXED | "byte-identical" replaced by "matches by file size" | docs, paper |
| RT-19 | LOW | FIXED | Paper §4 wording: entity key, 77% APMC in April, 6% volume in Nov 2025, "conformal" not "calibrated" | — |
| RT-20 | LOW | FIXED | DM HAC lag = h+3 (7 for next). Lag-20 sensitivity is reported | `forecast_report.py`, paper §9 |
| RT-21 | LOW | FIXED/DISCLOSED | Backtest uses each horizon's selected configuration. Selection/calibration overlap is disclosed | EXPERIMENTS C.1, KNOWN_LIMITATIONS #26 |
| RT-22 | LOW | FIXED | `hdfs_verify.sh`: valid `-put` destinations, `meta.json` check, no host glob, no jar rebuild while in use | script |
| RT-23 | LOW | FIXED | `data_as_of` = last day with at least 10% of the trailing median volume (2026-04-20; 2026-04-21 had 1 report) | publish log |
| RT-24 | LOW | DISCLOSED | Panel survivorship in training composition | KNOWN_LIMITATIONS #8 |
| RT-25 | LOW | PARTLY FIXED | `Retry-After` honoured (test). One bad record still aborts a page, by design (schema change). Offset paging over a mutable resource remains | `test_retry_after_header_is_honoured` |
| RT-26 | LOW | FIXED | `/ready` no longer leaks the exception class. ILIKE wildcards escaped. `/api/docs` is opt-in. WAPE exposed as `test_wape_pct` | API tests |
| RT-27 | LOW | FIXED | The pipeline prints when it reuses existing features; `REBUILD_FEATURES=1` forces a rebuild | script |

## Additional defects found by the integration owner during this round
* **Conformal lower bounds missing in published forecasts.** The quantile key 0.09999999999999998 ≠ 0.1 after the CSV round trip, so the lookup failed. Fixed with normalised keys (`ForecastEval.qkey`). Covered by a test and by gold-layer checks (`tests/python/test_gold_layer.py`). The benchmark's own test-period coverage was unaffected, because it used in-memory keys.
* **Parity check column order.** `exceptAll` compares by position, and the key join had reordered the columns. Fixed by re-selecting the columns.
