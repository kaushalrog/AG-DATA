# Frozen-model future-window issuance v2

This is a local prospective collection protocol, not completed confirmation.
The existing prototype model fc_lgbm_2025 is an exploratory chosen model, not the smaller release-study fit. This collection cannot directly confirm the latter model. A successful
future evaluation could assess it forward in time; it would not retroactively make
historical selection independent or reproduce the original test population.

## Lock and issue

`PYTHONPATH=py .venv/bin/python -m agri.research.prospective lock`
copies boosters, category/feature metadata and calibration files into a new root,
records hashes, dependency versions, relevant preprocessing/issuance source and commit.
It refuses dirty locked source or an existing root. Do not edit locked source/artifacts
or upgrade dependencies in this run; begin a separately labelled protocol if needed.

`PYTHONPATH=py .venv/bin/python -m agri.research.prospective issue`
recomputes forecasts from frozen artifacts and current retained feature bytes, not
from unbound UI values. Each latest in-panel, known-commodity origin must precede the
local issue date by no more than two days, and its entire target window must start
strictly after issuance's Asia/Kolkata calendar date. No CLI timestamp override exists.
Thus next-report forecasts may be ineligible when issuance follows the origin date;
this is a declared future-window population, not all retrospective-origin rows.

The recorder fingerprints the feature files before/after computation, rejects future
observation dates, validates price/interval outputs, and atomically publishes a batch.
A local file lock serialises calls. A separately retained atomic HEAD record detects missing/truncated tail batches; manifest timestamps/counts are checked against retained rows and directory dates. Missing visible batch files fail closed. A crash between batch publication and HEAD update requires manual inspection rather than automatic reissuance. Existing (entity,origin,horizon) keys are skipped;
checksums and a previous-manifest chain detect modifications to retained batches.
Incomplete hidden staging directories do not become issued batches. The ledger is
not a distributed exactly-once or independently witnessed immutable storage system.
Feature-byte fingerprints cannot independently establish when every raw report became
public or certify the code that created the inputs. End-of-day same-day cross-market
availability remains an assumption requiring review.

## Evaluation and witnesses

`... prospective status` verifies the lock and retained ledger. At least 90 completed
calendar days, plus target maturation, are required before considering an evaluation.
No outcomes are scored by this collection utility, and no future success is assumed.
A separate reviewed scoring protocol must define first available official target,
revision vintage, missing targets, persistence comparator, stable population and
error/coverage metrics before reading accumulated outcomes. Never backcast missing
issuance dates. Report all missing/failed runs, horizon coverage and exclusions.

Timestamps use the local system clock. Hash chains and a public commitment to the
lock/first-batch hashes support later auditing but are not trusted external time
attestations or protection against an owner rewriting everything. Independent
archival/time witnessing and human statistical review remain pending. No scheduler,
cloud upload, data subscription or human outreach is installed by this change.

Production serving and refresh configuration are unchanged. Real collection requires
operators to refresh official data and invoke issuance; this session can only record
currently eligible future windows, not observe their outcomes or complete 90 days.

## Development-cohort boundary

The first v1 batch was captured before code review found insufficient tail-deletion
and timestamp-mutation checks. It is retained under data/prospective_v1 and marked
superseded before any target outcomes, not silently edited. The hardened v2 uses a
new root and lock; no model tuning or outcomes informed this change. Only v2 is the
active collection population. Verify v1 with its matching source commit 52d914d if
needed for forensic review. Do not pool the duplicate development batch into results.
