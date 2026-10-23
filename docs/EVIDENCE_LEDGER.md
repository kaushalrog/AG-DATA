# Evidence classes for the revised manuscript

| Class | Files | What is established | What is not established |
|---|---|---|---|
| Historical analyses | `results/forecast/fc_main_v3`, `fc_retrain_2025`, `fc_lgbm_2025` | Saved metrics/artifacts, historical comparisons, operational adoption | Exact original dirty-code feature build; independent confirmation; entire full-size rerun |
| First retrospective sensitivity | `results/revision_q1` | Clean fitting source e7abad9, prediction-checksum reproduction, separate calibration | Original cleaned-feature build; pre-build executed artifact attribution |
| Clean-source release study | `results/release_v1`, source tag `agdata-research-source-v1` | Both variants rebuilt from same retained silver/panel bytes with pre/post source/JAR/input checks; same bounded 2024-training experiment | Full-size 2016–2023 MLlib replication; historical panel reconstruction; external independent execution; public archival availability of all large input bytes |
| Statistical sensitivity | Release manifest plus `docs/STATISTICAL_REVIEW.md` | Conditional effect estimates, explicitly retrospective bandwidth/block sensitivities, subgroup errors, dependence diagnostics | Proven nominal inferential coverage; independent markets; stationarity; human statistical approval |
| Confirmation | None | No claim | Future-issued scoring and independent held-out seasons remain unavailable |

The LightGBM serving decision is exploratory. The release does not re-evaluate all
Spark alternatives or independently confirm LightGBM superiority. Two cleaning
variants sharing data are sensitivity analyses, not independent replications.

## Reproduction boundary

The source archive, environment inventory, checksums, build records, model/prediction
manifests and commands are local release artifacts. Large retained input and model
files stay outside Git. A person with these exact input bytes can rerun the commands;
API access alone does not guarantee the same historical bytes after source revisions.
A public immutable archive of large inputs (with licensing/access review), and a
separate-environment reproduction, remain required for a journal reproducibility
package. No GitHub Release or anonymised journal package is claimed published.

## Editorial boundary

IJF is the explicit empirical forecasting/evaluation target, not a guarantee of fit
or acceptance. The IIF official author page was accessible on 2026-10-23; it requests
replicable methods/data, computer code, and PDF/EPS figures and encourages an
elsarticle template. Its linked detailed guideline PDF returned 404; ScienceDirect
returned 403. The article/IEEE renderings remain working drafts rather than certified
journal-template compliance. Author declarations and corresponding-author details
need verification. No submission is authorised or claimed.
