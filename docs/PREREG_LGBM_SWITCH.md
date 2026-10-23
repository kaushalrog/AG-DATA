# Pre-registered decision: should LightGBM replace the served model?

Written and committed **before** the LightGBM candidate was trained or scored (2026-10-23). The commit hash of this file is the timestamp.

## Candidate `fc_lgbm_2025`
* **Model.** Global LightGBM with an L1 objective, one model per horizon.
* **Inputs.** The same features and panel as `fc_retrain_2025` (`data/forecast_v3/features`, silver v2).
* **Configuration.**
  * Learning rate 0.05; min_data_in_leaf 200; feature_fraction 0.8; bagging 0.7 / 1. These are exactly as in `lgbm_baseline.py`.
  * Commodity is a categorical feature.
  * Training is one seed (1). A single booster is what would be served.
* **Train.** Origins 2016-01-01 .. 2024-12-31, with targets purged at 2024-12-31, on a uniform sample of 2,000,000 rows (seed 20261022).
* **Validation (2025).** Used only to choose `num_leaves` ∈ {63, 255} with early stopping (100 rounds, up to 3,000), and to fit the split-conformal intervals. The intervals use 5 Mondrian bins on `std30`, with edges at validation quintiles and residual quantiles 0.05 / 0.10 / 0.90 / 0.95. This is the same procedure as `ForecastEval.fitConformal`.
* **Final test.** 2026-01-01 .. 2026-10-22, scored once on rows identical to the frozen `fc_main_v3` and the retrained `fc_retrain_2025` predictions.

## Comparator
The currently served model is `fc_main_v3`, frozen with training data to 2023, scored on the same rows (`data/forecast_v3/test_predictions/fc_main_v3/final_test_2026`).

## Switch rule (all must hold)
1. **Primary, at the decision horizon h7.** LightGBM has lower MAE than `fc_main_v3`. The Diebold–Mariano test (daily mean absolute error difference, HLN correction, lag h+3) must give a two-sided p below 0.05 after a Holm correction over the four horizons.
2. **No harm.** At no horizon is LightGBM significantly worse (two-sided p < 0.05 with a positive mean difference).
3. **Calibration.** At every horizon, 80% interval coverage on the final test is within [75%, 85%] and no more than 2.0 points further from 80% than that of `fc_main_v3`.
4. **Operational.**
   * The candidate publishes through the normal refresh path and passes `validate_release`.
   * The published medians reproduce the offline candidate predictions for the same origin rows (maximum absolute difference in log return below 1e-9).

If any condition fails, `AGRI_SERVING_MODEL` stays `fc_main_v3`, and the candidate is reported as evaluated but not adopted.

## Known weaknesses of this test (disclosed in advance)
* The 2026 final test has already been used twice: to score the frozen models and to compare the retrained models. This is the third model scored on it. No LightGBM choice uses any 2026 data.
* January–April 2026 also belongs to the original `fc_main_v3` test period. April–October 2026 is the earlier frozen-model hold-out.
* The earlier LightGBM result on the `fc_main_v3` protocol (`lgbm_baseline.json`) is known. It motivated this test, so a positive outcome partly confirms an expectation already formed on overlapping data.
