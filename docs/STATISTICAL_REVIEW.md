# Automated independent statistical-method review (2026-10-23)

Reviewer: separate adversarial AI agent, read-only review of source, manifests and
saved predictions. This is **not human expert statistical sign-off**. The reviewer
computed descriptive daily-loss autocorrelations without training models or changing
files. An independent statistician familiar with dependent forecast panels remains
required before submission.

## Findings and response

1. **High: long-range dependence.** In prior cleaned h7 results, daily-loss ACF was
   .285 at lag 14, .227 at lag 28 and .215 at lag 56. The original HAC bandwidth 10
   and block lengths 14/28 do not cover that visible dependence. ACF is descriptive;
   drift, panel exposure or seasonality may contribute and challenge stationarity.
   Response: retain original output with a legacy label; add all 28/42/56-day HAC
   bandwidths and circular/non-circular blocks with 2,000 replicates. Do not choose
   the sensitivity giving the smallest p-value or claim nominal coverage validated.
2. **Medium: HLN horizon/bandwidth conflation.** The old helper uses its bandwidth as
   the HLN horizon. Actual target gaps are irregular, so no standard fixed-horizon
   correction is established. Response: secondary release diagnostics use asymptotic
   normal HAC tests with no HLN claim. Original values are historical heuristics.
3. **High: block-bootstrap assumptions.** Circular wrapping creates artificial
   end-to-start adjacency; 14 days is shorter than the longest target window and
   roughly ten 28-day spans do not supply many independent seasons. More replicates
   improve Monte Carlo precision, not dependence validity. Response: long-block and
   non-circular sensitivities, approximate conditional wording, daily loss/count and
   ACF diagnostics. No interval is advertised as a validated confidence guarantee.
4. **Medium: entity resampling.** Entities share markets, commodities and regional
   shocks. Independent entity resampling cannot justify inference to independent new
   markets. Response: label exploratory entity-resampling sensitivity; show direct
   entity-ratio quantiles and commodity/state summaries. Do not combine temporal and
   entity intervals into a two-way robustness claim.
5. **Sampling unit and multiplicity.** Prior fits had 281–294 calendar days, not
   half a million independent observations. Same-day aggregation preserves the joint
   observed cross-section; residual dependence remains. Holm controls the declared
   family only if component p-values are valid; it cannot repair dependence or
   historical model-selection reuse. Response: report days/rows/entities together;
   lead with observed rupee and proportional effects, not tiny p-values.
6. **MASE population.** About 4.4–4.5% of earlier evaluation rows lacked positive,
   finite training scales. Response: disclose exact release exclusions per fit.
   MASE and pooled MAE do not necessarily cover identical populations.

## Supported versus unresolved

Observed pooled MAE reductions in these historical samples are descriptive facts.
They do not establish causal cleaning effects, calibrated inferential coverage,
future performance, benefit in every market, farm profit or welfare. Disjoint
selection/calibration reduces reuse but does not make observations independent.
Two cleaning regimes share most observations and are not independent replications.
The new statistical specifications were chosen after this review of prior results;
they are explicitly retrospective sensitivities, not independent confirmation.
