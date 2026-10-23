# Response to the second supplied review

No readiness score is adopted or predicted. Recommendation remains **do not submit
this working draft yet**. See EVIDENCE_LEDGER.md for the precise evidence boundaries.

| Request | Status and concrete response |
|---|---|
| Clean, versioned execution | PASS for bounded study: source tag agdata-research-source-v1/e233b40; eight new shard builds; pre/post silver/panel/source/JAR checks; all commands exited zero; eight fits; principal release tables generated from checked predictions. PARTIAL overall: full-size historical principal tables and original panel selection were not reproduced. |
| Clarify LightGBM evidence | PASS: adoption explicitly exploratory; neither smaller study is independent confirmation or a new Spark comparison. Production configuration unchanged. |
| Statistical scrutiny | PASS automated adversarial review and implementation changes: effective days/rows/entities, 28/42/56-day circular and non-circular blocks (2,000 replicates), asymptotic HAC without HLN, ACF/count/loss plots, MASE exclusions, entity quantiles and state/commodity errors. PENDING human statistician; no validated coverage claim. |
| Empirical contribution and venue | PASS scope clarified: source-completeness audit changes drift-evaluation practice; no new learner or conformal method. IJF explicitly targeted, official IIF scope/author/reproducibility pages checked. Detailed linked guideline PDF is 404 and ScienceDirect is 403; formal template compliance remains pending. |
| Publication package | PARTIAL: local source archive/environment/checksums/manifests and Git version tags. Large input/model/prediction bytes remain local outside Git; no public immutable data archive, anonymised package, independent execution or journal submission claimed. |

## Actual evidence

`results/release_v1/TABLES.md`, manifest, build-pair check, build manifests and generated
LaTeX distinguish this reproduction from earlier results. Old results and the earlier
`paper/tables/revision_robustness.tex` remain unchanged. Reporting source cd1f786
repairs the table-isolation issue found in independent review; statistical methods
are unchanged from fitting source e233b40. Release tables have unique filenames.

Observed release-study MAE gains are 4.4–5.9% (INR 9.92–18.83/quintal). Subgroup
failures, dependence limitations and 4.4–4.5% MASE omissions are explicit. Independent
artifact review found no critical/high issues, checking prediction/feature checksums
and all 48 interval entries; it did not independently rerun every bootstrap or rehash
large silver inputs. This is AI-assisted verification, not human peer review.

Local tests after implementation: Python 98 passed (one deprecation warning), app 58
passed. Feature execution comprises eight real local Spark shard jobs, not a claimed
distributed cluster test. Saved commands can rerun in an appropriate environment.

## Reproduce

From a clean checkout with retained inputs: `scripts/reproduce_release.sh`. Existing
output roots are refused, never deleted automatically. For the exact fitting execution,
use source tag agdata-research-source-v1; that version's legacy table write is avoided
in later reporting code. Final release reporting: `PYTHONPATH=py .venv/bin/python -m
agri.research.revision report --output results/release_v1`, then
`.venv/bin/python paper/build_release.py` and `python3 paper/ieee/build_ieee.py`.
Compile in paper/ and paper/ieee/ with `tectonic -X compile main.tex`.

## Still needed

1. Full-size end-to-end replication of historical acceptance-critical tables, or
   removing them from acceptance-critical claims; the clean smaller study does not
   retroactively certify them.
2. Human expert statistical assessment, including long-run dependence/seasonality,
   target availability and transportability assumptions.
3. Immutable archival of exact large input bytes and an independent environment run.
4. Future-issued evaluation, verified author declarations/correspondence, formal
   journal template compliance and native-speaker/device/farmer field reviews.
