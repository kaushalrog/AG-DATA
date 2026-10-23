"""Decision-support rule (canonical spec: conf/decision_rules.json, fixtures: conf/decision_fixtures.json).

The same rule is implemented in app/js/decision.js (so farmers can apply their own
costs) and, for HOLD/SELL/WATCH, in ForecastEval.decisions (the Spark backtest).
All three are tested against the shared fixtures.

Evaluated on the PRIMARY horizon only (h7), in this order:
  unsupported      -> WATCH  [insufficient_history | stale_data | (none for not_in_forecast_commodities)]
  forecast_expired -> WATCH  [forecast_expired]   (today is past the target window, or the dataset is stale)
  stale report     -> WATCH  [stale_data]
  HOLD   if lo80 >= today * (1 + cost_h)          cost_h = fixed + weekly(perishable) * h/7
  SELL   if hi80 <= today
  COMPARE if a fresh (<= 3 days), comparable market's (price - transport) >= today * (1 + 5%)
  WATCH  otherwise [uncertain]
The output is a MARKET OUTLOOK with machine-readable reason codes; the app localises the wording.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

RULES_PATH = Path("conf/decision_rules.json")
EPS = 1e-9  # boundary tolerance shared with decision.js / ForecastEval


@lru_cache(maxsize=4)
def load_rules(path: str | None = None) -> dict:
    return json.loads(Path(path or RULES_PATH).read_text())


@dataclass
class Decision:
    signal: str
    horizon: str | None
    reason_codes: list[str]
    holding_cost_pct: float
    perishable: bool
    kind: str = "market_outlook"
    best_market_gain_pct: float | None = None
    extra: dict = field(default_factory=dict)


def holding_cost(commodity: str, horizon_days: int, rules: dict) -> tuple[float, bool]:
    perishable = commodity in set(rules["perishable_commodities"])
    weekly = rules["weekly_holding_cost"]["perishable" if perishable else "durable"]
    return rules["fixed_transaction_cost"] + weekly * horizon_days / 7.0, perishable


def best_market_gain(today: float, compare: list[dict], transport: float, rules: dict) -> float | None:
    best = None
    for m in compare or []:
        if not m.get("comparable", True) or m.get("days_old") is None or m["days_old"] > rules["compare_max_staleness_days"]:
            continue
        g = (m["modal_price"] - transport) / today - 1
        best = g if best is None or g > best else best
    return best


def decide(commodity: str, *, supported: bool, unsupported_reason: str | None = None, expired: bool = False,
           stale: bool = False, today: float | None = None, days: int | None = None, lo80: float | None = None,
           hi80: float | None = None, compare: list[dict] | None = None, transport: float | None = None,
           rules: dict | None = None) -> Decision:
    """Prices (today, lo80, hi80, compare[].modal_price, transport) are INR/quintal."""
    rules = rules or load_rules()
    h = rules["primary_horizon"]
    perishable = commodity in set(rules["perishable_commodities"])
    if not supported or today is None or lo80 is None or hi80 is None:
        codes = {"insufficient_history": ["insufficient_history"], "stale_beyond_limit": ["stale_data"],
                 "not_in_forecast_commodities": []}.get(unsupported_reason or "insufficient_history", ["insufficient_history"])
        return Decision("WATCH", None, codes, 0.0, perishable)
    cost, _ = holding_cost(commodity, days, rules)
    cost_pct = round(cost * 100, 2)
    if expired:
        return Decision("WATCH", h, ["forecast_expired"], cost_pct, perishable)
    if stale:
        return Decision("WATCH", h, ["stale_data"], cost_pct, perishable)
    note = ["perishable_cost_applied"] if perishable else []
    if lo80 >= today * (1 + cost) * (1 - EPS):
        return Decision("HOLD", h, ["lower_bound_above_cost"] + note, cost_pct, perishable)
    if hi80 <= today * (1 + EPS):
        return Decision("SELL", h, ["upper_bound_below_today"], cost_pct, perishable)
    t = rules.get("default_transport_inr_per_quintal", 0) if transport is None else transport
    gain = best_market_gain(today, compare or [], t, rules)
    if gain is not None and gain >= rules["compare_min_gain"] - EPS:
        return Decision("COMPARE", h, ["better_market_nearby"], cost_pct, perishable, best_market_gain_pct=round(gain * 100, 2))
    return Decision("WATCH", h, ["uncertain"] + note, cost_pct, perishable)
