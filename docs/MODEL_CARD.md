# Model card: AG-DATA mandi price forecaster `fc_main_v3`

## Model details
* **What it predicts.** The modal price (INR/quintal) that a mandi will report for a commodity–variety. Horizons:
  * **next:** the next report, if it falls within 7 days;
  * **h3, h7, h14:** the first report dated in [t+h, t+h+3].
* **Models.** One Spark MLlib pipeline per horizon, selected on 2024 validation MAE:
  * next and h3: gradient-boosted trees with absolute loss, trained on the log return in percent (depth 7, 150 iterations, step 0.5);
  * h7 and h14: random forest (60 trees, depth 10, subsample 0.5).
* **Target.** Log return from the last report, ŷ. The forecast is P₀·exp(ŷ).
* **Uncertainty.** 80% and 90% split-conformal intervals with five volatility bins, calibrated on 2024 residuals.
* **Artifacts.** `data/forecast/models/fc_main_v3/<horizon>/<family>`, with manifest `results/forecast/fc_main_v3/manifest.json`. Code version: see `git_commit` in the manifest.
* **Authors.** The AG-DATA project team (see README).

## Intended use
* A **market outlook** for farmers, extension workers and researchers: a likely range of the next published modal prices for a market they can reach, with the measured accuracy shown alongside.
* Research on forecasting methodology for mandi prices.

## Out of scope
* **Not a financial or trading instruction**, and not a guarantee of any price.
* Not the farm-gate price an individual farmer will receive.
* Not for markets or commodities outside the 36 forecast commodities. The API then returns `supported=false`.
* Not for live decisions while the data is a historical archive: the app returns WATCH with `forecast_expired`.

## Training data
* AGMARKNET daily reports (Kaggle archive v134, GODL-India):
  * 36 commodities, quality `VALID` only;
  * identifiers harmonised (grade is not part of the key; the " APMC" suffix is removed);
  * ×5 sanity rule applied.
* Training origins 2016–2023, from 11,845 panel series (≥ 300 report days in 2021–23).
* A random sample of 2 M rows per horizon. Details: `docs/DATA_DICTIONARY.md`, `docs/EXPERIMENTS.md` A.1–A.3.

## Evaluation (test period 2025-01-01 .. 2026-04-21, scored once)

| Horizon | MAE ₹/q (selected / persistence) | Rel. MAE | WAPE | 80% coverage | Series where it beats persistence |
|---|---|---:|---:|---:|---:|
| next | 183.5 / 189.0 | 0.971 | 5.6% | 78.6% | 58.5% |
| h3 | 231.1 / 242.6 | 0.953 | 7.0% | 79.4% | 68.8% |
| h7 | 289.7 / 308.8 | 0.938 | 8.8% | 80.0% | 75.0% |
| h14 | 366.4 / 397.0 | 0.923 | 11.1% | 80.5% | 76.4% |

* Diebold–Mariano tests against persistence give p < 1e-9 at every horizon.
* After the AGMARKNET 2.0 migration (Nov 2025 on), the gains shrink (relative MAE 0.94–0.99) and 80% intervals cover only 68–73%.
* Per-commodity and per-state breakdowns are in `results/forecast/fc_main_v3/test_by_*`.

## Decision support
The rule (`conf/decision_rules.json`) is evaluated on the 7-day horizon:

| Precedence | Condition | Output |
|---|---|---|
| 1 | Unsupported series | WATCH |
| 2 | Forecast expired | WATCH |
| 3 | Stale report | WATCH |
| 4 | lo80 ≥ today·(1 + cost) | HOLD |
| 5 | hi80 ≤ today | SELL |
| 6 | A fresh market ≥ 5% higher after transport | COMPARE |
| 7 | Otherwise | WATCH (`uncertain`) |

The holding cost is cost = 1% + 5%/week for perishables, 1%/week for durables. These are placeholders the farmer can edit.

Backtest at h7 on the test period:
* HOLD on 0.5% of report-days, with an 80.0% hit rate;
* SELL on 1.0%, with a 67.8% hit rate;
* WATCH on 98.5%.

HOLD signals concentrate on unusually low reports that then revert. COMPARE is not back-tested. The same rule is implemented in the API, the app and the Spark backtest, and all three are tested against `conf/decision_fixtures.json`.

## Limitations and risks
* **Coverage of the panel.** Results describe well-reported mandis. Thinly reported series get forecasts with a `sparse_history` warning, and their accuracy is unknown.
* **Sensitivity to the source.** Accuracy and coverage degrade when the publishing system changes (Nov 2025). Re-calibrate after any source change.
* **Same-day cross-market features** assume timely publication of other markets' reports.
* **Training age.** The models were trained once, on data to 2023, and have not been retrained since.
* **Translations** of the explanations are provisional.
* Full list: `docs/KNOWN_LIMITATIONS.md`.

## Ethical considerations
* Uncertainty and the age of the data are always shown, and the default card is WATCH.
* No personal data is used.
* The literature finds that price information alone often does not raise farm-gate prices (Fafchamps & Minten 2012; Mitra et al. 2018). Impact on farmers has not been studied for this system.
