# AG-DATA 2.0 red-team review

Reviewer: independent red team. Date: 2026-10-23. Scope: code, protocol, docs and paper sections 01–03. I did not read test-period numbers: `data/forecast/test_predictions` and `results/forecast/fc_main_v3` were off limits and are not used here.

Method: I read the source files listed under each finding. I ran `node --test app/tests/` (53/53 pass) and `.venv/bin/python -m pytest -q tests/python` (39/39 pass). I also ran read-only DuckDB queries (4 threads) on `data/forecast/features` and `data/processed/daily_market_prices`. No JVM job was started.

## Summary

| ID | Severity | Area | Finding |
|---|---|---|---|
| RT-01 | CRITICAL | Streaming | One malformed message moves the event-time watermark to wall-clock time, so every later replayed event is silently dropped from silver. The tests and the parity check cannot detect this. |
| RT-02 | HIGH | Decision rule | The API, the PWA and the Spark backtest implement three different rules. The rule served to farmers (HOLD if *any* of h7/h14/h3 qualifies, then SELL, then COMPARE) was never back-tested. |
| RT-03 | HIGH | Decision rule / UI | "Stale" is measured against the dataset's end date, not today. Archived forecasts whose target windows ended months ago still produce present-tense SELL/HOLD cards. |
| RT-04 | HIGH | Reproducibility | `run_forecast_pipeline.sh` swallows every job failure (`\|\| true`) and still prints "experiment complete". The backtest's fallback spec does not exist. |
| RT-05 | HIGH | Security | The HDFS NameNode ports 9870 and 9000 are published on all interfaces, running as root with permissions disabled. `SECURITY.md` and `ARCHITECTURE.md` say they are localhost-only. |
| RT-06 | HIGH | Claims | `README.md` still advertises the unreproducible 95.66%/86.55% anomaly metrics, "end-to-end exactly-once" and "93.41 million records". `AUDIT_PRIOR_RESULTS.md` says these "must not be cited". |
| RT-07 | MEDIUM | Protocol | Run v1 computed test-period metrics and wrote test files before the A.10 amendment. Protocol docs still describe the v1 search space ("6 fits"), not the 8-spec space in code. |
| RT-08 | MEDIUM | Leakage | The same-day cross-sectional features (`cs_*`, `sc_*`) assume that every day-t report is known at the end of day t. There is no evidence about publication lag, and there is train/serve skew in live use. |
| RT-09 | MEDIUM | Claims / protocol | The commodity-selection rule ("36 with the most VALID reports 2021–23") does not reproduce: 4 of the 36 rank 40–43, while ranks 31–33 and 37–39 were skipped. |
| RT-10 | MEDIUM | Streaming / anomaly | Streaming alerts are scored against `entity_stats` that include the scored report and later ones when the replay window overlaps the gold snapshot. This contradicts "trailing statistics that exclude it". |
| RT-11 | MEDIUM | Streaming | The parity check is circular (replay reads batch silver) and joins batch rows to stream keys only, so missing stream rows can never fail it. |
| RT-12 | MEDIUM | Streaming / docs | The "batch backfill" that reconciles late events and corrections (`ARCHITECTURE.md`) is not implemented: no code reads `bronze/` or `silver/prices_stream`. |
| RT-13 | MEDIUM | Ingestion | The checkpoint advances before Kafka delivery is confirmed, and delivery errors still exit 0. A crash or broker error loses a page silently. |
| RT-14 | MEDIUM | API | The rate limiter is per worker (2 workers) and keyed on the proxy IP. `X-Forwarded-For` can be spoofed if forwarded IPs are widened. The whole table is cleared at 50k keys. |
| RT-15 | MEDIUM | API / publish | The forecast `origin` comes from `latest_prices`, while intervals are anchored on the latest *feature* row; 165 entities differ by more than 7 days. 6,170 recent entities are told "not_in_forecast_commodities" even when their commodity is a forecast commodity. |
| RT-16 | MEDIUM | Frontend / provenance | The demo snapshot is synthetic, yet it is labelled "AGMARKNET via data.gov.in (archived)" under GODL-India with `data_origin: archive`. |
| RT-17 | MEDIUM | Frontend | The service-worker shell is cache-first with a fixed `VERSION='v1'`, so code updates never reach installed clients. The "offline/cached" status never returns to live. |
| RT-18 | LOW | Provenance | "Byte-identical" to Kaggle v134 was checked by file size only. |
| RT-19 | LOW | Paper wording | The grade-uniqueness claim is false at the stated key, "95–97% APMC" ignores April (77%), Nov-2025 volume is 6% (not 20–35%), and "calibrated" is used before any result. |
| RT-20 | LOW | Statistics | The Diebold–Mariano HAC lag equals h, but the target windows overlap up to h+3 days (7 for `next`), so the lag is too short. |
| RT-21 | LOW | Protocol | The conformal set equals the selection set. The 2024 backtest fold equals the validation year. The backtest refits "best h7 GBT", not "the selected configuration" as the paper says. |
| RT-22 | LOW | Reproducibility | `hdfs_verify.sh` bugs: `-put` with no destination, a hard dependency on `data/gold/meta.json`, and a glob expanded on the host. |
| RT-23 | LOW | Data | `data_as_of` (2026-04-21) is defined by a single valid record. |
| RT-24 | LOW | Protocol | Panel eligibility from 2021–23 also filters 2016–20 training rows (survivorship in the training composition). |
| RT-25 | LOW | Ingestion | Schema validation checks presence only. One bad record aborts the run. `Retry-After` is ignored. Offset paging runs over a mutable resource. |
| RT-26 | LOW | API | Minor issues: `/ready` leaks the exception class, ILIKE wildcards are unescaped, `/api/docs` is public, WAPE is labelled "MAE % of price", and global coverage is shown per commodity. |
| RT-27 | LOW | Reproducibility | The pipeline silently reuses an existing `data/forecast/features` built by older code. |

---

## RT-01 (CRITICAL): a malformed message poisons the watermark and silently drops all later events

**Evidence**
- `PriceEventStream.scala:149-151`: `.withColumn("event_time", coalesce($"event_time", $"kafka_ts"))`. The comment says this is done "so the watermark does not discard them".
- `PriceEventStream.scala:154-156`: `.withWatermark("event_time", "10 days").dropDuplicatesWithinWatermark("dedup_key")`. The watermark is global to the query: max(event_time) − 10 days. Spark's dedup operators drop input rows older than the watermark.
- The replay events carry `event_time` = `arrival_date`, which is 2026-04-15..21 in `scripts/streaming_demo.sh:39`. An unparsable record (injected at 1% by `--invalid 0.01`, `replay.py:57-58`) carries `kafka_ts` = wall-clock time, 2026-10-23. After the first micro-batch that contains one, the watermark becomes about 2026-10-13. Every later replay event (April) is then older than the watermark and is dropped. It does not reach silver or quarantine, and no counter in `batches.jsonl` records it. Records whose `arrival_date` string cannot be parsed hit the same path (`__canonical_null`, `PriceEventStream.scala:148`).
- `StreamingSpec.scala:117-130` puts the invalid messages in the **same** micro-batch as the valid one, so the test cannot see the effect. `StreamingSpec.scala:101-115` itself shows that events behind the watermark are dropped.
- `StreamParityCheck.scala:40` builds `batchForStream` by joining batch rows to **stream** keys. Records missing from the stream never show up as mismatches, so `parity` stays `true`.
- `stream_summary.py` does not report `numRowsDroppedByWatermark`.
- No `results/streaming/` exists yet, so no published number is affected so far. The demo as scripted would, however, lose almost all events after the first batch.

**Why it matters.** It breaks the "effectively-once output per offset range" claim (`ARCHITECTURE.md:62`, `paper/05_system.tex:61`), and it can never be caught by the parity evidence offered for it.

**Recommended fix**
- Route unparsable and undated rows to quarantine **before** the watermark. Either split them into a separate stateless query, or give them `event_time = null` and filter `parsable && !__canonical_null` before `withWatermark`.
- Never use broker time as event time.
- Add a two-batch test: batch 1 holds an invalid message, batch 2 holds valid April events, and every valid event must reach the sink.
- Make the parity check a full outer comparison over the replayed key set, taken from the producer summary or bronze, not over the stream keys.
- Surface `numRowsDroppedByWatermark` in `stream_summary`.

## RT-02 (HIGH): three different decision rules, and the served one was never back-tested

**Evidence**
- **Spark backtest** (`ForecastEval.scala:137-143`): one horizon at a time. HOLD if lo80 ≥ ln(1+c), otherwise SELL if hi80 ≤ 0, otherwise WATCH. No support, stale or COMPARE logic.
- **API** (`decisions.py:43-65`):
  - unsupported returns WATCH with `insufficient_history`, whatever the reason (`stale_beyond_limit` included);
  - stale returns WATCH;
  - otherwise it is HOLD if **any** horizon in (h7, h14, h3) qualifies, then SELL if any qualifies, then COMPARE (district scope, no transport, freshness relative to the reference report's date, `app.py:286-292`), then WATCH;
  - `next` is ignored.
- **PWA** (`decision.js:62-86`, `commodity.js:116,124`): one horizon, the server's `d.horizon` or h7.
  - It maps `stale_beyond_limit` to `stale_data`.
  - COMPARE uses `api.compare(id, 'state')` (`commodity.js:20`): state scope, with transport subtracted, and freshness against the dataset end (`decision.js:40-41`).
  - It works on rupee values rounded to 2 decimals.
- A concrete divergence: if h7 has hi80 ≤ 0 (backtest h7 = SELL) and h14 has lo80 ≥ ln(1.01+0.10), the API returns HOLD (h14). No backtest evaluates "HOLD if any horizon", and the "OR over three horizons" raises the false-HOLD rate compared with any single-horizon hit rate in `decisions.csv`.
- `paper/01_intro.tex:43` says the app's "decision rule is back-tested".

**Recommended fix**
- Define one rule in `conf/decision_rules.json`: a single primary horizon (h7), and the order unsupported → stale → HOLD → SELL → COMPARE → WATCH.
- Implement it once in Python and test JS and Scala against shared golden fixtures.
- Back-test exactly the served rule (including COMPARE, or say explicitly that COMPARE is not back-tested).
- Align the COMPARE scope and freshness basis.

## RT-03 (HIGH): actionable SELL/HOLD cards on expired archive forecasts

**Evidence**
- `app.py:158-165`: `days_old = data_as_of − last_date`, measured against the dataset's own end, not `date.today()`. A report dated 2026-04-21 is "fresh" in October 2026.
- `decisions.py:45` and `decision.js:70` suppress signals only when `stale` is set.
- `ForecastPublish.scala:97` sets `supported` from `days_old ≤ 30` against `dataEnd`.
- The UI shows a global stale banner (`ui.js:101`), but the card still says "Selling now may be worth considering…" (`en.json:144`), for target windows such as 2026-04-22..25 that ended six months ago.

**Why it matters.** A farmer can act on a signal whose forecast window has already passed. This conflicts with the "harm from false certainty" commitments (`paper/08_app_ethics.tex:56`).

**Recommended fix**
- When `today > target_to` for the decision horizon, or when `meta.days_since_data > stale_after_days`, return WATCH with a new reason `forecast_expired` on both server and client.
- Show the intervals as "historical example" only.

## RT-04 (HIGH): the pipeline script hides failures

**Evidence**
- `scripts/run_forecast_pipeline.sh:12`: `sbt … | tee | grep … || true`. Under `pipefail`, a failing sbt step returns non-zero and `|| true` discards it.
  - When F1 fails, F2 runs on old features.
  - When F2 fails mid-way, `manifest.json` is partial (`ForecastBenchmark.scala:287`, `final_ = false`), and Publish dereferences `selected_on_validation.get(h)`, which is null (`ForecastPublish.scala:42`). That error is swallowed too.
  - Line 19 still prints "experiment … complete".
- `:16` falls back to `spec=gbt_d7_i100_s0.1`, but that spec is not in `ForecastModels.SearchSpace` (`ForecastModels.scala:41-45`), so `ForecastBacktest.scala:31` calls `sys.error`, and the error is swallowed.
- `.venv/bin/python -m agri.analysis.forecast_report` (line 17) is not wrapped in `|| true`, so the script aborts there only by accident.

**Recommended fix.** Use `set -o pipefail` with `run() { sbt … 2>&1 | tee -a log; }` and filter the display separately. Check `${PIPESTATUS[0]}`. Fail if `tuning.csv` has no GBT row. Write a `COMPLETED` marker in `manifest.json` and make Publish refuse a non-final manifest.

## RT-05 (HIGH): HDFS is exposed on the LAN, contrary to the security docs

**Evidence**
- `docker/docker-compose.yml:27-29` has `"9870:9870"` and `"9000:9000"`, which bind to 0.0.0.0. Only the Spark UI is pinned to `127.0.0.1` (`:98`).
- The containers run as `user: root` (`:25`), and `SECURITY.md:36` confirms `dfs.permissions.enabled=false`.
- `SECURITY.md:16` claims the compose file "publishes HDFS ports to the developer machine only", and `ARCHITECTURE.md:94` says "publishes them to localhost".
- With WebHDFS on 9870 and permissions off, anyone on the same network (campus Wi-Fi, a viva room) can list, rename or `op=DELETE` `/agri` as any user.

**Recommended fix.** Bind to loopback (`"127.0.0.1:9870:9870"`, `"127.0.0.1:9000:9000"`), or drop the RPC port mapping, since the cluster jobs use the Docker network. Then re-check the docs.

## RT-06 (HIGH): the README contradicts the project's own audit

**Evidence**
- `README.md:72` and `:351` claim 95.66% accuracy, 86.55% precision, 0.948 ROC-AUC.
- `:362` says "more than 6 out of 7 … alerts represent genuine, verified price shocks". The labels are a z-score threshold, not verified shocks.
- `:107` claims "end-to-end exactly-once guarantees".
- `:148` mentions "93.41 million real canonical records", but silver has 75,644,801.
- `:69` and `:364` cite throughput and latency figures with no file in `results/streaming/`.
- `docs/AUDIT_PRIOR_RESULTS.md` ("Not reproducible… Must not be cited") and `ARCHITECTURE.md:64` ("Not claimed: end-to-end exactly-once") contradict all of these.
- `git status` shows README.md modified in the working tree.

**Recommended fix.** Replace the README with the 2.0 overview and link the legacy text from `docs/legacy/`. Every numeric claim should point to a file under `results/`.

## RT-07 (MEDIUM): run v1 touched the test set before the amendment; protocol docs are stale

**Evidence**
- `logs/f2_benchmark_fc_main_v1_ABORTED_searchspace_v1.log:38` prints "selected on validation: pred_persistence".
- The crash that follows (`:39-43`) is a DIVIDE_BY_ZERO in `hashAgg_doAggregateWithKeysOutput`, which is a **grouped** aggregation. In `ForecastBenchmark.scala` the grouped aggregations run after the test overall metrics (`:214-220`) and after `test_by_commodity` is written (`:236`). The comment at `ForecastEval.scala:43-44` names the per-state breakdown.
- So test metrics for `next` were computed, and test-period files were written, before the search space was changed. `EXPERIMENTS.md:92` admits test predictions were written and deleted. The heading at `:77`, "before any test metric was read", is literally true but understates this.
- The only log lines printed before the abort are validation MAEs (`:14-36`) and the selection line; v2 (`…v2_ABORTED…:14-74`) printed validation MAEs only. So I found no evidence that test numbers were seen. The amendment rationale (34.4% exact zeros, sign-gradient step size) is based on validation and is legitimate.
- Stale protocol text:
  - `EXPERIMENTS.md:45` lists the v1 GBT grid;
  - `:74` and `KNOWN_LIMITATIONS.md:12` say "6 fits/configurations per horizon";
  - code has 8 (`ForecastModels.scala:41-45`), including Huber LR and 3 absolute-loss GBTs;
  - `EXPERIMENTS.md:3` says the protocol "was fixed in code… before the test period was scored", which v1 contradicts.

**Recommended fix**
- State plainly that v1 scored the test period for `next` and wrote files that were deleted unread.
- Report the v1-space result (squared loss only) as a pre-registered sensitivity row in the final tables, so readers can see that the amendment did not choose the test outcome.
- Update A.4, A.8 and Limitation 12 to the v3 space.
- Make `ForecastBenchmark` refuse to score the test period unless `exp` is new and its manifest is absent.

## RT-08 (MEDIUM): same-day cross-sectional features depend on undocumented publication timing

**Evidence**
- `Features.scala:185-192` computes `cs_dev30`, `cs_ret1` and `cs_n` per (commodity, day), and `sc_dev30` per (state, commodity, day), over **all** reports on day t, the entity's own report included.
- The docstring (`:181-184`) asserts this is "information published by the end of day t". AGMARKNET uploads are known to lag by one or more days, and the archive is assembled after the fact. For `next`, the target can be the report on t+1, which may be published before late day-t reports from other markets.
- `cs_n` (median 387 reports per commodity-day in 2024 panel rows) directly encodes how complete the reporting was. At serving time the latest day is incomplete: 2026-04-21 has one valid record in the whole archive. So the published forecast's `cs_*` inputs differ systematically from training.
- Self-inclusion is harmless, because the entity's own `dev30` is already a feature. In 1.07% of 2024 panel rows `sc_dev30 == dev30` exactly (sole reporter in the state).

```sql
SELECT avg((abs(sc_dev30-dev30)<1e-12)::int) FROM 'data/forecast/features/year=2024/*.parquet' WHERE in_panel;  -- 0.0107
```

**Recommended fix.** Either lag the cross-sectional aggregates by one day (use day t−1 markets), or keep them and report the `no_cross_section` ablation for all horizons, not only h7. Document the assumption in `KNOWN_LIMITATIONS.md`. At publish time, compute `cs_*` only from days at least 2 days before `dataEnd`.

## RT-09 (MEDIUM): the commodity-selection rule does not reproduce

**Evidence**
- `paper/03_problem_data.tex:34` and `conf/forecast_commodities.txt:2-4` say "the 36 commodities with the most VALID observations in 2021-2023".
- Recomputed on silver:

```
top-36 by VALID reports 2021-23 ∩ conf list = 32
in conf but not top-36: Coriander (Leaves) #41, Groundnut #43, Jowar (Sorghum) #42, Lentil (Masur)(Whole) #40
in top-36 but excluded: Banana - Green #31, Gur (Jaggery) #32, Papaya #33, Raddish (<=30)
also skipped: Mousambi #37, Ridgeguard #38, Spinach #39 (vegetable/fruit, so the "category" qualifier does not explain it)
```

**Why it matters.** It is a researcher degree of freedom that is not documented. It is not leakage (only training-period data is involved), but the claim as written is false.

**Recommended fix.** State the actual rule (for example, a manual category filter plus exclusions, with reasons) or regenerate the list programmatically from the stated rule.

## RT-10 (MEDIUM): streaming anomaly reference includes the scored report and later ones

**Evidence**
- `ForecastPublish.scala:54-55,76-77`: `entity_stats.ref_mean30/ref_std30` use `rangeBetween(-29, 0)` up to the entity's **latest** report (≤ 2026-04-21).
- `PriceEventStream.scala:109` and `Anomaly.score` (`:218-219`) score replayed 2026-04-15..21 events against them. So the reference contains the event itself and up to 6 days after it.
- `PriceEventStream.scala:187-188` ("they never include the scored observation") and `ARCHITECTURE.md:52` say otherwise.

**Recommended fix.** For a replay, compute the reference as of `event_date − 1`: store a dated stats history, or restrict the replay window to dates after `ref_date`. Assert `ref_date < arrival_date` in the scoring join and emit `no_reference` otherwise.

## RT-11 (MEDIUM): the parity evidence is close to tautological

**Evidence**
- `replay.py:21`: the replay source *is* the batch silver layer.
- `StreamParityCheck.scala:34-38` canonicalises the batch side with the same `CanonicalEvent.standardize`.
- `:40` restricts the batch side to the stream's keys.
- `:31` excludes all injected-fault events.
- The test therefore checks a JSON round-trip of the same function on its own output. It cannot detect lost events (RT-01), and it cannot detect drift between `DataQuality`/`Readers` on raw CSV and the stream path.
- `paper/01_intro.tex:41` presents it as "tested for parity".

**Recommended fix.** Compare stream silver against the replay manifest (the event_ids the producer sent, minus quarantined ones), in both directions. Add a parity case from **raw CSV** through `Readers` → `DataQuality`, versus the same rows sent as JSON events.

## RT-12 (MEDIUM): the described backfill and correction reconciliation do not exist

**Evidence**
- `ARCHITECTURE.md:57`: "The batch layer resolves them by keeping the latest ingested version when silver is rebuilt".
- `ARCHITECTURE.md:59`: late events "are picked up by the next batch backfill".
- `:68` describes a procedure.
- `grep -rln "prices_stream\|bronze" src/main/scala` matches only `PriceEventStream.scala` and `StreamParityCheck.scala`. No batch job reads bronze or stream silver, and batch silver is rebuilt from the Kaggle CSVs only.
- Corrections (new `event_id`) therefore leave two rows per business key in stream silver, and both get scored for alerts.

**Recommended fix.** Either implement `BackfillFromBronze`, which deduplicates by business key and keeps the latest `ingest_ts`, or mark the design as "not implemented" in ARCHITECTURE, paper §5 and KNOWN_LIMITATIONS.

## RT-13 (MEDIUM): the ingestion checkpoint is not tied to delivery

**Evidence**
- `datagovin.py:186-194`: the generator yields records and then saves `offset += len(records)` when the consumer asks for the next item.
- `cli.py:71-75` calls `produce()` asynchronously. Delivery is confirmed only at `flush(60)` (`:85`).
- A crash, or a broker failure reported via `on_delivery` (`:53-57`), after the checkpoint write loses that page permanently: at-most-once, not at-least-once.
- `cli.py:133-134` returns 0 even when `delivery_errors > 0`, and `flush(60)`'s return value (messages still queued) is ignored.

**Recommended fix.** Call `prod.flush()` and check errors **before** `save_checkpoint` for each page; for example, have `fetch_all` yield pages and let the caller commit. Exit non-zero if `delivery_errors` or the remaining queue length is above 0.

## RT-14 (MEDIUM): the rate limit can be bypassed or turned into a shared lockout

**Evidence**
- `app.py:139` keys on `request.client.host`.
- `Dockerfile.api:18` runs `--proxy-headers --workers 2`. Uvicorn trusts `X-Forwarded-For` only from `FORWARDED_ALLOW_IPS` (default 127.0.0.1), so behind a containerised proxy all clients share the proxy's bucket. If an operator widens it to `*`, a spoofed `X-Forwarded-For` gives each request a fresh bucket.
- Each worker process has its own `RateLimiter`, so the effective limit is 2×.
- `app.py:112-113` clears **all** buckets once there are more than 50k keys, so rotating source addresses (cheap with IPv6) resets everyone's limit.
- `SECURITY.md:22` does not mention any of this.

**Recommended fix.** Document `FORWARDED_ALLOW_IPS=<proxy ip>` (never `*`) and do the limiting at the edge. Use LRU eviction instead of `clear()`, or a shared store. State the per-worker semantics.

## RT-15 (MEDIUM): forecast origin mismatch and misleading "unsupported" reason

**Evidence**
- `ForecastPublish.scala:90-93` takes the latest row of the *feature table*. That table includes only `WarmUp` rows (`Features.scala:199`) for the 36 commodities, and its sanity flags were computed over the full history.
- `app.py:343-344` returns `origin` from `latest_prices` (`r`), not `fc.origin_date/origin_price`.
- The PWA computes HOLD/SELL with `today = fc.origin.modal_price` against intervals anchored on a different price (`commodity.js:124`).
- DuckDB check (2026 partition, last 120 days):

```
entities with both: 18,708 | latest price newer than latest feature origin: 165 | of which > 7 days: 163
recent entities of forecast commodities with no feature row at all: 6,170
```

- Those 6,170 get `unsupported_reason: "not_in_forecast_commodities"` (`app.py:307`), although their commodity is a forecast commodity. The real cause is insufficient warm-up.

**Recommended fix.** Return `origin` from the `fc` row (`origin_date`, `origin_price`), and mark the forecast unsupported when `fc.origin_date < latest price date`. Use a distinct reason (`insufficient_history`) when the commodity is in the panel list but has no feature row.

## RT-16 (MEDIUM): synthetic demo prices attributed to AGMARKNET

**Evidence**
- `app/demo/README.md` says "The current files are synthetic placeholders… invented prices".
- `app/demo/meta.json` and every `forecast_*.json` nevertheless carry `"source": {"name": "AGMARKNET via data.gov.in (archived)", "licence": "GODL-India"}` and `"data_origin": "archive"`, generated by `app/tools/make_demo.py:17-21`.
- The PWA renders this source on the provenance card (`commodity.js:98-103`).
- The demo banner ("Prices are examples only", `en.json:51`) mitigates this, but the source line is false.

**Recommended fix.** Set `source.name` to "Synthetic demo data (not AGMARKNET)" and `data_origin` to `"synthetic"`, or ship a real archived export through `py/agri/analysis/export_demo.py` as the README intends.

## RT-17 (MEDIUM): installed PWAs never update, and the status stays "cached"

**Evidence**
- `sw.js:6` has `VERSION = 'v1'`.
- `shellCacheFirst` (`sw.js:65-67`) serves the cached JS and CSS (with `ignoreSearch`) for ever. Unless someone remembers to bump `VERSION`, fixes such as RT-02 and RT-03 never reach installed devices. No test enforces a bump.
- `api.js:42-43`: once `status.mode` is `'cache'`, a later live response does not set it back to `'live'`. The offline banner persists after connectivity returns, until the user presses "Try again".

**Recommended fix.** Derive `VERSION` from `APP_VERSION` or a build hash, and add a test that fails when shell files change without a version change. Use stale-while-revalidate for the shell. Reset `status.mode` to `'live'` on any non-cached success.

## RT-18 (LOW): "byte-identical" is a size comparison

`DATA_SOURCES.md:165-166` says provenance "was confirmed by comparing every file's byte size". `:174`, `:198`, `KNOWN_LIMITATIONS.md:7` and `paper/03_problem_data.tex:27` turn that into "byte-identical". **Fix:** say "identical file sizes", or compute and publish SHA-256 hashes for the downloaded release.

## RT-19 (LOW): wording and numbers in paper §3

- `03_problem_data.tex:41` says "Across all (market, commodity, variety, date) keys since 2023, none carries two grades on the same day". At that key there are **455** such keys. With state and district added there are 0, which is what the entity key uses.

```sql
SELECT count(*) FROM (SELECT market,commodity,variety,arrival_date FROM silver WHERE arrival_date>='2023-01-01' GROUP BY ALL HAVING count(DISTINCT grade)>1); -- 455
-- with state,district added: 0
```

- `:42` says "95–97% … APMC". Monthly shares were Dec 0.969, Jan 0.969, Feb 0.956, Mar 0.952, **Apr 2026 0.770**.
- `:47` says "monthly volume falls to roughly 20–35%". November 2025 has 32,927 reports against about 530k a month (about 6%). The claim holds for Dec–Apr only.
- `01_intro.tex:22,36` says "calibrated intervals" before any coverage result exists. Say "conformal intervals whose coverage we measure".
- Verified as correct against `panel_report.json` and DuckDB: 36 commodities (count), 33,116,234; 75,814; 117,623 (raw series with grade); 191; 28,567 (0.086%); 11,845; 21.06M; 75,644,801 silver rows; 97.6% VALID; 17.2–34.4% zero changes (EXPERIMENTS A.10, validation).

## RT-20 (LOW): the DM test HAC lag is too short

`forecast_report.py:89` uses `dm_test(d, max(1, H_DAYS[h]))`, so the lag is h, with `next` mapped to 1. The targets lie in [t+h, t+h+3], and `next` reaches up to 7 days, so daily loss differentials are autocorrelated beyond lag h. Lags also count observed dates, not calendar days. **Fix:** use lag = h+3 (7 for `next`), or a data-driven bandwidth, and report the sensitivity.

## RT-21 (LOW): selection and calibration reuse

- The conformal quantiles (`ForecastBenchmark.scala:209`) come from the same full validation set used to choose the winner (`:202-203`), so the calibration residuals of the selected model are slightly optimistic. Test coverage is measured, so this is disclosed by construction. Mention it anyway.
- The backtest fold 2024 is the validation year on which the GBT spec was chosen.
- `paper/04_method.tex:89` says the backtest uses "the selected configuration". The script picks the lowest-validation-MAE GBT for h7 (`run_forecast_pipeline.sh:15`), which may not be the selected model, and applies it to every horizon.

## RT-22 (LOW): `hdfs_verify.sh` bugs

- `:35`: `dfs -put -f /opt/agri-results` has no destination. It always fails and the failure is hidden by `|| true`, so results are never uploaded.
- `:33` crashes under `set -e` if `data/gold/meta.json` is absent, and the script never checks for it.
- `:32`: `/staging/gold/*` is glob-expanded by the host shell, where `/staging` does not exist. It only works if Hadoop globbing takes over.

## RT-23 (LOW): one record defines `data_as_of`

```
2026-04-21: 1 VALID row; 2026-04-20: 5,152; 2026-04-19: 4,820 …
```

`ForecastPublish.scala:47` sets `dataEnd = max(arrival_date)`. Every `days_old` is therefore shifted by one day, and that day's `cs_n = 1` feeds the cross-section. **Fix:** define `data_as_of` as the last day with at least X% of the trailing median volume.

## RT-24 (LOW): survivorship in training rows

`BuildForecastFeatures.scala:71-79` keeps only entities that report at least 300 days in 2021–23, and applies this to 2016–2020 training rows too. That conditions on future survival. It does not leak test information, but it biases the training distribution towards incumbent markets. Note it next to Limitation 9.

## RT-25 (LOW): ingestion details

- `datagovin.py:153-157` checks for key presence only (no types or dates).
- `:180-184`: one non-conforming record raises `SchemaChanged` and aborts the whole pull; `rejected` can never exceed 1.
- `:124-134` ignores `Retry-After` on 429.
- Offset pagination over a "Current Daily Price" resource that changes during the day can skip or duplicate records. Duplicates are absorbed by `event_id`; skips are not.
- Redaction is otherwise correct: `public_url` drops `api-key`, network errors are passed through `_redact`, and checkpoints store key-free URLs only.

## RT-26 (LOW): API details

- `app.py:129,185` returns the exception class name in `/ready`.
- `:212,227,247` uses ILIKE with unescaped `%` and `_` from the user. All values are bound, so there is no injection.
- The OpenAPI UI is public (`:120`).
- `test_mae_pct_of_price` is filled with WAPE (`:322`).
- `interval_coverage80_test` is the overall coverage, shown on every commodity card (`:324`, `commodity.js:73`).

## RT-27 (LOW): stale features are reused

`run_forecast_pipeline.sh:13` skips F1 whenever `data/forecast/features` exists, even if `Features.scala` changed. **Fix:** store the git commit and config hash in `panel_report.json` and rebuild on mismatch.

---

## Checked and found OK

- **Feature construction is causal and matches the docs.** I recomputed `ret1`, `dev30`, `std30`, `ly_dev`, `tday_h7` and `y_h7` from raw silver (harmonised, collision-ranked, ×5 jump rule over ROWS 10 preceding) for 40 random entities: **67,278 rows, 0 mismatches** on every column.
- **Target windows are as documented.** `tday − day` falls in [1,7] for next, [3,6] for h3, [7,10] for h7 and [14,17] for h14. There are no labels without a target day and no target day without a label.
- **No duplicate entity-days.** There are 32,515,229 rows and 32,515,229 distinct (entity_id, day).
- **No suspicious feature–target correlation.** On 2024 panel rows the maximum |corr| is 0.37 (`dev7` vs `y_next`), all negative mean-reversion signs as expected; `snaive_h7` vs `y_h14` is 0.27.
- **Purging works.** 74,110 validation-origin rows have h14 targets after 2024-12-31, and `periodFilter` (`ForecastBenchmark.scala:43`) excludes them. Training purge is the same.
- **Preprocessing is fitted on training rows only.** StringIndexer, OneHotEncoder and StandardScaler sit inside the Pipeline fitted on `trainS`. Null fill is a constant. The MASE scale comes from unsampled training rows only (`ForecastEval.scala:71-72`). The conformal bucket edges and quantiles come from validation only (`:97-109`).
- **Absolute-loss GBTs use a scaled label.** The label is scaled at fit time and the prediction is rescaled inside the pipeline, so the persisted model needs no label at serving time.
- **Seasonal frames end at least 348 days before the origin** (`Features.scala:149-156`).
- **The aborted logs print validation numbers only.** Before abort they contain only validation MAEs and the selection line (see RT-07 for what was computed but not printed).
- **The quality rules are equivalent** in Python `schema.classify` and Scala `DataQuality.classify`, including null handling.
- **The API uses bound parameters for every user string.** `LIMIT`/`OFFSET` are bounded ints, CORS allows GET only from an allow-list, the generic 500 handler hides details, and `nosniff` is set.
- **The ingest code never logs or stores the key.** It also checkpoints atomically (tmp + replace).
- **Silver foreachBatch overwrites `batch_id=N`,** so re-executing a batch is idempotent. Dedup by content hash `event_id` is the right key for exact re-sends.
- **The frontend tests pass** (53/53): XSS guard, offline cache semantics, i18n. All 264 keys are present in ta/te/ml/hi/kn; only 3 per language are identical to English (placeholders/proper nouns). There is a skip link, live regions, and an `aria-label` on the chart.
- **Python tests pass** (39/39).
- **The archive is not presented as live** in the API or app wording: `archive_data` warning, stale banner, `origin.*` labels. RT-03 and RT-16 are the exceptions noted.
- **Licensing is stated with UNVERIFIED markers** where it could not be confirmed (`DATA_SOURCES.md`). GODL attribution is carried in `meta.source`.
