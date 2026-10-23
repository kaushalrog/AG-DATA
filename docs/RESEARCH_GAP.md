# AG-DATA — Literature Review and Research Gap

Status: working document, compiled 2026-10-22. BibTeX for every work cited here is in
[`paper/references.bib`](../paper/references.bib); citation keys are shown in `[brackets]`.

> **Ground rules used in this document**
> - Every paper listed was checked to exist: title, authors, year and venue were retrieved from
>   Crossref (`api.crossref.org/works/<DOI>`) and/or OpenAlex. For the two works without a DOI
>   (JMLR MLlib, NeurIPS adaptive conformal) the publisher page was retrieved.
> - "Reading depth" says what was actually read: **Full text** (methods section retrieved),
>   **Abstract** (only the abstract was retrieved), or **Metadata** (bibliographic record only;
>   the publisher blocked automated access to the abstract).
> - Numbers are quoted only where they appeared in text we retrieved. Otherwise the cell says
>   **not extracted**. Nothing in this file should be cited as a result unless the source is
>   re-checked by a human with full-text access.
> - Statements about *our* project are hypotheses to be tested, not claims.

---

## 1. Scope and search method

**Research question for the review.** What has been published on forecasting market-level (mandi)
prices of Indian agricultural commodities, how was it evaluated, and which parts of the AG-DATA
design (market-level daily data at national scale, chronological splits, naive/seasonal baselines,
multi-horizon targets, conformal intervals, anomaly flags, distributed processing, farmer-facing
decision cards) have prior work already covered?

**Themes covered.**
1. Indian agricultural price forecasting: TOP crops (tomato, onion, potato), pulses, oilseeds, AGMARKNET data.
2. Mandi-level ML/DL/hybrid models (ARIMA, ARMA-GARCH, TDNN, wavelet hybrids, SVR, RF, GBM, LSTM/GRU).
3. Reviews of agricultural price forecasting.
4. Distributed / big-data forecasting with Apache Spark.
5. Price volatility and excessive-variability early warning.
6. Forecast evaluation methodology (scaled errors, DM test, M competitions, time-series CV, pitfalls).
7. Conformal / distribution-free prediction intervals for time series.
8. Market-information interventions and farmer outcomes in India.

**Databases / APIs queried (2026-10-22).**
- Crossref REST API (`query.bibliographic=` and `works/<DOI>`), for metadata verification.
- OpenAlex API (`works?search=` and `works/doi:`), for discovery and abstracts.
- Semantic Scholar Graph API (heavily rate-limited; few results; publishers had removed abstracts for Springer titles).
- Europe PMC REST (full text of the open-access *Scientific Reports* paper).
- Publisher pages: PLOS ONE (full text), JMLR, NeurIPS proceedings. Springer and Nature landing pages blocked automated access.

**Queries used** (as typed). `onion price forecasting India`; `tomato price forecasting India`;
`potato price forecasting India`; `pulses price forecasting India`; `agricultural price forecasting India LSTM`;
`wavelet agricultural price forecasting India`; `mandi price forecasting`; `AGMARKNET price`;
`Paul Garai onion price forecasting wavelet`; `Jha Sinha time-delay neural network agricultural price forecasting India`;
`Sinha Jha Paul pulses price forecasting India`; `agricultural price forecasting Spark big data`;
`Agricultural commodity price forecasting review machine learning deep learning`;
`Excessive food price variability early warning system`; plus exact-title lookups for the
methodology, conformal and market-information papers named in the brief.

**Inclusion.** Peer-reviewed article, book chapter, proceedings paper or institutional report;
directly about (a) Indian agricultural price forecasting, (b) a method or evaluation practice used in
AG-DATA, or (c) the effect of price information on Indian farmers. **Exclusion.** Papers whose metadata
could not be verified; predatory-looking venues where no other evidence was available; non-price targets
(yield, production) unless the paper was otherwise central.

**Limits of this review.** It is a targeted, not a systematic, review (no PRISMA protocol, a single
reviewer, one day). Many Indian studies appear in journals not well indexed by OpenAlex/Crossref, so
coverage of that literature is incomplete. Paywalled methods sections (Springer, Wiley) could not be read,
which limits how sure we can be about split design and horizons in those papers.

---

## 2. Literature matrix (compact)

Legend. **Depth**: F = full text (methods) read, A = abstract only, M = metadata only.
**Split**: how train/test was formed, as stated in the text we saw. "n/s" = not stated in what we saw.

### 2a. Indian agricultural price forecasting

| Key | Year | Venue | Data / geography | Target & freq. | Horizon | Models | Split | Metrics | Reported result (seen) | Depth |
|---|---|---|---|---|---|---|---|---|---|---|
| `paul2022brinjal` | 2022 | PLOS ONE | AGMARKNET, 17 Odisha markets, 1 Jan 2015 – 31 May 2021 | Brinjal wholesale price, daily | Evaluation over the hold-out; one figure shows 30-step-ahead | ARIMA, GRNN, SVR, RF, GBM | 90 % / 10 %; chronology not stated in what we saw | ME, RMSE, MAE, MAPE; DM test; Model Confidence Set | GRNN best "in most of the cases"; numbers not extracted (Table 4 not read) | F (partial) |
| `paul2021wavelet` | 2021 | Soft Computing | not extracted | Agricultural commodity prices | not extracted | Wavelet-based ML | not extracted | not extracted | not extracted | M |
| `paul2025deep` | 2025 | ISAFM | Monthly wholesale, 19 commodities, 143 Indian markets, Jan 2010 – Dec 2022 | Monthly wholesale price | not extracted | RW with drift, ARIMA, ANN, SVR, RNN, LSTM, GRU | not extracted | "different accuracy measures"; DM and multivariate DM | DL beats ML and stochastic models; accuracy higher for cereals/pulses than vegetables | A |
| `jha2012tdnn` | 2012 | Neural Comput. & Appl. | India (oilseeds) | Monthly wholesale price | not extracted | TDNN vs linear | not extracted | not extracted | not extracted | M |
| `jha2013ann` | 2013 | Agric. Econ. Res. Review | India; soybean, rapeseed-mustard | Monthly wholesale price | not extracted | ANN, linear, linear+ANN hybrid | not extracted | Direction-of-change accuracy, others n/s | ANN captures more directions of change; hybrid more accurate on nonlinear series | A |
| `kumar2021onion` | 2021 | Indian J. Agric. Sci. | Varanasi market (UP), 2015–2020 | Onion price (seasonal period 52 → weekly) | not extracted | ARIMA(0,1,2)(1,0,0)[52], ARFIMA-sGARCH | not extracted | MAPE, MSE, RMSE, Theil's U | ARMA-GARCH outperformed ARIMA (no values seen) | A |
| `anjoy2017pulses` | 2017 | Indian J. Agric. Sci. | India, all-India WPI of pulses | Monthly WPI | Multi-step ahead | MODWT(Haar)-ANN vs ANN | not extracted | not extracted | Hybrid "significantly better" than ANN (no values seen) | A |
| `praveenkumar2024potato` | 2024 | Potato Research | not extracted | Potato price | not extracted | LSTM, Bi-LSTM, AM-LSTM | not extracted | not extracted | not extracted | M |
| `jaiswal2021lstm` | 2021 | Neural Comput. & Appl. | not extracted | Agricultural prices | not extracted | Deep LSTM | not extracted | not extracted | not extracted | M |
| `manogna2021spot` | 2021 | ISAFM | NCDEX spot; cotton seed, castor seed, rape-mustard, soybean, guar seed | Daily spot price | not extracted | ARIMA, TDNN, LSTM | "out-of-sample" (details n/s) | not extracted | LSTM best on directional movement | A |
| `manogna2025deep` | 2025 | Scientific Reports | AGMARKNET, 23 commodities incl. TOP, 165 markets, 26 Feb 2010 – 11 Jun 2024 | Daily wholesale price | not stated in sections searched | ARIMA, SVR, XGBoost, MLP, RNN, LSTM, GRU, ESN, LinReg | 80 % / 20 %, 1000-step sliding windows; chronology not stated in sections searched | RMSE, RNMSE, MAE, MAPE | Abstract: GRU RMSE 369.54 (onion), 210.35 (tomato); ARIMA 1564.62 / 1298.60; GRU MAPE 14.59 % onion, 10.58 % tomato. **Body text** gives GRU MAPE 16.17 % onion, 14.81 % tomato; ARIMA 92.66 % / 92.17 % | F (searched) |
| `manogna2025volatility` | 2025 | J. Big Data | 23 commodities, 165 markets, Feb 2010 – Jun 2024 | Price volatility | not extracted | LSTM-GARCH hybrid | not extracted | not extracted | Hybrid "significantly enhanced accuracy" (no values seen) | A |
| `vani2024top` | 2024 | Indian J. Agric. Econ. | All-India CPI/WPI sub-indices, Jan 2014 – Apr 2024 | CPI sub-index (TOP), monthly | not extracted | Autoregressive models | not extracted | MAPE | MAPE 4.58 % tomato, 2.02 % onion, 1.30 % potato | A |

### 2b. Reviews, big-data systems, volatility

| Key | Year | Venue | Type | What it covers | Relevance to AG-DATA | Depth |
|---|---|---|---|---|---|---|
| `sun2023review` | 2023 | Agriculture (MDPI) | Review | Traditional, intelligent and combination models for agricultural price forecasting | Background; recommends combined models and attention to trend direction as well as value | A |
| `rana2024bigdata` | 2024 | ETASR | Empirical | Pakistan, multi-city prices 2007–2022, Spark for preprocessing; ARIMA, RF, LSTM on spinach in one city (Vehari) | Closest "Spark + ag price" precedent; Spark used for cleaning only, modelling on one series. LSTM R² 0.8, MAE 125.29 (abstract) | A |
| `zaharia2016spark` | 2016 | CACM | System | Apache Spark unified engine | Platform citation | A |
| `meng2016mllib` | 2016 | JMLR | System | Spark MLlib | Platform citation for GBT/RF/linear models | A |
| `geng2021earlywarning` | 2021 | IFPRI report | Method / system | Excessive Food Price Variability Early Warning System; nonparametric CVaR/CES thresholds on daily returns; maize, wheat, soybeans with exogenous covariates | Closest precedent for our anomaly flags (international futures, not mandis) | A |

### 2c. Evaluation methodology and conformal prediction

| Key | Year | Venue | Contribution used by AG-DATA | Depth |
|---|---|---|---|---|
| `hyndman2006another` | 2006 | IJF | Scaled errors (MASE) relative to an in-sample naive forecast | M (well-known; abstract not returned by OpenAlex) |
| `diebold1995comparing` | 1995 | JBES | Test of equal predictive accuracy; works with non-quadratic loss and serially correlated errors | A |
| `makridakis2020m4` | 2020 | IJF | 100,000 series; included prediction-interval evaluation | A |
| `makridakis2022m5` | 2022 | IJF | Hierarchical retail series (Walmart); point-accuracy track | A |
| `bergmeir2018note` | 2018 | CSDA | Conditions under which K-fold CV is valid for purely autoregressive models | M |
| `cerqueira2020evaluating` | 2020 | Machine Learning | Empirical comparison of performance-estimation methods (holdout, CV, prequential) for time series | M |
| `hewamalage2022pitfalls` | 2022 | DMKD | Common flawed evaluation practices in ML forecasting and best practices | A |
| `xu2023conformal` | 2023 | IEEE TPAMI | EnbPI: distribution-free intervals for time series without exchangeability | A |
| `jensen2024encqr` | 2024 | IEEE TNNLS | Ensemble conformalized quantile regression for nonstationary, heteroscedastic series | A |
| `gibbs2021adaptive` | 2021 | NeurIPS | Adaptive conformal inference: long-run coverage under distribution shift | A |

### 2d. Market information and farmer outcomes (India)

| Key | Year | Venue | Setting | Design | Finding (from abstract) | Depth |
|---|---|---|---|---|---|---|
| `jensen2007digital` | 2007 | QJE | Kerala fisheries, 1997–2001 | Staggered mobile-phone rollout, micro survey data | Large fall in price dispersion, waste eliminated, welfare up for producers and consumers | A |
| `fafchamps2012sms` | 2012 | WBER | 100 villages, Maharashtra; Reuters Market Light SMS | Randomized experiment | Small effects; no statistically significant average effect on prices received | A |
| `goyal2010information` | 2010 | AEJ: Applied | Madhya Pradesh soy; ITC internet kiosks (e-Choupal) from Oct 2000 | Market-level panel | Significant rise in soy price and soy area after kiosks | A |
| `mitra2018asymmetric` | 2018 | REStat | West Bengal potato farmers | Randomized wholesale-price information | No average change in farmgate sales or prices; pass-through rose | A |

---

## 3. Per-paper notes

**`paul2022brinjal`** — Paul, Yeasin, Kumar, Kumar, Balasubramanian, Roy, Paul, Gupta (2022), *PLOS ONE* 17(7):e0270553, doi:10.1371/journal.pone.0270553.
Uses AGMARKNET daily brinjal prices for 17 Odisha markets (2015–2021). Compares ARIMA with GRNN, SVR,
RF and GBM, and uses the Diebold–Mariano test and Model Confidence Set, which is better practice than
most of the field. *Limitations seen:* a 90/10 split without a stated rolling origin; no naive or
seasonal-naive benchmark; no prediction intervals; one crop, one state; a separate model per market.
Reading: methods read through the publisher page; Table 4 values not extracted.

**`paul2021wavelet`** — Paul & Garai (2021), *Soft Computing* 25(20):12857–12873, doi:10.1007/s00500-021-06087-4.
Wavelet-decomposition + ML comparison from the ICAR-IASRI group. Metadata only (abstract withheld by
the publisher via API, landing page blocked). Data, horizon and results not extracted.

**`paul2025deep`** — Paul, Yeasin, Tamilselvi, Paul, Sharma, Birthal (2025), *ISAFM* 32(1):e70002, doi:10.1002/isaf.70002.
The broadest Indian benchmark found: 19 commodities × 143 markets, monthly, 2010–2022. It includes
**random walk with drift** as a baseline and uses DM and multivariate DM tests. It finds accuracy depends
on how volatile the commodity is (vegetables are hardest). *Limitations (from the abstract):* monthly
frequency, which is coarser than daily mandi decisions; split design and horizon not visible; intervals not mentioned.

**`jha2012tdnn`** — Jha & Sinha (2012/2014), *Neural Computing and Applications* 24(3–4):563–571, doi:10.1007/s00521-012-1264-z.
TDNN for monthly oilseed wholesale prices. Metadata only.

**`jha2013ann`** — Jha & Sinha (2013), *Agricultural Economics Research Review* 26(2):229–239, doi:10.1177/0971344120130208.
Monthly soybean and rapeseed-mustard prices. ANN captures more directions of change than linear models,
and a linear+ANN hybrid helps on nonlinear series. Notably, it frames the model as a *decision-support
system*, an early precedent for the farmer-facing part of AG-DATA. Abstract only.

**`kumar2021onion`** — Kumar, Badal, Paul, Jha, Venkatesh, Kamalvanshi, Anbukani, Balasubramanian, Patel (2021), *Indian J. Agric. Sci.* 91(2):249–253, doi:10.56093/ijas.v91i2.111603.
A single market (Varanasi), 2015–2020. ARMA-GARCH beats ARIMA on MAPE, MSE, RMSE and Theil's U. A typical
single-market study. Abstract only.

**`anjoy2017pulses`** — Anjoy, Paul, Sinha, Paul, Ray (2017), *Indian J. Agric. Sci.* 87(6):834–839, doi:10.56093/ijas.v87i6.71022.
MODWT (Haar) + ANN for multi-step forecasts of the monthly all-India pulses WPI. The target is an index,
not a mandi price. Abstract only.

**`praveenkumar2024potato`** — Praveenkumar, Jha, Madival, Lama, Kumar (2024), *Potato Research* 68(2):1941–1963, doi:10.1007/s11540-024-09823-z.
Compares LSTM, Bi-LSTM and attention-LSTM for potato prices. Metadata only.

**`jaiswal2021lstm`** — Jaiswal, Jha, Kumar, Choudhary (2021), *Neural Computing and Applications* 34(6):4661–4676, doi:10.1007/s00521-021-06621-3.
Deep LSTM for agricultural prices (ICAR-IASRI). Metadata only.

**`manogna2021spot`** — Manogna & Mishra (2021), *ISAFM* 28(1):72–83, doi:10.1002/isaf.1487.
Daily NCDEX **spot** prices (exchange, not mandi) for five non-perishables. LSTM is best on direction. Abstract only.

**`manogna2025deep`** — Manogna, Dharmaji, Sarang (2025), *Scientific Reports* 15:20903, doi:10.1038/s41598-025-05103-z.
The closest data match to AG-DATA: daily AGMARKNET prices for 23 commodities (including TOP) across 165
markets, 2010–2024. What the full text says (keyword search of the Europe PMC full text, PMC12215695):
an 80/20 train/test split with 1000-step sliding windows; metrics RMSE, RNMSE, MAE and MAPE. The authors
say they **considered MASE and Theil's U and chose not to use them**. No naive/persistence baseline was
found in the sections searched. *Internal inconsistency:* the abstract gives GRU MAPE 14.59 % (onion) and
10.58 % (tomato), while the body gives 16.17 % and 14.81 %. The ARIMA MAPE of about 92 % is implausibly
high for a correctly specified one-step benchmark, which points to a multi-step or level-mismatch setup;
we could not confirm which. How series from different markets are combined could not be determined from
the sections searched.

**`manogna2025volatility`** — Manogna, Dharmaji, Sarang (2025), *Journal of Big Data* 12:85, doi:10.1186/s40537-025-01131-8.
LSTM-GARCH for volatility on the same 23-commodity/165-market data. Relevant to our anomaly flags. Abstract only.

**`vani2024top`** — Vani, Verma, Singh, Shrivastav (2024), *Indian J. Agric. Econ.* 79(3):394–406, doi:10.63040/25827510.2024.03.005.
Forecasts all-India CPI sub-indices for TOP crops (Jan 2014 – Apr 2024) with low MAPE (1.3–4.6 %). The
target is a smooth national index, so these MAPEs are **not comparable** to mandi-level price errors.
Useful seasonality facts (onion and potato peak in November, tomato in July). Abstract only.

**`sun2023review`** — Sun et al. (2023), *Agriculture* 13(9):1671, doi:10.3390/agriculture13091671. General review. Abstract only.

**`rana2024bigdata`** — Rana, Farooq, Kazi, Baig, Akhtar (2024), *ETASR* 14(1):12652–12658, doi:10.48084/etasr.6468.
Uses Spark for preprocessing a multi-city price dataset from Pakistan, then models one commodity in one
city. Shows that "big data" in this literature usually means ingestion and cleaning at scale, not
training and evaluation at scale. Abstract only.

**`zaharia2016spark`, `meng2016mllib`** — Platform references (CACM 59(11):56–65, doi:10.1145/2934664; JMLR 17(34):1–7).

**`geng2021earlywarning`** — Geng, Hernandez, Martins-Filho (2021), IFPRI, doi:10.2499/p15738coll2.134592.
Describes IFPRI's Food Security Portal tool, which flags "excessive" daily price variability against an
estimated quantile threshold (nonparametric CVaR/CES). It covers international maize, wheat and soybean
markets. Abstract only.

**Methodology (`hyndman2006another`, `diebold1995comparing`, `makridakis2020m4`, `makridakis2022m5`, `bergmeir2018note`, `cerqueira2020evaluating`, `hewamalage2022pitfalls`).**
These are the evaluation standards we use: scale-free errors relative to naive forecasts (MASE), formal
tests of equal accuracy (DM), large-scale benchmarks against simple baselines and with interval
evaluation (M4/M5), and guidance on when CV is or is not valid for time series and on common ML
evaluation mistakes. Bergmeir et al. and Cerqueira et al. were verified through metadata only; the claims
attributed to them here are the well-known framing given by their titles, so check the text before
quoting specifics.

**Conformal (`xu2023conformal`, `jensen2024encqr`, `gibbs2021adaptive`).** Three routes to
distribution-free intervals for non-exchangeable, shifting series: bootstrap-ensemble residuals (EnbPI),
conformalized quantile ensembles (EnCQR), and online alpha-adaptation (ACI). None of the Indian
agricultural price papers found here uses any of them.

**Market-information impact (`jensen2007digital`, `goyal2010information`, `fafchamps2012sms`, `mitra2018asymmetric`).**
The evidence is mixed. Large effects appear where information lets producers reach a different market
(Kerala fishermen, e-Choupal kiosks with a direct buyer). Small or no average price effects appear where
farmers get price information but face the same middlemen (RML SMS in Maharashtra, potato farmers in West
Bengal). Implication for AG-DATA: a forecast or SELL/HOLD card is not expected to raise farmer prices by
itself, so any welfare claim needs a field evaluation.

---

## 4. Synthesis: common weaknesses in the prior work

These are patterns across the papers above. Each is qualified by how deeply we read the paper.

1. **Split design is unclear or not shown to be leak-free.** Where we saw the split, it was a single
   proportional hold-out (90/10 in `paul2022brinjal`; 80/20 in `manogna2025deep`). We did not see the
   word "chronological" or a rolling-origin evaluation in the sections we read. Feature scaling or
   window construction before splitting is a known leakage route (`hewamalage2022pitfalls`); we could not
   verify whether it happened. Treat this as *unverified risk*, not proven leakage.
2. **Single-market or small-panel studies dominate** (`kumar2021onion`; one city in `rana2024bigdata`;
   17 markets of one state in `paul2022brinjal`). The multi-market exceptions (`paul2025deep`: 143
   markets, monthly; `manogna2025deep`: 165 markets, daily) still model far fewer markets than AGMARKNET contains.
3. **Weak or missing simple baselines.** ARIMA is the usual "baseline". A naive/persistence benchmark was
   seen only in `paul2025deep` (random walk with drift). `manogna2025deep` explicitly decided against
   MASE. M4/M5 show that simple baselines are hard to beat (`makridakis2020m4`, `makridakis2022m5`), so
   leaving them out can inflate apparent gains.
4. **Scale-dependent metrics across heterogeneous series.** RMSE/MAE in ₹/quintal are averaged or compared
   across commodities with very different price levels. MAPE is unstable near low prices.
   `hyndman2006another` recommends scaled errors instead.
5. **Little statistical testing outside the ICAR-IASRI group.** DM / MCS appear in `paul2022brinjal` and
   `paul2025deep`, but not in the other abstracts we saw.
6. **No uncertainty quantification.** None of the Indian price-forecasting papers reviewed reports
   prediction intervals, let alone checks their coverage. The conformal literature (`xu2023conformal`,
   `jensen2024encqr`, `gibbs2021adaptive`) has not been applied in this domain, as far as we found.
7. **Horizon is often unstated.** Most abstracts do not say whether results are one-step or h-step,
   which makes comparison impossible.
8. **No deployment or scalability evaluation.** "Big data" appears as data volume or Spark preprocessing
   (`rana2024bigdata`), not as end-to-end distributed training, scoring and serving across thousands of
   market-commodity series.
9. **Little farmer-facing explanation or decision framing.** `jha2013ann` proposes a decision-support
   system, but none of the papers turns forecasts plus uncertainty into actions (sell/hold) or tests them
   with users. The impact studies show that information alone often fails to move prices.
10. **Anomaly / spike detection is separate from forecasting.** Early warning exists for international
    commodity returns (`geng2021earlywarning`) and volatility modelling exists for Indian prices
    (`manogna2025volatility`), but we found no mandi-level system combining point forecasts, intervals
    and anomaly flags.

---

## 5. Comparability rules

Prior results are **not directly comparable** to AG-DATA unless **all** of the following match:

1. **Same data source and target**: AGMARKNET mandi-level *modal* price, not min/max price, CPI/WPI
   index, NCDEX spot, or a national average.
2. **Same aggregation and frequency**: daily (or our observation cadence) at market × commodity
   (× variety) level, not monthly or weekly averages.
3. **Same horizon definition**: next observation, t+7 days, t+14 days, as defined in our pipeline.
4. **Same split protocol**: chronological train/validation/test with the same cut-off dates, no shuffling,
   and features computed only from the past.
5. **Same metric definition**: same formula (e.g. MAPE vs sMAPE; MASE scaling period), same handling of
   zeros and outliers, same averaging (per-series mean vs pooled).
6. **Same series set**: same markets, commodities and date range, or a documented overlapping subset.

If any rule fails, a prior number may be quoted only as **context**, with the reason it is not
comparable. In particular:
- `vani2024top` MAPE (1–5 %) is for national CPI indices, so it cannot be compared with our mandi MAPE.
- `manogna2025deep` RMSE/MAPE come from an 80/20 hold-out of unclear horizon and aggregation, and the
  paper reports two inconsistent sets of MAPE values. Context only.
- `paul2025deep` is monthly. Context only.

To make real comparisons possible, AG-DATA should, where feasible, **re-run comparable baselines on our
own splits** (e.g. naive, seasonal naive, ARIMA on a sample of series) rather than compare against
published numbers.

---

## 6. Candidate contributions (hypotheses to be tested, not claims)

Each hypothesis says what evidence would support or refute it. None is claimed as true yet.

- **H1 — Baseline honesty.** On chronological test splits, a good share of mandi-commodity series will
  *not* show significant gains of GBT/RF over seasonal-naive or moving-average baselines at the
  next-observation horizon, while gains will be larger at 7 and 14 days.
  *Test:* MASE per series against naive and seasonal naive; DM test with a multiple-testing correction;
  report the fraction of series where the model wins.
- **H2 — Calibrated uncertainty.** Split-conformal (or adaptive-conformal) intervals on top of Spark
  MLlib models reach close to nominal coverage (e.g. 80/90 %) on the chronological test period, and
  coverage falls in volatile periods unless an adaptive method is used.
  *Test:* empirical coverage and mean width, by commodity and by period, compared with
  `gibbs2021adaptive`-style adaptation.
- **H3 — Scale.** One distributed pipeline (Spark/HDFS) can train, evaluate and score all eligible
  market × commodity series from about 76M rows within a bounded wall-clock budget, which single-series
  studies do not attempt.
  *Test:* report runtimes, cluster configuration and series counts. This is an engineering
  contribution, not a methodological one.
- **H4 — Breadth of evaluation.** Evaluating across thousands of mandi series rather than 1–165 markets
  will show heterogeneity (by crop group, market size, data sparsity) that single-market studies cannot
  see, consistent with `paul2025deep`'s volatility finding.
  *Test:* stratified error distributions; check whether vegetables (TOP) have higher MASE than cereals and pulses.
- **H5 — Integrated anomaly flags.** Flags derived from forecast residuals and interval exceedance
  identify known price-spike episodes (e.g. onion spikes) earlier than or as well as a simple
  return-threshold rule.
  *Test:* event-based precision/recall against a hand-labelled list of spike episodes. Requires a
  labelled list, which we do not have yet.
- **H6 — Decision usefulness.** SELL/HOLD/WATCH/COMPARE cards built on intervals improve a simulated
  farmer's realised price compared with "always sell now" in back-tests. Real-world welfare effects are
  **not** claimed, given `fafchamps2012sms` and `mitra2018asymmetric`.
  *Test:* back-tested decision rule with transaction/transport costs. Any field claim would need a user study.

### Strongest defensible gap statement (draft)

> Among the Indian agricultural price-forecasting studies we reviewed, none jointly (i) evaluates
> mandi-level daily modal prices across all AGMARKNET markets, (ii) uses strictly chronological splits
> with naive/seasonal baselines and scale-free metrics (MASE) at several horizons, and (iii) reports
> calibrated, distribution-free prediction intervals. AG-DATA is designed to test whether doing all
> three, at scale, changes the conclusions drawn from smaller studies.

This statement is limited to the papers reviewed here (Section 2) and should be rephrased as "to our
knowledge" in any publication.

---

## 7. Comparison table template

Fill in from our experiment logs. Leave "reported value" as the paper's own number with its units, and
fill "comparable?" using the rules in Section 5.

| paper | data | horizon | metric | reported value | comparable? | note |
|---|---|---|---|---|---|---|
| `manogna2025deep` | AGMARKNET daily, 23 commodities, 165 markets, 2010–2024 | not stated in sections searched | MAPE (GRU, onion) | 14.59 % (abstract) / 16.17 % (body) | No | Inconsistent values; 80/20 hold-out; aggregation unclear |
| `manogna2025deep` | same | same | RMSE (GRU, onion / tomato) | 369.54 / 210.35 (abstract) | No | Scale-dependent; units ₹/quintal assumed, not confirmed |
| `paul2022brinjal` | AGMARKNET daily, 17 Odisha markets, 2015–2021, brinjal | hold-out (10 %) | RMSE / MAPE | not extracted | No | Different split and market set. Brinjal is among our 36 commodities: our h7 rel. MAE for brinjal is in `results/forecast/fc_main_v3/test_by_commodity_h7.csv` |
| `paul2025deep` | Monthly wholesale, 19 commodities, 143 markets | not extracted | various | not extracted | No | Monthly frequency |
| `kumar2021onion` | Varanasi onion 2015–2020 | not extracted | MAPE, RMSE, Theil's U | not extracted | Possibly, for one market only | Re-run on our split if Varanasi is in our data |
| `vani2024top` | All-India CPI sub-indices | not extracted | MAPE | 4.58 % / 2.02 % / 1.30 % (T/O/P) | No | Index, not mandi price |
| `rana2024bigdata` | Pakistan, spinach, Vehari | not extracted | MAE / R² | 125.29 / 0.8 (LSTM) | No | Different country and commodity |
| AG-DATA (ours, measured) | AGMARKNET mandi modal, 36 commodities, 11,845 series; test 2025-01..2026-04 | next / 3 d / 7 d / 14 d | MAE ₹/q (rel. to persistence) | 183.5 (0.971) / 231.1 (0.953) / 289.7 (0.938) / 366.4 (0.923) | — | Chronological purged split, validation 2024; `results/forecast/fc_main_v3/` |
| AG-DATA (ours, measured) | same | same | WAPE; 80 % interval coverage | 5.6 / 7.0 / 8.8 / 11.1 %; 78.6 / 79.4 / 80.0 / 80.5 % | — | WAPE is not MAPE: do not compare with the MAPE values above |
| AG-DATA (ours, measured) | 400 random panel series | same | rel. MAE of per-series SES vs global model | 0.975 vs 0.976 / 0.962 vs 0.960 / 0.967 vs 0.946 / 0.975 vs 0.935 | — | Tests H1: ML adds nothing over SES at 1–3 days |

**Hypotheses after the experiments.**
* **H1: supported.** Learned models beat persistence and SES only modestly, and most clearly at 7–14 days.
* **H2: partly supported.** Coverage is near nominal overall and across volatility bins, but falls to 68–73% after the Nov 2025 source change.
* **H3: supported as an engineering result.** Single-host evidence is in `docs/EXPERIMENTS.md` Part C.
* **H4: supported.** Gains vary by commodity (rel. MAE 0.88–0.97 at h7) and by period.
* **H5: not testable.** There is no labelled spike list; injected corruptions were used instead.
* **H6: back-test only.** HOLD/SELL hit rates of 68–80% on about 1.5% of report-days. No farmer-welfare claim is made.

---

## 8. Verification log and unverified items

- **Verified with DOI via Crossref (30):** all entries in `references.bib` except `meng2016mllib`
  (verified on jmlr.org) and `gibbs2021adaptive` (verified on proceedings.neurips.cc, plus arXiv DOI
  via OpenAlex).
- **Abstract withheld / landing page blocked (metadata only):** `paul2021wavelet`, `jha2012tdnn`,
  `praveenkumar2024potato`, `jaiswal2021lstm`, `hyndman2006another`, `bergmeir2018note`,
  `cerqueira2020evaluating`. Do not cite specific results from these until the full text has been read.
- **Searched for but not included:**
  - A peer-reviewed SARIMA/XGBoost study on daily mandi TOP prices with a clearly chronological split.
    Several 2024–2026 single-market papers in regional journals turned up
    (e.g. Kolar and Karnataka tomato, Anugul onion), but they were not verified in enough depth to include.
  - An ICAR-IASRI pulses *mandi* price forecasting paper. Only the pulses WPI paper (`anjoy2017pulses`)
    and a pulses market-integration paper (Paul, Saxena, Bhat 2016, AERR, doi:10.5958/0974-0279.2016.00035.5;
    metadata seen, not included because it is about integration, not forecasting) were found.
  - Darekar & Reddy (2017) "Price forecasting of pulses: case of pigeonpea", *Journal of Food Legumes*:
    found in OpenAlex with no DOI. Volume and pages not verified, so it is not included.
