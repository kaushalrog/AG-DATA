# Journal choice and novelty audit (AG-DATA 2.0)

Date of check: **2026-10-23**. Scope: where to submit the forecasting paper, how to structure it, and which
claims hold up against prior work. Every measured number below comes from `docs/EXPERIMENTS.md`
(Parts B–D). The 2016–2024 retraining (`fc_retrain_2025`) has completed: no measurable gain over the frozen models (VERIFIED_METRICS §4).

**Verification labels**
- **VERIFIED**: read on the publisher, indexer or Crossref page given.
- **VERIFIED (index)**: the publisher page returned HTTP 403 to every automated client. The statement comes
  from the search engine's extract of that official URL and should be re-checked by hand before submission.
- **UNVERIFIED**: not confirmed, with the reason.

**How the sources were checked**
- ScienceDirect "Guide for authors" pages and forecasters.org returned HTTP 403 to `WebFetch`, `curl` and the
  in-app browser.
- Scope text was read on `shop.elsevier.com`.
- Quartiles were read on scimagojr.com (SJR 2025). JCR/Clarivate quartiles were **not** checked (paywalled).
- Journal of Big Data guidelines were read in full on link.springer.com.
- Citations were checked against Crossref `api.crossref.org/works/<DOI>`, with OpenAlex used for search and
  abstracts. Semantic Scholar returned HTTP 429 and was not used.

---

## 1. Candidate journals

SJR quartiles are for the **2025** edition (scimagojr.com journal pages, ids in the table). All of them are
**VERIFIED**.

| Journal | SJR 2025 | SJR categories (2025 quartile) | Scimago id |
|---|---:|---|---|
| Computers and Electronics in Agriculture (CEA) | 2.165 | Agronomy & Crop Sci. Q1; Animal Sci. Q1; Computer Sci. Applications Q1; Forestry Q1; Horticulture Q1 | 30441 |
| International Journal of Forecasting (IJF) | 2.272 | Business & International Management Q1 | 22706 |
| Expert Systems with Applications (ESWA) | 1.939 | Artificial Intelligence Q1; Computer Sci. Applications Q1; Engineering (misc.) Q1 | 24201 |
| Agricultural Systems | 1.606 | Agronomy & Crop Sci. Q1; Animal Sci. Q1 | 15061 |
| Journal of Big Data (JBD) | 1.964 | Computer Networks Q1; Hardware & Architecture Q1; Information Systems Q1; Info. Systems & Mgmt Q1 | 21100791292 |
| Food Policy | 2.011 | Development Q1; Economics & Econometrics Q1; Food Science Q1; Mgmt/Monitoring/Policy Q1; Sociology & Pol. Sci. Q1 | 35048 |
| Information Processing in Agriculture (IPA) | 1.240 | Agronomy Q1; Animal Sci. Q1; Aquatic Sci. Q1; Computer Sci. Applications Q1; Forestry Q1 | 21100804573 |
| Applied Soft Computing | 1.456 | Software Q1 | 18136 |
| Smart Agricultural Technology (CEA companion) | 1.169 | Agri. & Bio. Sci. (misc.) Q1; AI Q1; Computer Sci. (misc.) Q1 | 21101111783 |

### 1.1 Computers and Electronics in Agriculture

Guide: https://www.sciencedirect.com/journal/computers-and-electronics-in-agriculture/publish/guide-for-authors (403).
Scope: https://shop.elsevier.com/journals/computers-and-electronics-in-agriculture/0168-1699 (VERIFIED).

**Scope (VERIFIED).** Computer hardware, software, electronics and control applied to agriculture.
- The journal stresses "novelty and innovation" and whether a paper advances the state of the art.
- Applying existing technology to a new crop "does not qualify".
- Work that uses off-the-shelf tools is sent to *Smart Agricultural Technology*.
- **Datasets (VERIFIED).** Prototyping on previously published datasets is "preliminary". Authors are expected
  to collect a more rigorous dataset under controlled conditions.

**Fit for us.** This dataset rule is a direct risk, because our data are public AGMARKNET records.

**Article types (VERIFIED).** Original papers, reviews, application notes.

**Requirements**
- **VERIFIED (index):**
  - abstract ≤ 250 words;
  - highlights: 3–5 bullets, ≤ 85 characters each, supplied as a separate file;
  - application notes ≤ 4 printed pages.
- **UNVERIFIED:**
  - the full-paper length limit (not in any extract);
  - whether a graphical abstract is mandatory (the guide has a section on it, but the extract was cut off).

**Prior price-forecasting papers in CEA.** An OpenAlex search (ISSN 0168-1699, 2018+, "agricultural price
forecasting") found almost none. The closest is a corn yield and price study driven by satellite data
(doi:10.1016/j.compag.2024.108962).

### 1.2 International Journal of Forecasting

Guide: https://www.sciencedirect.com/journal/international-journal-of-forecasting/publish/guide-for-authors (403).
Scope: https://shop.elsevier.com/journals/international-journal-of-forecasting/0169-2070 (VERIFIED).

**Scope (VERIFIED).**
- "All aspects of forecasting", with an explicit welcome for machine learning, big data forecasting and the
  effect of forecast uncertainty on decisions.
- Strong emphasis on "empirical studies, evaluation activities, implementation research".
- Replication studies are encouraged.
- Review is double-blind.

**Article types (VERIFIED).** Research papers, research notes, discussion articles, book reviews, editorials,
letters.

**Data and code policy**
- **VERIFIED (index), forecasters.org/ijf:** since July 2023, sharing data and code is mandatory unless the
  Editor-in-Chief accepts a reason. Acceptance is conditional on passing a reproducibility check.
- **VERIFIED (Crossref):** a 2026 editorial on the policy exists: Pinson et al., "Editorial: Reproducibility
  at the International Journal of Forecasting", doi:10.1016/j.ijforecast.2026.08.004. We did not read its
  text.

**Requirements**
- **VERIFIED (index):** abstract of 100–150 words, with no references, jargon or mathematical notation.
  Highlights and graphical abstract are listed "where applicable".
- **UNVERIFIED:**
  - word or page limits (not in any extract);
  - the number of keywords (a third-party site says ≥ 5);
  - the highlights character limit for IJF.

**Prior agricultural work in IJF (VERIFIED).**
- Agricultural commodity price forecasting: Wang et al. 2022, doi:10.1016/j.ijforecast.2019.08.006.
- Real-time (vintage) databases: FRED-SD, Bokun et al. 2023, doi:10.1016/j.ijforecast.2021.11.008.

### 1.3 Expert Systems with Applications

Guide: https://www.sciencedirect.com/journal/expert-systems-with-applications/publish/guide-for-authors (403).

**Requirements**
- **VERIFIED (index):** abstract ≤ 250 words; highlights encouraged.
- **UNVERIFIED:**
  - the length limit (only a user post claiming 9,000 words was found);
  - the highlights character limit.

**Prior work (VERIFIED, OpenAlex).** ESWA publishes agricultural price forecasting, for example
doi:10.1016/j.eswa.2020.114232 and doi:10.1016/j.eswa.2025.129822.

**Fit.** Acceptable, but ESWA rewards new algorithms. Our contributions are about evaluation and data, not a
new model.

### 1.4 Agricultural Systems

Scope: https://shop.elsevier.com/journals/agricultural-systems/0308-521X (VERIFIED).

**Scope (VERIFIED).**
- Discouraged: "Econometric, descriptive, or other statistical analyses that exclude systems considerations".
- Also discouraged: economic analyses without substantive natural-science content.

**Requirements (VERIFIED, index).**
- Abstract ≤ 250 words, structured with headings.
- Graphical abstract required.
- Recommended maximum of 8,000 words for research papers and 4,000 for short communications.

**Fit.** Poor. A price-forecasting paper has no biophysical system component.

### 1.5 Journal of Big Data

Guidelines: https://link.springer.com/journal/40537/submission-guidelines and `/research-articles`.
Everything here is **VERIFIED**.

- **Open access.** APC £1440 / $2290 / €1990. Waiver requests must be made at submission.
- **Review.** Single-anonymous.
- **Research article.**
  - Abstract of 150–250 words; 3–10 keywords.
  - Main text with free subsections.
  - A list of abbreviations.
  - A mandatory "Declarations" block: ethics, consent, *Availability of data and materials*, competing
    interests, funding, authors' contributions, acknowledgements.
- **Datasets.** Public datasets must be cited with persistent identifiers.
- **LLM use.** Must be documented in Methods.
- **Prior work.** JBD has published AGMARKNET work: Manogna et al. 2025, doi:10.1186/s40537-025-01131-8.

**Fit.** Good, and an easy route for the Spark/streaming platform. It is a lower-prestige outlet for
forecasting methodology.

### 1.6 Food Policy

Scope: https://shop.elsevier.com/journals/food-policy/0306-9192 (VERIFIED).

**Scope.** Every paper must contribute to international food-policy debates. Methodological articles are
accepted if they are accessible to that readership.

**Prior work (VERIFIED, Crossref).** It has published ML food-price-inflation forecasting: Yan et al. 2026,
doi:10.1016/j.foodpol.2026.103077.

**UNVERIFIED.** Length limits (guide page returned 403).

**Fit.** Only if the paper were reframed around policy, for example the reliability of AGMARKNET as public
price information. Not the current paper.

### 1.7 Others

**Information Processing in Agriculture.**
- Scope: agricultural information processing (sensors, IoT, remote sensing). Published by China Agricultural
  University with Elsevier.
- It has published price forecasting: coffee price, doi:10.1016/j.inpa.2021.07.003.
- **UNVERIFIED:** guide details (403).

**Applied Soft Computing.** SJR Q1 (Software). **UNVERIFIED:** guide details (403). Algorithm-focused, so a weak
fit.

---

## 2. Recommendation

**First choice: International Journal of Forecasting, article type "Research paper".**

Why IJF:
1. **Our contributions are about forecast evaluation**, not a new learner:
   - which loss to use when the target has mass at zero;
   - honest benchmarks (persistence and SES);
   - DM tests;
   - calibration of conformal intervals;
   - how the data vintage or provenance distorts the evaluation;
   - prospective scoring of frozen models.

   This is exactly IJF's stated emphasis on "evaluation activities". It also extends a literature IJF
   already publishes: real-time data vintages (FRED-SD), intermittent-demand error measures (Kolassa 2016,
   doi:10.1016/j.ijforecast.2015.12.004), and the M4/M5 benchmarks.
2. **IJF's mandatory data, code and reproducibility check helps us.** The pipeline is scripted, the seeds are
   fixed, and the official data can be re-downloaded.
3. **CEA's dataset clause works against us.** CEA treats prototyping on published datasets as preliminary.
   Its scope is hardware and computing for farm operations, and an OpenAlex search found few price-forecasting
   papers there.
4. **Agricultural Systems and Food Policy are out of scope** for a pure forecasting paper (section 1).

**Fallbacks**
- **Journal of Big Data**, Research article. Keep the Spark, Kafka and HDFS evidence in the main text.
- **ESWA.**

**IJF format checklist**
- Abstract of 100–150 words with no maths or citations.
- Anonymised manuscript and a separate title page (double-blind).
- Data and code package ready for the reproducibility check.
- Highlights and graphical abstract only if the submission system asks for them.
- **Before submission:** re-check the length limit and the keyword count by hand. Both are UNVERIFIED.

### 2.1 Manuscript outline (10 top-level sections)

1. **Introduction.** The farmer and policy need; why mandi prices are hard (sticky re-quotes, a fragmented
   panel, data that changes under you). Contributions C1–C5 (§4). Most of the platform (PWA, Kafka) does not
   belong here.
2. **Related work.**
   - Indian mandi price forecasting (`docs/RESEARCH_GAP.md` table).
   - ML vs statistical benchmarks (M4/M5, Makridakis 2018).
   - Point-forecast scoring and zero-inflated targets (Gneiting 2011, Kolassa 2016).
   - Real-time data and vintages (Croushore & Stark 2001, FRED-SD).
   - Conformal prediction for prices.
3. **Data and provenance audit (F4, F5).**
   - AGMARKNET and the data.gov.in resources.
   - The Kaggle mirror v134 vs the official record: 30.0% coverage between Oct 2025 and Apr 2026; 100%
     containment; 99.33% identical modal prices.
   - Identifier drift (grade relabel, " APMC" suffix, "Keralam", spacing before "(").
   - Panel construction: 11,845 series, 36 commodities.
4. **Task and evaluation protocol.**
   - Horizons: next report, 3, 7 and 14 days.
   - Purged chronological splits and the scored-once test.
   - Metrics: MAE, relative MAE, MASE, WAPE.
   - DM test with HLN correction and daily-averaged differentials.
   - The prospective protocol, fixed in advance (A.10 amendment).
5. **Methods.**
   - Baselines: persistence, moving average, seasonal naive, seasonal-adjusted persistence, per-series SES.
   - Global MLlib models: ridge, Huber, RF, GBT, and GBT with absolute loss.
   - Feature groups, including same-day cross-market features and their availability assumption.
   - Split-conformal with Mondrian volatility bins.
6. **Point-forecast results (F1, F2).**
   - Share of zero changes and its effect on the squared- vs absolute-loss ranking.
   - Main table.
   - Per-commodity and per-series wins.
   - SES parity at 1–3 days.
   - Ablation.
7. **Interval calibration and the data-provenance effect (F3, F4).**
   - Coverage overall and by volatility bin.
   - Mirror vs complete data before and after the AGMARKNET 2.0 migration: the apparent shift and its
     disappearance.
8. **Prospective evaluation of frozen models (F6).** Six months of official data, April–October 2026. Add the
   2016–2024 retraining results here **only after they exist**.
9. **Decision-rule back-test, discussion and limitations (F7).**
   - SELL/HOLD/WATCH hit rates and abstention.
   - Not farm-gate profit.
   - Threats to validity: single seed, cross-section timing, reporting errors, MASE scaling.
10. **Conclusions.** Plus the mandatory statements: data and code availability, CRediT, declaration of
    generative-AI use, competing interests.

The platform (HDFS, Spark cluster, Kafka, PWA) goes into an online appendix or supplement, not the main text.

---

## 3. Novelty check

**Databases searched.** OpenAlex `works?search=` (titles, abstracts, citations), Crossref `works/<DOI>`
(verification), web search (Google-type index), plus direct pages on arXiv and link.springer.com.

**Queries run (OpenAlex unless noted)**
- "AGMARKNET price forecasting"
- "mandi price forecasting machine learning India"
- "agricultural commodity price forecasting India wholesale market"
- "price stickiness agricultural wholesale zero price changes"
- "zero-inflated price changes forecasting loss function"
- "intermittent demand mean absolute error zero forecast"
- "conformal prediction agricultural price"
- "conformal prediction commodity price forecasting intervals"
- "Mondrian conformal prediction regression"
- "Kaggle dataset incompleteness data quality machine learning"
- "dataset provenance spurious distribution shift"
- "mirror dataset incomplete official data replication discrepancy"
- "data vintage real-time data forecast evaluation"
- "backfill revisions epidemic forecasting evaluation"
- "AGMARKNET data quality"
- "Agmarknet arrivals prices data errors missing"
- "prospective evaluation forecasting models frozen out-of-sample agriculture"
- "large-scale panel price forecasting thousands of markets machine learning global model"
- "statistical and machine learning forecasting methods concerns ways forward"
- "farmer storage sell decision price forecast value backtest"
- "forecast value decision rule abstain prediction interval selling crops"
- "price rigidity food prices India markets"
- "Diebold Mariano agricultural price forecasting India machine learning benchmark naive"
- Web search: "AGMARKNET Kaggle … incomplete … data.gov.in comparison"
- Web search: "conformal prediction intervals mandi prices India AGMARKNET"

All DOIs below resolved on Crossref on 2026-10-23, except the arXiv DOI, which was checked on OpenAlex.

### C-F1. Zero-inflated price changes and the choice of loss

**Prior work**
- **Gneiting (2011)**, "Making and Evaluating Point Forecasts", *JASA* 106:746–762, doi:10.1198/jasa.2011.r10138.
  Under absolute error the optimal point forecast is the median; under squared error it is the mean.
- **Kolassa (2016)**, *IJF* 32:788–803, doi:10.1016/j.ijforecast.2015.12.004. For intermittent (zero-heavy)
  series, MAE rewards forecasts that are biased toward zero.
- **Price-stickiness literature**, for example Nakamura & Steinsson (2008), *QJE* 123:1415–1464,
  doi:10.1162/qjec.2008.123.4.1415. This is about retail and consumer prices; we found no paper on zero
  changes in mandi modal-price reports.

**How ours differs**
- The theory is not new. When 17–34% of changes are exactly zero, the conditional median change is often zero,
  so persistence is close to MAE-optimal.
- What is new is the empirical consequence at national scale in this domain. Squared-loss learners (ridge
  1.002, DM p = 0.47; RF 0.997, p = 0.28) do not beat persistence at the next report, while absolute-loss GBT
  does (0.971).
- The model-selection consequence is also documented: under a squared-loss-only search space, validation
  selects persistence.

**Defensibility: moderate** as an applied finding; **weak** if presented as a methodological discovery. Present
it as "a known decision-theoretic result with large practical consequences that the mandi literature ignores".

### C-F4. A spurious distribution shift caused by an incomplete public mirror

**Prior work**
- **Real-time data and vintages:**
  - Croushore & Stark (2001), *J. Econometrics* 105:111–130, doi:10.1016/s0304-4076(01)00072-0;
  - Bokun et al. (2023), FRED-SD, *IJF* 39:279–297, doi:10.1016/j.ijforecast.2021.11.008.

  Both show that the data vintage changes forecast evaluations.
- **Epidemic backfill:** Tang et al. (2025), *PLOS Comput. Biol.* 21:e1013709, doi:10.1371/journal.pcbi.1013709.
- **Data quality in ML:**
  - Sambasivan et al. (2021), "Data Cascades", CHI, doi:10.1145/3411764.3445518;
  - Gebru et al. (2021), "Datasheets for datasets", *CACM* 64:86–92, doi:10.1145/3458723;
  - Kapoor & Narayanan (2023), *Patterns* 4:100804, doi:10.1016/j.patter.2023.100804.
- **AGMARKNET data quality:**
  - Jain et al. (2020), arXiv, doi:10.48550/arxiv.2009.04171: manual entry errors and missing days, 2 crops,
    14 markets, quality features;
  - Guo et al. (2020), AAAI, doi:10.1609/aaai.v34i08.7039: imputation of missing AGMARKNET entries.
- **Not found:** any audit of a public AGMARKNET mirror against the official record, or any paper showing that
  a mirror's incompleteness creates an apparent drop in calibration or accuracy.

**How ours differs**
- We have a record-level comparison of the mirror and the official data.
- We show that an apparent shift reverses: coverage of 67.6–72.9% on the mirror becomes 78.0–78.7% on the
  complete data.
- The mechanism is identified: missing reports make series artificially sparse, and the "next" reports end up
  further apart.

**Defensibility: strong**, provided that:
- the mechanism analysis is in the paper (gap-length distributions on mirror vs official data);
- it is framed as a vintage or provenance effect, in line with the real-time-data literature, not as
  "first ever".

Caveats:
- This is one mirror and one migration event.
- "Widely used" needs evidence: Kaggle download or usage counts, or citing papers, checked by hand.
  **UNVERIFIED.**

### C-F5. Identifier drift

**Prior work.** Generic entity-resolution and data-cleaning literature. We found nothing specific to AGMARKNET.

**How ours differs.** This is a documented, dated catalogue of the drift and its measured effect: 187,264
same-day collisions.

**Defensibility: weak as a stand-alone contribution.** Keep it as a supporting part of C-F4.

### C-F6. Prospective evaluation of frozen models at national mandi scale

**Prior work**
- Prospective, real-time evaluation is standard in epidemic forecasting: Cramer et al. (2022), *PNAS* 119,
  doi:10.1073/pnas.2113561119.
- The M-competitions evaluate on unseen future data.
- Indian mandi studies use retrospective hold-outs, for example the 80/20 split in Manogna et al. (2025),
  doi:10.1038/s41598-025-05103-z. The 2026 MSP study (Balantrapu et al., doi:10.18805/ag.d-6567) uses a
  27-month hold-out of monthly All-India prices.
- **Not found:** an evaluation of frozen models on mandi data published after development ended.

**How ours differs**
- The models were trained to 2023 and fixed. They were scored on April–October 2026 official data, which did
  not exist during development.
- Rel. MAE 0.963 / 0.955 / 0.958 / 0.952; DM p ≤ 1e-15.
- 80% coverage 76.9–80.1%.

**Defensibility: moderate–strong.** Weaknesses:
- It is one six-month window.
- Training ended in 2023, so there is a 2.3-year gap.
- The protocol amendment (A.10) was written on 2026-10-22, before the test metrics were read, but there was no
  external pre-registration.

### C-F2. ML ≈ SES at 1–3 days, ML better at 7–14 days

**Prior work**
- Makridakis et al. (2018), *PLOS ONE* 13:e0194889, doi:10.1371/journal.pone.0194889: statistical methods
  often match or beat ML.
- M4/M5 (in `paper/references.bib`): global ML models win on large related panels.

**How ours differs.** This confirms those patterns in a new domain. The cross-market ablation (0.944 → 0.960
without cross-section features) explains where the gain comes from.

**Defensibility: weak as novelty; strong as honesty.** Present it as a confirmation that makes the paper
credible, not as a contribution.

### C-F3. National-scale conformal intervals for mandi prices

**Prior work**
- Ouyang & Tang (2026), "Drift-Aware Conformal Prediction for Reliable Potato Price Forecasting", *Potato
  Research* 69, doi:10.1007/s11540-026-10049-4. Weekly potato prices in 25 Chinese provinces, 2012–2018 (abstract
  read).
- Pinitjitsamut (2026), SSRN, doi:10.2139/ssrn.6731997: adaptive conformal for agricultural and metal
  commodities. Abstract not available.
- Ma et al. (2019), ICTD, doi:10.1145/3287098.3287100: heuristic nearest-neighbour price intervals on AGMARKNET,
  more than 1,000 markets. Coverage is not reported in the abstract.
- Mondrian conformal regression is established: Johansson et al. (2015), LNCS, doi:10.1007/978-3-319-17091-6_22.

**Correction.** `docs/RESEARCH_GAP.md` gap #6 ("conformal … has not been applied in this domain") is now
**outdated** for agricultural prices in general. As far as we found, it still holds for Indian mandi prices.

**How ours differs.**
- Daily, market-level data for 11,845 series in India.
- Coverage of 78.6–80.5% at a nominal 80% on the test.
- Coverage by volatility bin.
- Coverage under a data-provenance change and prospectively.

**Defensibility: moderate.** The method is standard (split-conformal with Mondrian bins); the scale and the
stress tests are what is new. Do not claim "first conformal for agricultural prices".

### C-F7. Decision-rule back-test

**Prior work**
- Ma et al. (2019) motivate when and where to sell, but do not back-test a decision rule.
- Madaan et al. (2019), COMPASS, doi:10.1145/3314344.3332488: forecasting and anomaly (hoarding) detection for
  onion and potato.
- The impact studies in `paper/references.bib` (Jensen 2007; Fafchamps & Minten 2012; Goyal 2010) cover
  information, not forecast-driven rules.
- **Not found:** an abstaining SELL/HOLD back-test on interval forecasts for mandis.

**How ours differs.** A conservative rule built on calibrated intervals, with an abstain share and hit rates.

**Defensibility: weak.**
- WATCH is about 98% of report-days.
- HOLD signals concentrate on anomalously low reports, which may be reporting errors.
- The results are not farm-gate profits.
- There is no economic baseline (for example "always hold for h days"), no transaction or storage costs, and
  no users.

Keep it as an illustrative section.

---

## 4. Novelty statement and claims to avoid

### 4.1 Novelty statement (for the cover letter and introduction; revised 2026-10-23 against VERIFIED_METRICS)

> **Primary novelty: evaluation validity under data provenance (F4 + F6).** To our knowledge, this is the
> first study to show, at national mandi scale, that an incomplete public mirror of AGMARKNET is enough
> to manufacture an apparent post-migration distribution shift and loss of interval calibration. The mirror
> holds 30% of official reports after October 2025. On the complete official record, the same frozen models
> lose only 1.2–2.2 coverage points (68–72% against 79–80% on identical rows). We identify the mechanism (median report gaps of 3 days against 1) and
> pair the audit with a post-development hold-out: six months of official reports first downloaded after the
> models were saved.
>
> **Supporting findings.**
> * The scoring function decides whether learners beat persistence when 17–34% of changes are exactly zero.
>   This is an application of Gneiting (2011), not new theory.
> * Retraining on two further years gave no measurable gain on a final period not used for any retraining choice (DM p 0.12–0.99).
> * A global LightGBM beats the deployed MLlib model. The benchmark therefore separates what the evaluation
>   protocol changes from what the model class changes.

Must stay hedged:
* "to our knowledge";
* "post-development hold-out", not "real-time";
* "largely disappears" or "is small", not "disappears";
* never "widely used" (no usage evidence).

The earlier draft of this statement used "first national-scale benchmark", "widely used" and "data created
after development". Those phrasings are withdrawn: the first two lack evidence, and the third is inaccurate,
because the reports existed when the models were saved.

### 4.2 Claims we must NOT make

1. "First conformal prediction for agricultural prices." Ouyang & Tang (2026) is prior work.
2. "First data-quality study of AGMARKNET." Jain et al. (2020) and Guo et al. (2020) treat missing or erroneous
   entries.
3. "ML clearly outperforms statistical methods." SES matches the global model at 1–3 days, and gains are only
   3–8%.
4. "The zero-change / loss-function result is a new theory." It follows from Gneiting (2011) and Kolassa (2016).
5. "The AGMARKNET 2.0 migration caused a distribution shift." On complete data the shift is small (−1.5 to −2.2
   coverage points).
6. "The Kaggle mirror is wrong." Every mirror record exists in the official data and 99.3% have identical
   prices. It is **incomplete**, not corrupt.
7. "Widely used mirror", unless usage evidence is added (UNVERIFIED).
8. Any farmer-income, profit or welfare effect. Hit rates are on published modal prices, and there was no
   field study.
9. Anything about the 2016–2024 retraining or the 2026 test before those results exist.
10. Comparisons with published accuracy numbers from other papers (see the comparability rules in
    `RESEARCH_GAP.md` §5).
11. "Real-time" forecasting if the same-day cross-market features would not actually be available at the
    origin (KNOWN_LIMITATIONS #24).
12. "Distribution-free guarantee" under drift. Split-conformal guarantees exchangeability-based coverage only.

---

## 5. Evidence a Q1 (IJF) reviewer will likely demand

| Request | Why | Feasible locally? |
|---|---|---|
| Per-series ETS, ARIMA and Theta (statsforecast/fable) on a larger sample (≥ 2,000 series), on the same test rows as SES | Standard IJF benchmarks; SES alone is thin | **Yes**: CPU, hours |
| Global LightGBM or XGBoost with L1 and quantile loss | Strongest tabular global-model standard since M5 | **Yes**: 2 M-row samples fit in memory |
| Deep or foundation baselines (N-BEATS, DeepAR, TFT; zero-shot Chronos/TimesFM) on a sample | Reviewers expect at least one | **Partly**: on a few thousand series on CPU/MPS; not at full scale |
| Multiple seeds (training-row sample and model seeds), with spread of rel. MAE | Only seed 20261022 so far | **Yes**: about 1.7 h per run |
| Rolling-origin results in the main text (C.1 exists), plus Model Confidence Set | Stability across origins; multiple comparisons | **Yes** |
| Quantile and interval scores (pinball, Winkler/interval score, CRPS), conditional coverage | Coverage alone is not enough at IJF | **Yes**: from saved intervals |
| Cross-section timing check: re-run with cross-market features lagged one day | Leakage concern (KNOWN_LIMITATIONS #24) | **Yes**: one extra run |
| Mechanism of the mirror effect: gap-length and inter-report-interval distributions, mirror vs official | Makes C-F4 causal rather than correlational | **Yes**: data on disk |
| Evidence that the mirror is widely used (Kaggle usage, citing papers) | Supports the "widely used" framing | **Yes**: manual |
| Retraining 2016–2024, final test 2026 | Ageing gap of the frozen models | **Done**: no measurable gain (DM p 0.12–0.99) |
| Economic evaluation of the decision rule against naive policies, with storage costs | Decision value | **Partly**: back-test yes, real costs need external data |
| Field or user study with farmers | Real-world value | **No**: not feasible locally |
| Arrivals or volume features, weather | Domain completeness | **Partly**: arrivals depend on the data.gov.in resource (UNVERIFIED) |

---

## 6. Top reviewer risks

1. **Weak benchmark set.**
   - No ETS/ARIMA/Theta beyond SES on 400 series.
   - No LightGBM, deep or foundation baseline.
   - A single seed.

   With 3–8% gains, an IJF reviewer will ask whether a stronger standard closes the gap. Fix: the rows marked
   "Yes" in §5.
2. **Timing of the same-day cross-market features.**
   - The only feature group whose ablation hurts (0.944 → 0.960) relies on same-day reports from other
     markets.
   - If those reports are not available at forecast time, the 7–14 day advantage is partly leakage.

   Fix: a run with cross-market features lagged one day, plus a statement of the real publication lag.
3. **Novelty perceived as "data engineering".**
   - The loss result is textbook (Gneiting 2011), and conformal intervals already exist for agricultural prices
     (Ouyang & Tang 2026).
   - The mirror finding could read as a one-off data bug.

   Fix: frame the paper around evaluation validity (vintages, provenance, prospective scoring), in line with
   IJF's real-time-data tradition, and show the mechanism quantitatively.

## Follow-up to the second review (2026-10-23)

**Primary target for this draft: International Journal of Forecasting**, as an empirical
forecast-evaluation/source-quality study. This is a scope choice, not an acceptance or
current quartile guarantee. IEEE formatting is an alternate rendering, not a selected
IEEE journal or evidence of submission.

Fresh official IIF page accessible: https://forecasters.org/ijf/ (2026-10-23).
It explicitly includes evaluation, applications and implementation, uses double-blind
review, and describes mandatory data/code sharing (unless acceptable reasons apply)
and an acceptance-stage reproducibility check. Therefore a clean smaller-model release
alone does **not** establish that the full paper meets its reproducibility requirement.
Historical principal results still need full-size reruns or must be removed from
acceptance-critical claims. The ScienceDirect aims/scope endpoint still returned 403.

The empirical case is actionable: check source completeness before interpreting drift,
match origins while documenting target changes, report strong naive baselines and
separate historical results from source-attributable reproduction and future-issued
confirmation. No new forecasting or conformal algorithm is claimed. Human statistical
review remains an explicit blocker to submission recommendation.
