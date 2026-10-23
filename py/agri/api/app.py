"""AG-DATA public API (contract: docs/API.md).

Serves PERSISTED, versioned outputs of the Spark pipeline (gold layer). It never
trains or runs Spark per request. Run locally:

    AGRI_GOLD_ROOT=data/gold .venv/bin/uvicorn agri.api.app:app --app-dir py --port 8000

Configuration (environment):
    AGRI_GOLD_ROOT           gold layer directory (default data/gold)
    AGRI_RESULTS_ROOT        experiment results (default results/forecast)
    AGRI_API_CORS_ORIGINS    comma-separated allowed origins (default http://localhost:8000)
    AGRI_API_RATE_PER_MIN    requests per minute per client IP (default 120)
    AGRI_APP_DIR             static PWA directory served at / (default app; unset to disable)
    AGRI_API_DOCS            1 to serve /api/docs and /api/openapi.json (default off)
"""
from __future__ import annotations

import json
import logging
import math
import os
import threading
import time
from datetime import date
from pathlib import Path
from typing import Any

import duckdb
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .decisions import decide, load_rules

log = logging.getLogger("agri.api")
VERSION = "2.0.0"
HORIZON_DAYS = {"next": 1, "h3": 3, "h7": 7, "h14": 14}
ENTITY_FIELDS = ("state", "district", "market", "commodity", "variety", "grade")
MAX_Q = 64


class Store:
    """Read-only DuckDB views over the gold layer, loaded once at startup."""

    def __init__(self, gold: Path, results: Path):
        self.gold, self.results = gold, results
        self.meta = json.loads((gold / "meta.json").read_text())
        self.data_as_of = date.fromisoformat(self.meta["data_as_of"])
        self.con = duckdb.connect()
        self.lock = threading.Lock()
        g = str(gold)
        self.con.execute(f"CREATE TABLE prices AS SELECT * FROM read_parquet('{g}/latest_prices/*.parquet')")
        self.con.execute(f"CREATE TABLE fc AS SELECT * FROM read_parquet('{g}/latest_forecasts/*.parquet')")
        self.con.execute(f"CREATE TABLE alerts AS SELECT * FROM read_parquet('{g}/alerts/*.parquet')")
        self.con.execute(f"CREATE VIEW hist AS SELECT * FROM read_parquet('{g}/price_history/*.parquet')")
        self.forecast_commodities = {r[0] for r in self.con.execute("SELECT DISTINCT commodity FROM fc").fetchall()}
        exp = results / self.meta["model_version"]
        self.accuracy: dict[tuple[str, str], dict] = {}
        self.coverage: dict[str, float] = {}
        if exp.exists():
            for h in HORIZON_DAYS:
                f = exp / f"test_by_commodity_{h}.csv"
                if f.exists():
                    rows = self.con.execute(f"SELECT commodity, wape, n FROM read_csv_auto('{f}') WHERE model='selected'").fetchall()
                    for c, wape, n in rows:
                        self.accuracy[(c, h)] = {"wape": wape, "n": n}
                    rel = self.con.execute(
                        f"SELECT commodity, a.mae / b.mae FROM read_csv_auto('{f}') a JOIN read_csv_auto('{f}') b USING (commodity) "
                        f"WHERE a.model='selected' AND b.model='persistence'").fetchall()
                    for c, r in rel:
                        self.accuracy.setdefault((c, h), {})["rel_mae"] = r
            f = exp / "intervals.csv"
            if f.exists():
                for h, cov in self.con.execute(f"SELECT horizon, coverage80 FROM read_csv_auto('{f}') WHERE \"group\"='all'").fetchall():
                    self.coverage[h] = cov

    def q(self, sql: str, params: list | None = None) -> list[dict]:
        with self.lock:
            cur = self.con.execute(sql, params or [])
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]


def _clean(v: Any) -> Any:
    if isinstance(v, float):
        return None if (math.isnan(v) or math.isinf(v)) else round(v, 2)
    if isinstance(v, date):
        return v.isoformat()
    return v


def _like(q: str) -> str:
    """ILIKE pattern for a user substring, with the user's own % and _ treated literally (ESCAPE '\\')."""
    return "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _limit_str(s: str | None, name: str) -> str | None:
    if s is not None and (len(s) > MAX_Q or any(c in s for c in "\x00\n\r")):
        raise HTTPException(400, f"invalid {name}")
    return s


class RateLimiter:
    def __init__(self, per_min: int):
        self.rate, self.cap = per_min / 60.0, float(per_min)
        self.buckets: dict[str, tuple[float, float]] = {}
        self.lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self.lock:
            tokens, last = self.buckets.get(key, (self.cap, now))
            tokens = min(self.cap, tokens + (now - last) * self.rate)
            if tokens < 1:
                self.buckets[key] = (tokens, now)
                return False
            self.buckets[key] = (tokens - 1, now)
            if len(self.buckets) > 50_000:  # bound memory: evict the least recently seen half, not everyone
                for k, _ in sorted(self.buckets.items(), key=lambda kv: kv[1][1])[:25_000]:
                    del self.buckets[k]
            return True


def create_app(gold: str | None = None, results: str | None = None, app_dir: str | None = None) -> FastAPI:
    gold_p = Path(gold or os.environ.get("AGRI_GOLD_ROOT", "data/gold"))
    res_p = Path(results or os.environ.get("AGRI_RESULTS_ROOT", "results/forecast"))
    docs = os.environ.get("AGRI_API_DOCS", "0") == "1"  # interactive docs are opt-in for public deployments
    app = FastAPI(title="AG-DATA API", version=VERSION, docs_url="/api/docs" if docs else None,
                  openapi_url="/api/openapi.json" if docs else None, redoc_url=None)
    origins = [o.strip() for o in os.environ.get("AGRI_API_CORS_ORIGINS", "http://localhost:8000").split(",") if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET"], allow_headers=["*"])
    limiter = RateLimiter(int(os.environ.get("AGRI_API_RATE_PER_MIN", "120")))
    state: dict[str, Any] = {"store": None, "error": None, "target": None}

    def load() -> None:
        # data/gold may be a symlink that the refresh job switches atomically; remember its target
        target = os.path.realpath(gold_p)
        try:
            state["store"] = Store(gold_p, res_p)
            state["error"] = None
        except Exception as e:  # readiness reports it; details only in server logs
            log.exception("gold layer not loadable")
            state["error"] = type(e).__name__
        state["target"] = target

    load()

    def maybe_reload() -> None:
        if os.path.realpath(gold_p) != state["target"]:
            log.info("gold release changed; reloading")
            load()

    status_p = Path(os.environ.get("AGRI_REFRESH_STATUS", "results/refresh/status.json"))

    def store() -> Store:
        if state["store"] is None:
            raise HTTPException(503, "data not available")
        return state["store"]

    @app.middleware("http")
    async def guard(request: Request, call_next):
        if request.url.path.startswith("/api/v1"):
            maybe_reload()
            ip = request.client.host if request.client else "unknown"
            if not limiter.allow(ip):
                return JSONResponse({"error": {"code": "rate_limited", "message": "too many requests"}}, status_code=429)
        resp = await call_next(request)
        if state["store"] is not None:
            resp.headers["X-Data-As-Of"] = state["store"].meta["data_as_of"]
        resp.headers["X-Content-Type-Options"] = "nosniff"
        return resp

    @app.exception_handler(HTTPException)
    async def http_err(_, exc: HTTPException):
        code = {400: "bad_request", 404: "not_found", 429: "rate_limited", 503: "unavailable"}.get(exc.status_code, "error")
        return JSONResponse({"error": {"code": code, "message": str(exc.detail)}}, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def any_err(_, exc: Exception):
        log.exception("unhandled error")
        return JSONResponse({"error": {"code": "error", "message": "internal error"}}, status_code=500)

    def freshness(d: date | None) -> dict:
        s = store()
        days = (s.data_as_of - d).days if d else None
        stale_after = load_rules()["stale_after_days"]
        # days_old is measured against the dataset's own end date: it says whether this market's
        # report lags the others. Whether the WHOLE dataset is old is meta.days_since_data, and
        # every forecast from an archived snapshot carries the `archive_data` warning.
        return {"last_date": _clean(d), "days_old": days, "stale": True if days is None else days > stale_after}

    def entity(r: dict) -> dict:
        return {"entity_id": str(r["entity_id"]), **{k: r.get(k) for k in ENTITY_FIELDS}}

    def get_price(entity_id: str) -> dict:
        _limit_str(entity_id, "entity_id")
        rows = store().q("SELECT * FROM prices WHERE entity_id = ?", [entity_id])
        if not rows:
            raise HTTPException(404, "unknown entity")
        return rows[0]

    # ------------------------------------------------------------------ meta
    @app.get("/api/v1/health")
    def health():
        return {"status": "ok", "version": VERSION}

    @app.get("/api/v1/ready")
    def ready():
        if state["store"] is None:
            return JSONResponse({"ready": False, "reason": "data_unavailable"}, status_code=503)
        m = state["store"].meta
        return {"ready": True, "data_as_of": m["data_as_of"], "model_version": m["model_version"]}

    @app.get("/api/v1/meta")
    def meta():
        s = store()
        m = s.meta
        return {"data_as_of": m["data_as_of"], "generated_at": m["generated_at"],
                "days_since_data": (date.today() - s.data_as_of).days, "data_origin": m["data_origin"],
                "source": m["source"], "model_version": m["model_version"], "horizons": m["horizons"],
                "price_unit": m["price_unit"], "languages": ["en", "ta", "te", "ml", "hi", "kn"],
                "decision_rules_version": m["decision_rules_version"], "refresh": refresh_info()}

    def refresh_info() -> dict | None:
        """Last refresh outcome (no paths or error text: those stay in the server's status file)."""
        if not status_p.exists():
            return None
        try:
            st = json.loads(status_p.read_text())
        except ValueError:
            return None
        return {"last_run_ok": bool(st.get("ok")), "last_success": st.get("last_success"),
                "last_failure": st.get("last_failure"), "failed_step": None if st.get("ok") else st.get("failed_step")}

    @app.get("/api/v1/states")
    def states():
        return store().q("SELECT state, count(DISTINCT market) AS markets, max(arrival_date)::VARCHAR AS last_date "
                         "FROM prices GROUP BY state ORDER BY state")

    @app.get("/api/v1/markets")
    def markets(state: str | None = None, district: str | None = None, q: str | None = None,
                limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
        for n, v in (("state", state), ("district", district), ("q", q)):
            _limit_str(v, n)
        where, p = ["1=1"], []
        if state: where.append("state = ?"); p.append(state)
        if district: where.append("district = ?"); p.append(district)
        if q: where.append("market ILIKE ? ESCAPE '\\'"); p.append(_like(q))
        w = " AND ".join(where)
        total = store().q(f"SELECT count(*) n FROM (SELECT DISTINCT state, district, market FROM prices WHERE {w})", p)[0]["n"]
        items = store().q(f"SELECT state, district, market, count(DISTINCT commodity) AS commodities, "
                          f"max(arrival_date)::VARCHAR AS last_date FROM prices WHERE {w} GROUP BY ALL "
                          f"ORDER BY state, district, market LIMIT {limit} OFFSET {offset}", p)
        return {"total": total, "limit": limit, "offset": offset, "items": items}

    @app.get("/api/v1/commodities")
    def commodities(state: str | None = None, market: str | None = None, q: str | None = None):
        for n, v in (("state", state), ("market", market), ("q", q)):
            _limit_str(v, n)
        where, p = ["1=1"], []
        if state: where.append("p.state = ?"); p.append(state)
        if market: where.append("p.market = ?"); p.append(market)
        if q: where.append("p.commodity ILIKE ? ESCAPE '\\'"); p.append(_like(q))
        rules = load_rules()
        rows = store().q(f"SELECT p.commodity, count(DISTINCT p.market) AS markets, max(p.arrival_date)::VARCHAR AS last_date, "
                         f"bool_or(f.supported) AS forecast_supported FROM prices p LEFT JOIN "
                         f"(SELECT entity_id, supported FROM fc WHERE horizon='h7') f USING (entity_id) "
                         f"WHERE {' AND '.join(where)} GROUP BY 1 ORDER BY markets DESC", p)
        for r in rows:
            r["perishable"] = r["commodity"] in rules["perishable_commodities"]
            r["forecast_supported"] = bool(r["forecast_supported"])
        return rows

    @app.get("/api/v1/prices/latest")
    def prices_latest(state: str | None = None, district: str | None = None, market: str | None = None,
                      commodity: str | None = None, q: str | None = None,
                      limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
        for n, v in (("state", state), ("district", district), ("market", market), ("commodity", commodity), ("q", q)):
            _limit_str(v, n)
        where, p = ["1=1"], []
        for col, v in (("state", state), ("district", district), ("market", market), ("commodity", commodity)):
            if v: where.append(f"p.{col} = ?"); p.append(v)
        if q: where.append("(p.commodity ILIKE ? ESCAPE '\\' OR p.market ILIKE ? ESCAPE '\\')"); p += [_like(q), _like(q)]
        w = " AND ".join(where)
        total = store().q(f"SELECT count(*) n FROM prices p WHERE {w}", p)[0]["n"]
        rows = store().q(f"SELECT p.*, coalesce(f.supported, false) AS fsup FROM prices p LEFT JOIN "
                         f"(SELECT entity_id, supported FROM fc WHERE horizon='h7') f USING (entity_id) WHERE {w} "
                         f"ORDER BY p.arrival_date DESC, p.commodity, p.market LIMIT {limit} OFFSET {offset}", p)
        items = [{"entity": entity(r), "date": _clean(r["arrival_date"]), "min_price": _clean(r["min_price"]),
                  "max_price": _clean(r["max_price"]), "modal_price": _clean(r["modal_price"]), "unit": "INR/quintal",
                  "freshness": freshness(r["arrival_date"]), "change_7d_pct": _clean(r["change_7d_pct"]),
                  "forecast_supported": bool(r["fsup"])} for r in rows]
        return {"total": total, "limit": limit, "offset": offset, "items": items}

    def summary(r: dict, pts: list[dict]) -> dict:
        std = r.get("std30")
        vol = None if std is None or (isinstance(std, float) and math.isnan(std)) else std * 100
        ch30 = None
        if pts:
            cutoff = date.fromordinal(pts[-1]["date"].toordinal() - 30)
            old = [x for x in pts if x["date"] <= cutoff]
            if old:
                ch30 = (pts[-1]["modal"] / old[-1]["modal"] - 1) * 100
        trend = None if ch30 is None else ("rising" if ch30 > 5 else "falling" if ch30 < -5 else "stable")
        level = None if vol is None else ("low" if vol < 5 else "high" if vol > 15 else "medium")
        return {"n_obs_30d": r.get("cnt30"), "change_7d_pct": _clean(r.get("change_7d_pct")), "change_30d_pct": _clean(ch30),
                "trend": trend, "volatility_30d_pct": _clean(vol), "volatility_level": level}

    def history(entity_id: str, days: int) -> list[dict]:
        return store().q("SELECT arrival_date AS date, min_price AS min, max_price AS max, modal_price AS modal FROM hist "
                         "WHERE entity_id = ? AND arrival_date >= ? ORDER BY arrival_date",
                         [entity_id, date.fromordinal(store().data_as_of.toordinal() - days)])

    @app.get("/api/v1/series/{entity_id}")
    def series(entity_id: str, days: int = Query(180, ge=7, le=180)):
        r = get_price(entity_id)
        pts = history(entity_id, days)
        return {"entity": entity(r), "unit": "INR/quintal",
                "points": [{k: _clean(v) for k, v in x.items()} for x in pts],
                "summary": summary(r, pts), "freshness": freshness(r["arrival_date"])}

    def compare_items(r: dict, scope: str = "state", limit: int = 20) -> list[dict]:
        where = "commodity=? AND variety=? AND state=?" + (" AND district=?" if scope == "district" else "")
        p = [r["commodity"], r["variety"], r["state"]] + ([r["district"]] if scope == "district" else [])
        rows = store().q(f"SELECT p.*, f.median AS f7 FROM prices p LEFT JOIN (SELECT entity_id, median FROM fc "
                         f"WHERE horizon='h7' AND supported) f USING (entity_id) WHERE {where} AND entity_id <> ? "
                         f"ORDER BY modal_price DESC LIMIT {limit}", p + [r["entity_id"]])
        max_gap = load_rules()["compare_max_staleness_days"]
        items = [{"entity": entity(x), "modal_price": _clean(x["modal_price"]), "date": _clean(x["arrival_date"]),
                  "diff_pct": _clean((x["modal_price"] / r["modal_price"] - 1) * 100), "freshness": freshness(x["arrival_date"]),
                  "forecast_h7_median": _clean(x["f7"]),
                  # comparable = reported within max_gap days of the reference report
                  "comparable": abs((x["arrival_date"] - r["arrival_date"]).days) <= max_gap} for x in rows]
        items.sort(key=lambda i: (not i["comparable"], -(i["modal_price"] or 0)))
        return items

    @app.get("/api/v1/forecast/{entity_id}")
    def forecast(entity_id: str):
        r = get_price(entity_id)
        s = store()
        rules = load_rules()
        primary = rules["primary_horizon"]
        rows = s.q("SELECT * FROM fc WHERE entity_id = ? ORDER BY horizon_days", [entity_id])
        fr = freshness(r["arrival_date"])
        warnings: list[str] = []
        if s.meta.get("data_origin") == "archive":
            warnings.append("archive_data")
        if fr["stale"]:
            warnings.append("data_stale")
        if not rows:
            reason = ("insufficient_history" if r["commodity"] in s.forecast_commodities else "not_in_forecast_commodities")
            d = decide(r["commodity"], supported=False, unsupported_reason=reason)
            return {"entity": entity(r), "supported": False, "unsupported_reason": reason,
                    "origin": {"date": _clean(r["arrival_date"]), "modal_price": _clean(r["modal_price"])},
                    "freshness": fr, "horizons": [],
                    "decision": {"signal": d.signal, "horizon": None, "reason_codes": d.reason_codes,
                                 "costs": {"holding_cost_pct": 0, "perishable": d.perishable}, "kind": d.kind},
                    "explanation": {}, "warnings": warnings, "model_version": s.meta["model_version"], "source": s.meta["source"]}
        supported = bool(rows[0]["supported"])
        # The forecast is anchored on the latest FEATURE row; show that origin, not a later raw report.
        origin_date, origin_price = rows[0]["origin_date"], rows[0]["origin_price"]
        if origin_date != r["arrival_date"]:
            warnings.append("forecast_origin_differs")
        hs = []
        if supported:
            for x in rows:
                acc = s.accuracy.get((x["commodity"], x["horizon"]), {})
                hs.append({"horizon": x["horizon"], "days": x["horizon_days"],
                           "target_window": [_clean(x["target_from"]), _clean(x["target_to"])],
                           "median": _clean(x["median"]), "lo80": _clean(x["lo80"]), "hi80": _clean(x["hi80"]),
                           "lo90": _clean(x["lo90"]), "hi90": _clean(x["hi90"]),
                           "change_pct": _clean((math.exp(x["pred_log_return"]) - 1) * 100), "model": x["model"],
                           "test_wape_pct": _clean(acc["wape"] * 100) if acc.get("wape") is not None else None,
                           "test_mae_pct_of_price": _clean(acc["wape"] * 100) if acc.get("wape") is not None else None,
                           "test_rel_mae_vs_persistence": _clean(acc.get("rel_mae")),
                           "interval_coverage80_test": _clean(s.coverage.get(x["horizon"]))})
        ph = next((x for x in rows if x["horizon"] == primary), None)
        cmp_items = [{"modal_price": i["modal_price"], "days_old": i["freshness"]["days_old"], "comparable": i["comparable"]}
                     for i in compare_items(r)]
        expired = (ph is not None and date.today() > ph["target_to"]) or \
            (date.today() - s.data_as_of).days > rules["stale_after_days"]
        common = dict(supported=supported and ph is not None, unsupported_reason=rows[0]["unsupported_reason"],
                      stale=fr["stale"], today=origin_price, days=ph["horizon_days"] if ph else None,
                      lo80=ph["lo80"] if ph else None, hi80=ph["hi80"] if ph else None, compare=cmp_items)
        d = decide(r["commodity"], expired=expired, **common)
        decision = {"signal": d.signal, "horizon": d.horizon, "reason_codes": d.reason_codes,
                    "costs": {"holding_cost_pct": d.holding_cost_pct, "perishable": d.perishable}, "kind": d.kind}
        if expired and supported:
            snap = decide(r["commodity"], expired=False, **common)
            # what the rule said on the data date; historical, never shown as current advice
            decision["at_snapshot"] = {"as_of": _clean(origin_date), "signal": snap.signal, "reason_codes": snap.reason_codes}
        x7 = ph or rows[0]
        std = x7["std30"]
        if not rows[0]["in_panel"]:
            warnings.append("sparse_history")
        if std is not None and std * 100 > 15:
            warnings.append("high_volatility")
        if any(h["hi80"] and h["lo80"] and (h["hi80"] - h["lo80"]) / origin_price > 0.5 for h in hs):
            warnings.append("wide_interval")
        pts = history(entity_id, 60)
        summ = summary(r, pts)
        expl = {"recent_trend": summ["trend"], "volatility_level": summ["volatility_level"],
                "seasonal_last_year_change_pct": _clean((math.exp(x7["ly_chg"]) - 1) * 100) if x7["has_ly"] else None,
                "markets_moving_same_way_pct": None,
                "market_vs_30d_avg_pct": _clean((math.exp(x7["cs_dev30"]) - 1) * 100) if x7["cs_dev30"] is not None else None}
        return {"entity": entity(r), "supported": supported, "unsupported_reason": rows[0]["unsupported_reason"],
                "origin": {"date": _clean(origin_date), "modal_price": _clean(origin_price)},
                "freshness": fr, "horizons": hs, "decision": decision,
                "explanation": expl, "warnings": warnings, "model_version": s.meta["model_version"],
                "source": s.meta["source"]}

    @app.get("/api/v1/compare/{entity_id}")
    def compare(entity_id: str, scope: str = Query("state", pattern="^(state|district)$"),
                limit: int = Query(20, ge=1, le=100)):
        r = get_price(entity_id)
        return {"reference": {"entity": entity(r), "modal_price": _clean(r["modal_price"]), "date": _clean(r["arrival_date"])},
                "items": compare_items(r, scope, limit)}

    @app.get("/api/v1/alerts")
    def alerts(state: str | None = None, commodity: str | None = None, days: int = Query(14, ge=1, le=30),
               limit: int = Query(50, ge=1, le=200)):
        _limit_str(state, "state"); _limit_str(commodity, "commodity")
        where, p = ["arrival_date >= ?"], [date.fromordinal(store().data_as_of.toordinal() - days)]
        if state: where.append("state = ?"); p.append(state)
        if commodity: where.append("commodity = ?"); p.append(commodity)
        rows = store().q(f"SELECT * FROM alerts WHERE {' AND '.join(where)} ORDER BY arrival_date DESC, abs(log_dev) DESC LIMIT {limit}", p)
        return {"items": [{"entity": entity(x), "date": _clean(x["arrival_date"]), "modal_price": _clean(x["modal_price"]),
                           "type": x["type"], "log_dev": _clean(x["log_dev"]), "robust_z": _clean(x["robust_z"]),
                           "ref_mean_price": _clean(x["ref_mean_price"])} for x in rows]}

    @app.get("/api/v1/trends")
    def trends(state: str = Query(..., min_length=2, max_length=MAX_Q), limit: int = Query(10, ge=1, le=50)):
        rows = store().q("SELECT commodity, median(change_7d_pct) AS ch, count(*) AS markets FROM prices "
                         "WHERE state = ? AND change_7d_pct IS NOT NULL AND arrival_date >= ? GROUP BY 1 HAVING count(*) >= 3",
                         [state, date.fromordinal(store().data_as_of.toordinal() - 14)])
        rows = [{"commodity": x["commodity"], "median_change_7d_pct": _clean(x["ch"]), "markets": x["markets"]} for x in rows]
        return {"state": state, "as_of": store().meta["data_as_of"],
                "rising": sorted([x for x in rows if x["median_change_7d_pct"] > 0], key=lambda x: -x["median_change_7d_pct"])[:limit],
                "falling": sorted([x for x in rows if x["median_change_7d_pct"] < 0], key=lambda x: x["median_change_7d_pct"])[:limit]}

    adir = app_dir if app_dir is not None else os.environ.get("AGRI_APP_DIR", "app")
    if adir and Path(adir).is_dir():
        app.mount("/", StaticFiles(directory=adir, html=True), name="app")
    return app


app = create_app()
