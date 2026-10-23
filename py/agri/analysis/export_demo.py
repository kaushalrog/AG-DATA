"""Export a REAL-data demo snapshot for the PWA's offline demo mode.

Calls the real API (in-process, over the gold layer) and writes the exact JSON
bodies to app/demo/, replacing the synthetic placeholders. The snapshot is a
historical archive (meta.data_origin = "archive"), and the app labels it so.

Entity selection: for each focus state, the forecast-supported entities of the
most-reported commodities, preferring Tamil Nadu (the primary usability target).

    .venv/bin/python -m agri.analysis.export_demo --markets-per-state 4 --max-commodities 20
"""
from __future__ import annotations

import argparse
import os
import json
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from agri.api.app import create_app

FOCUS_STATES = ["Tamil Nadu", "Karnataka", "Kerala", "Telangana", "Andhra Pradesh", "Maharashtra", "Uttar Pradesh",
                "Madhya Pradesh", "Gujarat", "Punjab"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="app/demo")
    ap.add_argument("--markets-per-state", type=int, default=4)
    ap.add_argument("--max-commodities", type=int, default=20)
    a = ap.parse_args(argv)
    os.environ["AGRI_API_RATE_PER_MIN"] = "1000000"  # in-process export, not a client
    c = TestClient(create_app(app_dir=""))
    out = Path(a.out)
    tmp = out.with_name(out.name + "_new")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)

    def get(path, **params):
        r = c.get("/api/v1" + path, params=params)
        r.raise_for_status()
        return r.json()

    def dump(name, body):
        (tmp / name).write_text(json.dumps(body, ensure_ascii=False, separators=(",", ":")))

    meta = get("/meta")
    dump("meta.json", meta)
    states = [s for s in get("/states") if s["state"] in FOCUS_STATES]
    dump("states.json", states)
    # Consistency rule (checked by app/tests/demo.test.mjs): every market listed has prices, and every
    # listed price, alert or comparison opens a detail view. So the snapshot covers a few whole markets
    # per state instead of a sample of rows across many markets.
    markets = {"items": [], "total": 0}
    latest = {"items": [], "total": 0, "limit": 0, "offset": 0}
    alerts = {"items": []}
    trends: dict[str, str] = {}
    ids: list[str] = []
    for st in [s["state"] for s in states]:
        ms = [m for m in get("/markets", state=st, limit=500)["items"] if m["last_date"] >= meta["data_as_of"][:8] + "01"
              or m["last_date"] >= meta["data_as_of"]]
        # well-stocked but not huge markets keep the snapshot small enough for a phone
        ms = [m for m in ms if m["commodities"] <= a.max_commodities] or ms
        ms = sorted(ms, key=lambda m: (-m["commodities"], m["market"]))[: a.markets_per_state]
        for m in sorted(ms, key=lambda m: (m["district"], m["market"])):
            items = get("/prices/latest", state=st, market=m["market"], limit=200)["items"]
            items = [it for it in items if it["entity"]["district"] == m["district"]]
            if not items:
                continue
            markets["items"].append(m)
            latest["items"] += items
            ids += [it["entity"]["entity_id"] for it in items]
        f = f"trends_{len(trends)}.json"
        dump(f, get("/trends", state=st)); trends[st] = f
    idset = set(ids)
    for st in [s["state"] for s in states]:
        alerts["items"] += [it for it in get("/alerts", state=st, days=30, limit=200)["items"] if it["entity"]["entity_id"] in idset]
    markets["total"] = len(markets["items"])
    latest["total"] = latest["limit"] = len(latest["items"])
    dump("markets.json", markets)
    dump("prices_latest.json", latest)
    dump("alerts.json", alerts)
    dump("commodities.json", get("/commodities"))
    tn = "Tamil Nadu" if "Tamil Nadu" in trends else next(iter(trends))
    shutil.copy(tmp / trends[tn], tmp / "trends.json")
    for i in ids:
        dump(f"series_{i}.json", get(f"/series/{i}", days=180))
        dump(f"forecast_{i}.json", get(f"/forecast/{i}"))
        # full comparison list: its rows only display prices (no detail link), and the decision card's
        # COMPARE signal is computed from it
        dump(f"compare_{i}.json", get(f"/compare/{i}", scope="state", limit=20))
    dump("index.json", {
        "_doc": "REAL AGMARKNET data exported from the gold layer by py/agri/analysis/export_demo.py; "
                f"data_as_of {meta['data_as_of']}, model {meta['model_version']}. Historical snapshot, not live. "
                f"Covers up to {a.markets_per_state} whole markets per state.",
        "files": {"meta": "meta.json", "states": "states.json", "markets": "markets.json", "commodities": "commodities.json",
                  "prices_latest": "prices_latest.json", "alerts": "alerts.json", "trends": "trends.json"},
        "trends_by_state": trends,
        "entities": {"series": ids, "forecast": ids, "compare": ids}})
    for f in ("README.md",):
        if (out / f).exists():
            shutil.copy(out / f, tmp / f)
    shutil.rmtree(out, ignore_errors=True)
    tmp.rename(out)
    size = sum(p.stat().st_size for p in out.iterdir())
    print(json.dumps({"markets": markets["total"], "entities": len(ids), "files": len(list(out.iterdir())), "bytes": size, "states": [s["state"] for s in states]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
