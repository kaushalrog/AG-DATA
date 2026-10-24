"""Export the COMPLETE served release as static files, so the app works with all real data on a static
host (GitHub Pages) without a server. The app reads it in api.js "snapshot" mode.

Every response comes from the real API (in-process, over the current gold layer), so the snapshot is
the server's output, only re-packed:

  <out>/current.json                       pointer: version, data_as_of, shard count, state keys
  <out>/<version>/meta.json states.json commodities.json
  <out>/<version>/state/<key>.json         all latest prices of a state as compact rows (+ h7 median),
                                           from which api.js answers /prices/latest and /compare
  <out>/<version>/markets/<key>.json       /markets for the state (all pages)
  <out>/<version>/alerts/<key>.json        /alerts?state=..&days=14 (as the app asks)
  <out>/<version>/trends/<key>.json        /trends?state=..&limit=50
  <out>/<version>/series/<k>.json          /series/{id}?days=180 for ids with int(id) % SHARDS == k,
                                           points as [date, min, max, modal]
  <out>/<version>/forecast/<k>.json        /forecast/{id}, without the per-row source/model_version
                                           (api.js restores them from meta)

Versioned directories are immutable, so browsers may cache them forever; only current.json changes.

    .venv/bin/python -m agri.analysis.export_snapshot [--out build/snapshot] [--workers 8]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

SHARDS = 1024
LATEST_FIELDS = ["entity_id", "district", "market", "commodity", "variety", "grade", "date",
                 "min_price", "max_price", "modal_price", "change_7d_pct", "forecast_supported", "f7"]
_client = None


def key(state: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", state.lower()).strip("-")


def client():
    global _client
    if _client is None:
        os.environ["AGRI_API_RATE_PER_MIN"] = "1000000000"  # in-process export, not a client
        from fastapi.testclient import TestClient
        from agri.api.app import create_app
        _client = TestClient(create_app(app_dir=""))
    return _client


def get(path: str, **params):
    r = client().get("/api/v1" + path, params=params)
    r.raise_for_status()
    return r.json()


def pages(path: str, limit: int, **params) -> dict:
    out, offset = None, 0
    while True:
        p = get(path, limit=limit, offset=offset, **params)
        if out is None:
            out = p
        else:
            out["items"] += p["items"]
        offset += limit
        if offset >= p["total"]:
            break
    out["limit"], out["offset"] = len(out["items"]), 0
    return out


def entity_batch(ids: list[str]) -> list[tuple[str, dict, dict]]:
    res = []
    for i in ids:
        s = get(f"/series/{i}", days=180)
        s["points"] = [[p["date"], p["min"], p["max"], p["modal"]] for p in s["points"]]
        f = get(f"/forecast/{i}")
        f.pop("source", None); f.pop("model_version", None)
        res.append((i, s, f))
    return res


def dump(path: Path, body) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, ensure_ascii=False, separators=(",", ":")))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="build/snapshot")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args(argv)
    t0 = time.time()
    import duckdb
    meta = get("/meta")
    gold = Path(os.environ.get("AGRI_GOLD_ROOT", "data/gold"))
    version = f"{meta['data_as_of']}-{meta['model_version']}-" + hashlib.sha256(meta["generated_at"].encode()).hexdigest()[:8]
    out = Path(a.out); vdir = out / version
    shutil.rmtree(vdir, ignore_errors=True)
    dump(vdir / "meta.json", meta)
    states = get("/states")
    dump(vdir / "states.json", states)
    dump(vdir / "commodities.json", get("/commodities"))
    # h7 medians, exactly as compare_items joins them (supported forecasts only)
    f7 = dict(duckdb.sql(f"SELECT entity_id, median FROM read_parquet('{gold}/latest_forecasts/*.parquet') "
                         "WHERE horizon='h7' AND supported").fetchall())
    ids: list[str] = []
    for s in states:
        st, k = s["state"], key(s["state"])
        dump(vdir / "markets" / f"{k}.json", pages("/markets", 500, state=st))
        lat = pages("/prices/latest", 200, state=st)
        rows = []
        for it in lat["items"]:
            e = it["entity"]
            rows.append([e["entity_id"], e["district"], e["market"], e["commodity"], e["variety"], e["grade"], it["date"],
                         it["min_price"], it["max_price"], it["modal_price"], it["change_7d_pct"], int(it["forecast_supported"]),
                         round(f7[e["entity_id"]], 2) if e["entity_id"] in f7 and f7[e["entity_id"]] is not None else None])
            ids.append(e["entity_id"])
        dump(vdir / "state" / f"{k}.json", {"state": st, "fields": LATEST_FIELDS, "rows": rows})
        dump(vdir / "alerts" / f"{k}.json", get("/alerts", state=st, days=14, limit=200))
        dump(vdir / "trends" / f"{k}.json", get("/trends", state=st, limit=50))
    n_gold = duckdb.sql(f"SELECT count(*) FROM read_parquet('{gold}/latest_prices/*.parquet')").fetchall()[0][0]
    if len(ids) != len(set(ids)) or len(ids) != n_gold:  # paging must neither skip nor repeat a series
        raise SystemExit(f"export incomplete: {len(ids)} rows, {len(set(ids))} unique, {n_gold} in gold")
    print(f"states done: {len(states)} states, {len(ids)} series ({time.time() - t0:.0f}s)", flush=True)

    series: dict[int, dict] = {}
    forecast: dict[int, dict] = {}
    chunks = [ids[i:i + 500] for i in range(0, len(ids), 500)]
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for n, batch in enumerate(ex.map(entity_batch, chunks), 1):
            for i, s, f in batch:
                sh = int(i) % SHARDS
                series.setdefault(sh, {})[i] = s
                forecast.setdefault(sh, {})[i] = f
            if n % 20 == 0:
                print(f"  {n * 500}/{len(ids)} series ({time.time() - t0:.0f}s)", flush=True)
    for sh in range(SHARDS):
        dump(vdir / "series" / f"{sh}.json", series.get(sh, {}))
        dump(vdir / "forecast" / f"{sh}.json", forecast.get(sh, {}))
    pointer = {"version": version, "data_as_of": meta["data_as_of"], "model_version": meta["model_version"],
               "generated_at": meta["generated_at"], "shards": SHARDS, "entities": len(ids),
               "states": {s["state"]: key(s["state"]) for s in states}}
    tmp = out / "current.json.tmp"
    dump(tmp, pointer)
    os.replace(tmp, out / "current.json")  # written last: a half-written version is never pointed at
    for old in out.iterdir():  # keep only the current version
        if old.is_dir() and old.name != version:
            shutil.rmtree(old, ignore_errors=True)
    size = sum(p.stat().st_size for p in vdir.rglob("*.json"))
    print(json.dumps({"version": version, "states": len(states), "entities": len(ids), "bytes": size,
                      "seconds": round(time.time() - t0)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
