# Clean-source release reproduction protocol v1

This protocol is committed before new outputs exist. The release reruns the smaller
2024-training robustness experiment from raw-to-features boundaries, not the full
2016–2023 historical MLlib experiment. Its results cannot repair the original dirty
execution record or establish independent forecast confirmation.

* Rebuild both cleaned and unfiltered features from the same silver v2 and fixed
  historical panel input, history October 2022 onward, same four commodity shards.
* Hash silver and panel Parquet, tracked implementation/configuration, shard lists,
  and actual assembled JAR **before** starting each build. Capture executed commands,
  explicit environment overrides, start/end times, exit codes and runtime versions.
* Verify inputs/source/JAR unchanged before each shard and after completion; bind
  resulting feature checksums and all shard reports. Refuse partial or existing roots.
  No historical feature bytes are reused. The fixed panel itself remains a declared
  external input; we do not claim its original selection process was reproduced.
* Fit and evaluate the exact protocol in REVISION_PROTOCOL.md: 2024 training,
  Jan–Jun 2025 selection, Jul–Dec 2025 calibration, Jan–Oct 22 2026 evaluation;
  unchanged seed, two leaf settings, 500k training rows, eight fits, five baselines.
* Recompute principal **release-study** tables from saved predictions, retain original
  historical and earlier robustness outputs separately. Do not call the new study a
  full-size replication or confirmatory evaluation. No serving-model switch.
* Source and results release tags are local version markers, not GitHub-published
  releases. Do not move a tag once created. A source archive plus dependency and
  artifact manifests will be produced. Large/private API-key inputs are excluded.

Statistical assumptions are reviewed separately. Neither a very large number of
reports nor an AI-assisted code/method review provides human statistical sign-off.
Genuinely future-issued scoring and independent domain-statistician review remain
pending. No neural architecture is added.

Run: `scripts/reproduce_release.sh`. It uses isolated `data/release_v1_*`,
`data/release_v1` and `results/release_v1` paths, preserving production and prior runs.

## Retrospective statistical sensitivity amendment

The automated review inspected prior results and found positive daily-loss ACF beyond
28 days. Therefore these choices are explicitly post-hoc sensitivity analysis, not
pre-registered independent tests: circular and non-circular moving blocks of 28,
42 and 56 days, 2,000 replicates; asymptotic normal HAC diagnostics at bandwidths
28/42/56 without an HLN horizon correction. Holm is applied to each eight-fit
bandwidth family separately; no winning bandwidth is selected. Original 14/28-day
intervals and HLN heuristic are retained with explicit legacy labels. Report days,
row and entity counts, ACF, daily loss/count plots, MASE exclusions, entity-level
ratio quantiles and state/commodity summaries, including unfavorable results.
These estimates remain conditional on fixed fitted models/panel and require weak
stationarity/adequate dependence approximation; none has validated nominal coverage.
Independent-series resampling is exploratory, not proof of market generalisation.
