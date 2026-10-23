# Known limitations

Written as facts about the current system. Each item says what it affects. Status labels: **BLOCKED** (needs an external resource), **OPEN** (could be done, not yet done), **BY DESIGN** (an accepted trade-off).

## Data
1. **No live data (BLOCKED).** No data.gov.in API key was available. The adapter is implemented and tested against labelled synthetic fixtures; it has never been run against the live endpoint. Everything the app shows comes from the archive ending **2026-04-21**, about six months before this report. The app labels it as a historical snapshot.
2. **The archive is a third-party mirror.** It is a Kaggle compilation (GODL-India per its description) of AGMARKNET data, matching v134 by file size (content hashes not compared). It has not been reconciled record by record against AGMARKNET itself.
3. **AGMARKNET 2.0 migration (Nov 2025).** Market names changed (" APMC" suffix) and monthly volume fell to 20–35% of its earlier level. The harmonisation rule is heuristic: a market renamed in any other way would still split into two series.
4. **Grade is dropped from the entity key.** This is justified by the data: no day has two grades for one series. If the source ever reports two grades for the same series on the same day, the rule keeps one of them.
5. **No arrivals (quantity) after 2024-02-02** and no weather features. Supply-side information is therefore absent from the models.
6. **Units are taken from the publisher's statement (INR/quintal).** No per-record unit field exists. The ×5 sanity rule removes about 0.09% of rows that look like unit or keying slips.
7. **Source revisions** cannot be detected in a one-off archive. The streaming design keeps revisions (new `event_id`), but this has only been exercised with replayed data.

## Forecasting
8. **Panel selection.** Training and headline evaluation cover the 11,845 series with ≥ 300 report days in 2021–2023, so results describe well-reported markets. Thinly reported markets get forecasts from the same global model, flagged with the `sparse_history` warning. Their accuracy is not established.
9. **The rolling-origin folds for 2021–2023 use a panel chosen with 2021–2023 reporting density.** This is selection of which series to score; no prices or labels are involved. It is recorded in the backtest output.
10. **Models are trained once (on data up to 2023) and applied up to 2026-04.** Monthly retraining was not evaluated.
11. **Conformal intervals assume exchangeability, which time series violate.** Coverage is measured on the test period and reported per horizon and volatility bucket. It is not guaranteed.
12. **The search space is small** (8 configurations per horizon) because of the laptop compute budget. No deep-learning model was trained (see ARCHITECTURE for why).
13. **Literature comparisons are indirect.** No prior study uses the same data, horizons and splits (docs/RESEARCH_GAP.md §5).

24. **Same-day cross-sectional features (`cs_*`, `sc_*`)** assume that every market's day-t report is known by the end of day t. AGMARKNET's publication lag was not measured. In live use, late-arriving reports would make these features differ from training (train/serve skew). The h7 ablation removing them is reported in EXPERIMENTS Part B.
25. **Batch backfill from bronze is a documented procedure, not an automated job.** No code yet reads `bronze/` or `silver/prices_stream` back into the batch silver layer (red-team RT-12).
26. **Selection and calibration share data.** The conformal quantiles are calibrated on the same 2024 validation set used to choose the model, which makes them slightly optimistic. Test coverage is measured, and the 2024 backtest fold is the validation year.

## Decision support
14. **SELL/HOLD/WATCH/COMPARE is a market outlook, not a profit recommendation.** Transport, commission, storage loss and the farmer's cash needs are unknown. Costs are placeholders that the farmer can edit. The farmer-impact literature (Fafchamps & Minten 2012; Mitra et al. 2018) suggests that price information alone often does not raise farm-gate prices.
15. **COMPARE uses administrative districts and states as a proxy for "accessible markets".** There are no distances or travel times.

## Systems
16. **Spark ran in local mode and as a Docker standalone cluster on one machine.** No multi-machine cluster was tested, so the scalability numbers are single-host numbers.
17. **HDFS has one NameNode (no HA).** DataNode loss with replication 3 is demonstrated. NameNode loss is not survivable.
18. **Kafka is a single broker (replication 1).** Broker loss loses unconsumed data. Kafka replication was not demonstrated.
19. **Streaming does not maintain rolling features.** Forecasts refresh only when the batch publish runs (see ARCHITECTURE).
20. **No public deployment.** No cloud credentials were available. No public URL exists.

## Application
21. **Not tested on a physical 4 GB Android phone.** Testing used desktop Chromium with mobile viewport emulation.
22. **Translations into Tamil, Telugu, Malayalam, Hindi and Kannada are AI-produced and provisional.** They need review by native speakers with agricultural vocabulary before use with farmers (`app/i18n/TRANSLATION_STATUS.md`).
23. **No usability study with farmers was carried out.**
