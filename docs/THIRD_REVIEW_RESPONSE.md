# Third-review response: smaller study made primary

The review offered two alternatives for Priority 1. **Option B is implemented**:
make the smaller clean-source study primary, with a bounded title, primary
introduction/design/methods/results and conclusions. The older national-scale
benchmark, mirror audit, timing studies and operational backtests are preserved in
`paper/historical_results.pdf` and its sources, explicitly as historical supporting
evidence. Their original full-size execution and panel construction are not certified.
The primary article does not claim to have reproduced that national-scale benchmark.

## Request-to-evidence mapping

| Priority | Response | Remaining limitation |
|---|---|---|
| 1 Scope and reproducibility | PASS for selected alternative: clean-source smaller study is primary; all principal primary tables use results/release_v1. Title states small-budget retrospective cleaning/dependence sensitivity. | Fixed panel remains an external input; exact large-input public archive and independent execution pending. |
| 2 Time-forward evidence | PARTIAL: model/calibration/source/dependency lock and future-window recorder implemented; active v2 batch contains 4,956 forecasts (1,652 each h3/h7/h14), first issued 2026-10-23T17:18:59.010819+00:00, earliest target 2026-10-24. Duplicate call returns NO_ELIGIBLE_NEW_FORECASTS. | NOT_EVALUATED; future outcomes and 90 completed days unavailable. Local clock/hash chain are not external attestation. No schedule installed. Locked prototype differs from smaller-study candidate. |
| 3 Human statistical review | Automated independent adversarial review and 8 real-booster/synthetic-input integrity tests completed. Long dependence/limited seasons/approximate coverage remain prominent. | Human expert sign-off not obtained; 2,000 replicates are not additional independent seasons. Evaluation is not extended into selection/calibration to manufacture more data. |
| 4 Practical metric meaning | PASS: abstract, design, a new generated scaled-metric table, discussion and conclusion foreground MASE ~1.00–1.11 versus training-period naive scales, 4.4–4.5% omissions, and the different contemporaneous-persistence relative-MAE denominator. | No universal market/benchmark superiority, price guarantee, profit or welfare claim. |

## Issuance development audit

v1 was captured before independent review found missing final-batch truncation and
manifest timestamp checks. It remains retained as a **superseded development cohort
before outcomes**. v2 adds a separately persisted atomic head, tail/file checks,
timestamp/count/model/target consistency, and midnight-publication quarantine.
All 4,956 predictions/intervals are numerically identical across the two cohorts;
no model tuning or observed target outcomes influenced the code hardening. Only v2
is active, so development duplicates must never be pooled into evaluation.

The raw batches/models remain outside Git. Compact exact-byte lock, first manifest,
head and cohort-transition commitments are in results/prospective_v2. Public
commitments do not prevent coordinated owner rewrites or prove raw report availability.
Manual intervention is required after a crash between batch publication and head
update; recovery fails closed rather than silently reissuing missing keys.

## Verification and artifacts

Python: **106 passed**, one deprecation warning. New module tests use explicitly
synthetic observations and actual tiny LightGBM boosters; they are not live evidence.
The real v2 batch uses retained official/archive feature data and frozen fc_lgbm_2025
artifacts, with observed system issuance time and future windows. No future scores.
Independent review verified v2 status and frozen-artifact equality, inspected ledger
fixes/tests and the new primary-paper claims; it did not claim human statistical review.

Reproduce the historical primary study using docs/RELEASE_PROTOCOL.md; regenerate
its tables with `python paper/build_release.py`. Recorder commands are in
PROSPECTIVE_PROTOCOL.md. The main manuscript retains ten numbered sections.

The archived release index at results/release_v1/RELEASE_INDEX.json describes PDFs
from tag agdata-research-release-v1, not newer editorial revisions. Current paper
checksums are tracked separately under results/manuscript_v3.

**Submission recommendation remains pending**, chiefly human statistical review,
independent reproducibility/data archival, verified author information and formal
journal compliance. No readiness rating or new model is added to satisfy appearance.
