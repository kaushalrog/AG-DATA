# AG-DATA API contract — v1

Base path: `/api/v1`. JSON only. All responses carry the header `X-Data-As-Of` (latest observation date in the served dataset).
The API never returns prose for farmers: it returns numbers and **codes**; the app localises every code into the user's language.
Ids are strings (64-bit hashes do not fit in JavaScript numbers).

Common objects

```jsonc
// Entity = one price series
{"entity_id": "-7212340012345", "state": "Tamil Nadu", "district": "Salem", "market": "Salem",
 "commodity": "Tomato", "variety": "Hybrid", "grade": "Local"}

// Freshness: always present when a price is shown
{"last_date": "2026-04-17", "days_old": 4, "stale": true}  // days_old counted from meta.data_as_of
```

Errors: `{"error": {"code": "not_found" | "bad_request" | "rate_limited" | "unavailable", "message": "..."}}` with HTTP 404/400/429/503. No stack traces, file paths or infrastructure names.

## Endpoints

| Method & path | Purpose |
|---|---|
| `GET /health` | liveness `{"status":"ok","version":"2.0.0"}` |
| `GET /ready` | readiness: gold data loaded `{"ready":true,"data_as_of":"2026-04-21","model_version":"..."}`; 503 if not |
| `GET /meta` | dataset/model metadata (below) |
| `GET /states` | `[{"state":"Tamil Nadu","markets":312,"last_date":"2026-04-21"}]` |
| `GET /markets?state=&district=&q=&limit=&offset=` | paged markets |
| `GET /commodities?state=&market=&q=` | commodities with coverage |
| `GET /prices/latest?state=&district=&market=&commodity=&q=&limit=50&offset=0` | latest report per entity, paged |
| `GET /series/{entity_id}?days=180` | history + summary |
| `GET /forecast/{entity_id}` | forecast, intervals, decision card, evidence |
| `GET /compare/{entity_id}?scope=state\|district&limit=20` | same commodity+variety in other markets |
| `GET /alerts?state=&commodity=&days=14` | recent unusual price movements |
| `GET /trends?state=&limit=10` | biggest 7-day movers in a state |

### `GET /meta`
```json
{"data_as_of": "2026-04-21", "generated_at": "2026-10-22T18:00:00Z", "days_since_data": 184,
 "data_origin": "archive", "source": {"name": "AGMARKNET via data.gov.in (archived)", "licence": "GODL-India", "url": "https://www.data.gov.in/"},
 "model_version": "fc_2026-10-22_abc123", "horizons": ["next","h3","h7","h14"],
 "price_unit": "INR/quintal", "languages": ["en","ta","te","ml","hi","kn"],
 "decision_rules_version": "2026-10-22.1"}
```
`data_origin` is `archive` (historical snapshot), `replay`, or `live`. The app must show a banner whenever `days_since_data > 3`.

### `GET /prices/latest`
```json
{"total": 1234, "limit": 50, "offset": 0, "items": [
  {"entity": {...Entity}, "date": "2026-04-17", "min_price": 1800, "max_price": 2200, "modal_price": 2000,
   "unit": "INR/quintal", "freshness": {...}, "change_7d_pct": -4.2, "forecast_supported": true}]}
```

### `GET /series/{entity_id}?days=180`
```json
{"entity": {...}, "unit": "INR/quintal",
 "points": [{"date": "2026-01-02", "min": 1700, "max": 2100, "modal": 1900}],
 "summary": {"n_obs_30d": 18, "change_7d_pct": -4.2, "change_30d_pct": 12.0, "trend": "rising|falling|stable",
             "volatility_30d_pct": 9.1, "volatility_level": "low|medium|high"},
 "freshness": {...}}
```
`trend`: 30-day log change > +5% rising, < -5% falling, else stable. `volatility_30d_pct` = 100 x std of daily log price over 30 days; level low < 5, high > 15.

### `GET /forecast/{entity_id}`
```json
{"entity": {...}, "supported": true, "unsupported_reason": null,
 "origin": {"date": "2026-04-17", "modal_price": 2000},
 "freshness": {...},
 "horizons": [
   {"horizon": "h7", "days": 7, "target_window": ["2026-04-24", "2026-04-27"],
    "median": 2080, "lo80": 1750, "hi80": 2460, "lo90": 1650, "hi90": 2610, "change_pct": 4.0,
    "model": "gbt", "test_mae_pct_of_price": 9.8, "test_rel_mae_vs_persistence": 0.93, "interval_coverage80_test": 0.79}],
 "decision": {"signal": "HOLD|SELL|WATCH|COMPARE", "horizon": "h7",
              "reason_codes": ["forecast_expired"],
              "costs": {"holding_cost_pct": 6.0, "perishable": true},
              "kind": "market_outlook",
              "at_snapshot": {"as_of": "2026-04-17", "signal": "HOLD", "reason_codes": ["lower_bound_above_cost", "perishable_cost_applied"]}},
 "explanation": {"recent_trend": "rising", "volatility_level": "medium", "seasonal_last_year_change_pct": 5.5,
                 "markets_moving_same_way_pct": 62},
 "warnings": ["data_stale", "sparse_history", "high_volatility", "wide_interval", "archive_data", "forecast_origin_differs"],
 "model_version": "...", "source": {...}}
```
* `supported=false` with `unsupported_reason` in `insufficient_history` | `not_in_forecast_commodities` | `stale_beyond_limit`. Then `horizons` is empty and `decision.signal` is `WATCH`.
* Intervals are split-conformal intervals calibrated on 2024 validation residuals; their measured test coverage is returned per horizon. They are not guarantees.
* `decision.kind` is always `market_outlook`: transport, fees and storage are not known for the individual farmer, so the card is not a profit recommendation.

Signals and reason codes. The canonical rule is in `conf/decision_rules.json`. It is implemented identically in `py/agri/api/decisions.py`, `app/js/decision.js` and, for HOLD/SELL/WATCH, `ForecastEval.decisions`, and all three are tested against `conf/decision_fixtures.json`. It is evaluated on the **primary horizon h7 only**, in this order:

| order | signal | rule | reason codes |
|---|---|---|---|
| 1 | WATCH | no supported forecast (unsupported reason stale_beyond_limit maps to stale_data; not_in_forecast_commodities gives no code) | `insufficient_history`, `stale_data` |
| 2 | WATCH | **forecast expired**: today is past the h7 target window, or days_since_data > 3. The response adds `decision.at_snapshot` with what the rule said on the data date (history, not advice) | `forecast_expired` |
| 3 | WATCH | the market's own report is more than 3 days older than the dataset end | `stale_data` |
| 4 | HOLD | lo80 ≥ today × (1 + cost), cost = 1% + weekly(5% perishable / 1% durable) × 7/7 | `lower_bound_above_cost` (+ `perishable_cost_applied`) |
| 5 | SELL | hi80 ≤ today | `upper_bound_below_today` |
| 6 | COMPARE | a comparable market in the same **state**, reported within 3 days, with (price − transport) ≥ today × 1.05 | `better_market_nearby` |
| 7 | WATCH | otherwise | `uncertain` (+ `perishable_cost_applied`) |

Horizon objects also carry `test_wape_pct`, the commodity's test WAPE for that horizon. `test_mae_pct_of_price` is kept as an alias for older clients, and its value is the same WAPE.

### `GET /compare/{entity_id}`
```json
{"reference": {"entity": {...}, "modal_price": 2000, "date": "2026-04-17"},
 "items": [{"entity": {...}, "modal_price": 2300, "date": "2026-04-18", "diff_pct": 15.0,
            "freshness": {...}, "forecast_h7_median": 2250, "comparable": true}]}
```
`comparable=false` when the other price is more than 3 days older than the reference.

### `GET /alerts`
```json
{"items": [{"entity": {...}, "date": "2026-04-18", "modal_price": 5200, "type": "price_spike|price_drop|suspect_data_error",
            "log_dev": 0.62, "robust_z": 5.1, "ref_mean_price": 2800}]}
```

### `GET /trends`
```json
{"state": "Tamil Nadu", "as_of": "2026-04-21",
 "rising": [{"commodity": "Tomato", "median_change_7d_pct": 18.0, "markets": 25}],
 "falling": [...]}
```

## Security
* CORS allow-list from `AGRI_API_CORS_ORIGINS` (comma separated); default is the local dev origin only.
* Token-bucket rate limit per client IP (`AGRI_API_RATE_PER_MIN`, default 120).
* Inputs validated (lengths, enums, numeric ranges); unknown ids return 404.
