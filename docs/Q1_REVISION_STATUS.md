# Q1 review response and evidence

This revision does not claim Q1 acceptance readiness or superiority over prior work.
The candidate contribution is a matched-origin audit of source completeness and its
impact on multi-horizon price and interval evaluation, rather than a novel learner.

## Scientific status

* Historical scores and LightGBM adoption remain exploratory. Reusing an already
  examined period cannot provide independent confirmation.
* `docs/REVISION_PROTOCOL.md` locks separate training, selection, calibration and
  evaluation periods for a smaller retrospective robustness experiment. Production
  boosters and forecasts are preserved.
* The original dirty-code provenance cannot be repaired retrospectively. New model
  fitting uses clean commit `e7abad9`, exact input and output hashes and imported
  module locations. The unfiltered feature seal is a **post-build fingerprint**,
  not proof that those exact inputs and executable bytes produced the features.
  Its Scala builder was committed as `d624416`; assembly/build logs are retained.
* `results/revision_q1/superseded_d624416.json` is explicitly invalid and must not be
  cited: an earlier in-progress run had an incorrect seasonal-naive conversion.
* Exclusion audit: 18,775 of 14,098,524 valid in-scope reports were flagged (all
  commodities in the four shards, history from October 2022). A deterministic,
  nonrepresentative sample of 120 reports is retained in `exclusion_audit.json`.
  Large deviations and multi-day runs do not establish erroneous reporting. No
  manual error labels or causal effects are asserted.

## Independent confirmation still required

The earliest proposed future confirmation start is 2026-10-24. Freeze booster,
preprocessing and calibration hashes before issuance; archive each forecast with
its actual issuance time before its target; then score at least 90 completed days.
Do not backdate forecasts or label a backcast as an issued forecast. No such future
outcomes exist in this session; no future collector or schedule is claimed installed.

## Submission and field-review blockers

* Keep at most ten numbered manuscript sections; IEEE is generated from the same
  authoritative section sources as the IJF version.
* Reorganised related work synthesises comparability, source quality and uncertainty;
  it does not establish an unprecedented combination or new statistical theory.
* An anonymised review archive, release tag, verified corresponding-author details
  and final author declarations remain owner actions. No package is claimed supplied.
* The official IJF author guide returned HTTP 403 on the fresh check. Existing venue
  notes are not a substitute for checking current requirements before submission.
* Real Android/TalkBack, native-speaker and farmer reviews remain pending; browser
  emulation is not real-device validation.

## Reproduction

From the committed experiment source, run `scripts/revision_q1.sh`. It verifies a
sealed existing feature table or builds four shards before training. Partial builds
are never silently removed. See the protocol for exact dates and budgets. The
saved-prediction report command is `PYTHONPATH=py .venv/bin/python -m
agri.research.revision report`; it validates prediction hashes before recomputing
metrics. The manifest distinguishes completed runs from running/invalid ones.

## Completed checks

Robustness fitting completed in 222.6 seconds (feature build and hashing excluded).
All eight fits and five simple baselines are recorded in `results/revision_q1`.
Report generation rechecks saved prediction hashes and recomputes metrics,
statistical summaries, multiplicity corrections and common-origin metrics.
Python: 87 passed; app: 58 passed; Scala: 22 passed. Real headless Chrome
155: 15/15 PWA checks, including installability, service worker, offline reload,
six-language 320 px rendering and CPU/network throttling. Throttled first list
4.061 s / 70 KB; JS heap 4.69 MB (not a real 4 GB Android test).
