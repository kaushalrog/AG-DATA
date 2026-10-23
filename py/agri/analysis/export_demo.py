"""Export a REAL-data demo snapshot for the PWA's offline demo mode.

Calls the real API (in-process, over the gold layer) and writes the exact JSON
bodies to app/demo/, replacing the synthetic placeholders. The snapshot is a
historical archive (meta.data_origin = "archive"), and the app labels it so.

Entity selection: for each focus state, the forecast-supported entities of the
most-reported commodities, preferring Tamil Nadu (the primary usability target).

    .venv/bin/python -m agri.analysis.export_demo --per-state 8
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
    ap.add_argument("--per-state", type=int, default=8)
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
    markets = {"items": [], "total": 0}
    latest = {"items": [], "total": 0, "limit": 0, "offset": 0}
    alerts = {"items": []}
    ids: list[str] = []
    for st in [s["state"] for s in states]:
        m = get("/markets", state=st, limit=500)
        markets["items"] += m["items"]
        p = get("/prices/latest", state=st, limit=200)
        latest["items"] += p["items"]
        alerts["items"] += get("/alerts", state=st, days=30, limit=20)["items"]
        picked, seen = [], set()
        for it in p["items"]:
            e = it["entity"]
            if it["forecast_supported"] and not it["freshness"]["stale"] and e["commodity"] not in seen:
                # prefer series with enough history to make the chart meaningful
                if len(get(f"/series/{e['entity_id']}", days=180)["points"]) >= 20:
                    picked.append(e["entity_id"]); seen.add(e["commodity"])
            if len(picked) >= a.per_state:
                break
        ids += picked
    markets["total"] = len(markets["items"])
    latest["total"] = latest["limit"] = len(latest["items"])
    dump("markets.json", markets)
    dump("prices_latest.json", latest)
    dump("alerts.json", alerts)
    dump("commodities.json", get("/commodities"))
    tn = "Tamil Nadu" if any(s["state"] == "Tamil Nadu" for s in states) else states[0]["state"]
    dump("trends.json", get("/trends", state=tn))
    for i in ids:
        dump(f"series_{i}.json", get(f"/series/{i}", days=180))
        dump(f"forecast_{i}.json", get(f"/forecast/{i}"))
        dump(f"compare_{i}.json", get(f"/compare/{i}"))
    dump("index.json", {
        "_doc": "REAL archived AGMARKNET data exported from the gold layer by py/agri/analysis/export_demo.py; "
                f"data_as_of {meta['data_as_of']}, model {meta['model_version']}. Historical snapshot, not live.",
        "files": {"meta": "meta.json", "states": "states.json", "markets": "markets.json", "commodities": "commodities.json",
                  "prices_latest": "prices_latest.json", "alerts": "alerts.json", "trends": "trends.json"},
        "entities": {"series": ids, "forecast": ids, "compare": ids}})
    for f in ("README.md",):
        if (out / f).exists():
            shutil.copy(out / f, tmp / f)
    shutil.rmtree(out, ignore_errors=True)
    tmp.rename(out)
    size = sum(p.stat().st_size for p in out.iterdir())
    print(json.dumps({"entities": len(ids), "files": len(list(out.iterdir())), "bytes": size, "states": [s["state"] for s in states]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
