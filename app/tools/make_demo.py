#!/usr/bin/env python3
"""Write a SMALL, SYNTHETIC placeholder demo snapshot into app/demo/ following docs/API.md.

Every file carries "_demo_placeholder": true. The integration owner replaces these files with an
export of real archived data (same file names, listed in demo/index.json). Prices here are
invented and deterministic; they are NOT real market data.
Usage: python3 app/tools/make_demo.py
"""
import json
import math
import os
from datetime import date, timedelta

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "demo")
AS_OF = date(2026, 4, 21)
META = {
    "_demo_placeholder": True,
    "data_as_of": AS_OF.isoformat(), "generated_at": "2026-10-22T18:00:00Z", "days_since_data": 184,
    "data_origin": "archive",
    "source": {"name": "AGMARKNET via data.gov.in (archived)", "licence": "GODL-India", "url": "https://www.data.gov.in/"},
    "model_version": "demo-placeholder", "horizons": ["next", "h3", "h7", "h14"],
    "price_unit": "INR/quintal", "languages": ["en", "ta", "te", "ml", "hi", "kn"],
    "decision_rules_version": "2026-10-22.1",
}
PERISHABLE = {"Tomato", "Onion", "Potato", "Brinjal", "Banana"}

# id, state, district, market, commodity, variety, last modal, days_old, growth/day, interval width, mode
E = [
    ("-7212340012345", "Tamil Nadu", "Salem", "Salem", "Tomato", "Hybrid", 2000, 0, 0.020, 0.06, "hold"),
    ("-7212340012346", "Tamil Nadu", "Salem", "Attur", "Tomato", "Hybrid", 2150, 1, 0.004, 0.10, "watch"),
    ("-7212340012347", "Tamil Nadu", "Salem", "Mettur", "Tomato", "Hybrid", 2400, 9, 0.0, 0.12, "watch"),
    ("-7212340012348", "Tamil Nadu", "Salem", "Omalur", "Tomato", "Hybrid", 1900, 2, 0.003, 0.10, "watch"),
    ("5512900077001", "Tamil Nadu", "Dindigul", "Dindigul", "Onion", "Bellary", 1800, 1, -0.015, 0.07, "sell"),
    ("5512900077002", "Tamil Nadu", "Dindigul", "Oddanchatram", "Onion", "Bellary", 1700, 2, -0.010, 0.09, "watch"),
    ("3300110022001", "Tamil Nadu", "Thanjavur", "Thanjavur", "Paddy (Dhan)(Common)", "Common", 2300, 3, 0.001, 0.05, "watch"),
    ("3300110022002", "Tamil Nadu", "Namakkal", "Namakkal", "Tapioca", "Other", 1200, 5, 0.0, 0.0, "unsupported"),
    ("8801234500001", "Karnataka", "Kolar", "Kolar", "Tomato", "Local", 1100, 0, 0.002, 0.11, "compare"),
    ("8801234500002", "Karnataka", "Kolar", "Chintamani", "Tomato", "Local", 1250, 1, 0.002, 0.11, "watch"),
    ("8801234500003", "Karnataka", "Kolar", "Bangarpet", "Tomato", "Local", 1050, 6, 0.0, 0.12, "watch"),
]
HZ = [("next", 1), ("h3", 3), ("h7", 7), ("h14", 14)]
MAE = {"next": 5.1, "h3": 7.4, "h7": 9.8, "h14": 13.2}
COV = {"next": 0.81, "h3": 0.80, "h7": 0.79, "h14": 0.77}


def entity(e):
    return {"entity_id": e[0], "state": e[1], "district": e[2], "market": e[3], "commodity": e[4], "variety": e[5], "grade": "FAQ"}


def fresh(days_old):
    return {"last_date": (AS_OF - timedelta(days=days_old)).isoformat(), "days_old": days_old, "stale": days_old > 3}


def history(e, n=120):
    last = AS_OF - timedelta(days=e[7])
    pts = []
    for i in range(n, -1, -1):
        d = last - timedelta(days=i)
        if d.weekday() == 6 and i:  # markets often closed on Sunday (keep the latest report)
            continue
        trend = e[6] * (1 - e[8] * 0.6 * (i / 7)) if e[8] else e[6]
        wobble = 1 + 0.06 * math.sin(i / 6.0 + len(e[3])) + 0.025 * math.sin(i * 1.7)
        modal = round(max(200, trend * wobble) / 10) * 10 if i else e[6]
        pts.append({"date": d.isoformat(), "min": round(modal * 0.85), "max": round(modal * 1.12), "modal": modal})
    return pts


def summary(pts, e):
    last = pts[-1]["modal"]
    w = [p for p in pts if p["date"] >= (date.fromisoformat(pts[-1]["date"]) - timedelta(days=7)).isoformat()]
    m = [p for p in pts if p["date"] >= (date.fromisoformat(pts[-1]["date"]) - timedelta(days=30)).isoformat()]
    c7 = round((last / w[0]["modal"] - 1) * 100, 1)
    c30 = round((last / m[0]["modal"] - 1) * 100, 1)
    lr = [math.log(m[i]["modal"] / m[i - 1]["modal"]) for i in range(1, len(m))]
    mu = sum(lr) / len(lr)
    vol = round(100 * math.sqrt(sum((x - mu) ** 2 for x in lr) / len(lr)), 1)
    trend = "rising" if c30 > 5 else "falling" if c30 < -5 else "stable"
    level = "low" if vol < 5 else "high" if vol > 15 else "medium"
    n30 = 3 if e[4].startswith("Paddy") else len(m)
    return {"n_obs_30d": n30, "change_7d_pct": c7, "change_30d_pct": c30, "trend": trend, "volatility_30d_pct": vol, "volatility_level": level}


def forecast(e, comp_items):
    p, mode = e[6], e[10]
    f = fresh(e[7])
    base = {"_demo_placeholder": True, "entity": entity(e), "origin": {"date": f["last_date"], "modal_price": p}, "freshness": f,
            "model_version": META["model_version"], "source": META["source"]}
    perishable = e[4] in PERISHABLE
    if mode == "unsupported":
        return {**base, "supported": False, "unsupported_reason": "not_in_forecast_commodities", "horizons": [],
                "decision": {"signal": "WATCH", "horizon": "h7", "reason_codes": [], "costs": {"holding_cost_pct": 2.0, "perishable": False}, "kind": "market_outlook"},
                "explanation": {}, "warnings": ["archive_data"]}
    hs = []
    for name, d in HZ:
        med = p * (1 + e[8] * d)
        w = e[9] * math.sqrt(d / 7)
        start = date.fromisoformat(f["last_date"]) + timedelta(days=d)
        hs.append({"horizon": name, "days": d, "target_window": [start.isoformat(), (start + timedelta(days=3)).isoformat()],
                   "median": round(med), "lo80": round(med * (1 - w)), "hi80": round(med * (1 + w)),
                   "lo90": round(med * (1 - 1.3 * w)), "hi90": round(med * (1 + 1.3 * w)),
                   "change_pct": round((med / p - 1) * 100, 1), "model": "gbt",
                   "test_mae_pct_of_price": MAE[name], "test_rel_mae_vs_persistence": 0.93 if d > 1 else 0.98,
                   "interval_coverage80_test": COV[name]})
    h7 = hs[2]
    cost = 1.0 + (5.0 if perishable else 1.0)
    signal, reasons = "WATCH", ["uncertain"]
    if f["stale"]:
        signal, reasons = "WATCH", ["stale_data"]
    elif h7["lo80"] >= p * (1 + cost / 100):
        signal, reasons = "HOLD", ["lower_bound_above_cost"] + (["perishable_cost_applied"] if perishable else [])
    elif h7["hi80"] <= p:
        signal, reasons = "SELL", ["upper_bound_below_today"]
    elif any(c["comparable"] and c["freshness"]["days_old"] <= 3 and c["modal_price"] >= p * 1.05 for c in comp_items):
        signal, reasons = "COMPARE", ["better_market_nearby"]
    warnings = ["archive_data"] + (["data_stale"] if f["stale"] else [])
    if e[4].startswith("Paddy"):
        warnings.append("sparse_history")
    if e[9] >= 0.11:
        warnings.append("wide_interval")
    return {**base, "supported": True, "unsupported_reason": None, "horizons": hs,
            "decision": {"signal": signal, "horizon": "h7", "reason_codes": reasons,
                         "costs": {"holding_cost_pct": cost, "perishable": perishable}, "kind": "market_outlook"},
            "explanation": {"recent_trend": "rising" if e[8] > 0.005 else "falling" if e[8] < -0.005 else "stable",
                            "volatility_level": "medium", "seasonal_last_year_change_pct": 5.5, "markets_moving_same_way_pct": 62},
            "warnings": warnings}


def compare(e):
    ref = {"entity": entity(e), "modal_price": e[6], "date": fresh(e[7])["last_date"]}
    items = []
    for o in E:
        if o is e or o[4] != e[4] or o[5] != e[5] or o[1] != e[1]:
            continue
        items.append({"entity": entity(o), "modal_price": o[6], "date": fresh(o[7])["last_date"],
                      "diff_pct": round((o[6] / e[6] - 1) * 100, 1), "freshness": fresh(o[7]),
                      "forecast_h7_median": round(o[6] * (1 + o[8] * 7)) if o[10] != "unsupported" else None,
                      "comparable": (o[7] - e[7]) <= 3})
    return {"_demo_placeholder": True, "reference": ref, "items": items}


def write(name, obj):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for fn in os.listdir(OUT):
        if fn.endswith(".json"):
            os.remove(os.path.join(OUT, fn))
    ids = {"series": [], "forecast": [], "compare": []}
    latest = []
    for e in E:
        pts = history(e)
        s = summary(pts, e)
        write(f"series_{e[0]}.json", {"_demo_placeholder": True, "entity": entity(e), "unit": "INR/quintal", "points": pts, "summary": s, "freshness": fresh(e[7])})
        ids["series"].append(e[0])
        c = compare(e)
        if c["items"]:
            write(f"compare_{e[0]}.json", c)
            ids["compare"].append(e[0])
        write(f"forecast_{e[0]}.json", forecast(e, c["items"]))
        ids["forecast"].append(e[0])
        last = pts[-1]
        latest.append({"entity": entity(e), "date": last["date"], "min_price": last["min"], "max_price": last["max"], "modal_price": last["modal"],
                       "unit": "INR/quintal", "freshness": fresh(e[7]), "change_7d_pct": s["change_7d_pct"], "forecast_supported": e[10] != "unsupported"})
    write("meta.json", META)
    states = sorted({e[1] for e in E})
    write("states.json", [{"state": st, "markets": len({e[3] for e in E if e[1] == st}),
                           "last_date": max(fresh(e[7])["last_date"] for e in E if e[1] == st)} for st in states])
    mk = sorted({(e[1], e[2], e[3]) for e in E})
    write("markets.json", {"_demo_placeholder": True, "total": len(mk), "limit": 500, "offset": 0,
                           "items": [{"state": a, "district": b, "market": c, "commodities": sum(1 for e in E if e[3] == c),
                                      "last_date": max(fresh(e[7])["last_date"] for e in E if e[3] == c)} for a, b, c in mk]})
    cm = sorted({e[4] for e in E})
    write("commodities.json", {"_demo_placeholder": True, "items": [{"commodity": c, "markets": sum(1 for e in E if e[4] == c),
                               "forecast_supported": c != "Tapioca"} for c in cm]})
    write("prices_latest.json", {"_demo_placeholder": True, "total": len(latest), "limit": 50, "offset": 0, "items": latest})
    write("alerts.json", {"_demo_placeholder": True, "items": [
        {"entity": entity(E[0]), "date": "2026-04-18", "modal_price": 2600, "type": "price_spike", "log_dev": 0.42, "robust_z": 4.3, "ref_mean_price": 1700},
        {"entity": entity(E[4]), "date": "2026-04-19", "modal_price": 1500, "type": "price_drop", "log_dev": -0.31, "robust_z": -3.9, "ref_mean_price": 2050},
        {"entity": entity(E[6]), "date": "2026-04-16", "modal_price": 9800, "type": "suspect_data_error", "log_dev": 1.45, "robust_z": 9.2, "ref_mean_price": 2300},
        {"entity": entity(E[8]), "date": "2026-04-20", "modal_price": 1400, "type": "price_spike", "log_dev": 0.38, "robust_z": 4.0, "ref_mean_price": 960}]})
    write("trends.json", {"_demo_placeholder": True, "state": "Tamil Nadu", "as_of": AS_OF.isoformat(),
                          "rising": [{"commodity": "Tomato", "median_change_7d_pct": 18.0, "markets": 25},
                                     {"commodity": "Green Chilli", "median_change_7d_pct": 9.5, "markets": 14},
                                     {"commodity": "Coriander (Leaves)", "median_change_7d_pct": 7.2, "markets": 11}],
                          "falling": [{"commodity": "Onion", "median_change_7d_pct": -12.0, "markets": 31},
                                      {"commodity": "Potato", "median_change_7d_pct": -4.8, "markets": 22}]})
    write("index.json", {"_demo_placeholder": True,
                         "_doc": "The app's demo loader reads ONLY this index. files: endpoint -> file; entities: ids with series_/forecast_/compare_<id>.json",
                         "files": {"meta": "meta.json", "states": "states.json", "markets": "markets.json", "commodities": "commodities.json",
                                   "prices_latest": "prices_latest.json", "alerts": "alerts.json", "trends": "trends.json"},
                         "entities": ids})
    print("demo files written:", len(os.listdir(OUT)))
