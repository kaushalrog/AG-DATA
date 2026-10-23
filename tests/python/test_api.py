"""API contract tests against a tiny SYNTHETIC gold layer written to a temp dir (never real data)."""
import json
import math
from datetime import date, timedelta

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from fastapi.testclient import TestClient

from agri.api.app import create_app

AS_OF = date(2026, 4, 21)


def write(path, rows):
    path.mkdir(parents=True)
    pq.write_table(pa.Table.from_pylist(rows), path / "part-0.parquet")


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    g = tmp_path_factory.mktemp("gold")
    ent = lambda i, m, c="Tomato", d="Salem": dict(entity_id=str(1000 + i), state="Tamil Nadu", district=d, market=m,
                                                  market_raw=m, commodity=c, variety="Hybrid", grade="FAQ")
    prices = [
        {**ent(1, "Salem"), "arrival_date": AS_OF, "min_price": 900.0, "max_price": 1100.0, "modal_price": 1000.0,
         "days_old": 0, "change_7d_pct": 5.0, "cnt30": 20, "std30": 0.08},
        {**ent(2, "Attur"), "arrival_date": AS_OF - timedelta(days=1), "min_price": 1100.0, "max_price": 1300.0,
         "modal_price": 1200.0, "days_old": 1, "change_7d_pct": 2.0, "cnt30": 18, "std30": 0.07},
        {**ent(3, "Omalur"), "arrival_date": AS_OF - timedelta(days=20), "min_price": 1400.0, "max_price": 1600.0,
         "modal_price": 1500.0, "days_old": 20, "change_7d_pct": None, "cnt30": 2, "std30": None},
        {**ent(4, "Salem", c="Saffron"), "arrival_date": AS_OF, "min_price": 1.0, "max_price": 2.0, "modal_price": 1.5,
         "days_old": 0, "change_7d_pct": None, "cnt30": 5, "std30": 0.01},
    ]
    write(g / "latest_prices", prices)
    write(g / "price_history", [dict(entity_id="1001", arrival_date=AS_OF - timedelta(days=k), min_price=900.0,
                                     max_price=1100.0, modal_price=1000.0 * (1 - 0.003 * k)) for k in range(60)])
    fc = []
    for eid, sup, inp in (("1001", True, True), ("1002", True, True), ("1003", False, False)):
        for h, d, lo, hi, pred in (("next", 1, -0.05, 0.05, 0.0), ("h3", 3, -0.08, 0.1, 0.01),
                                   ("h7", 7, 0.10, 0.30, 0.2), ("h14", 14, -0.2, 0.3, 0.05)):
            fc.append(dict(entity_id=eid, commodity="Tomato", origin_date=AS_OF, origin_price=1000.0, horizon=h,
                           horizon_days=d, target_from=AS_OF + timedelta(days=d), target_to=AS_OF + timedelta(days=d + 3),
                           median=1000 * math.exp(pred), lo80=1000 * math.exp(lo), hi80=1000 * math.exp(hi),
                           lo90=1000 * math.exp(lo - 0.05), hi90=1000 * math.exp(hi + 0.05), pred_log_return=pred,
                           lo80_log=lo, hi80_log=hi, model="gbt", supported=sup,
                           unsupported_reason=None if sup else "insufficient_history", in_panel=inp, std30=0.08,
                           cnt30=20, cs_dev30=0.02, ly_chg=0.05, has_ly=1.0, days_old=0))
    write(g / "latest_forecasts", fc)
    write(g / "alerts", [dict(entity_id="1002", state="Tamil Nadu", district="Salem", market="Attur", commodity="Tomato",
                              variety="Hybrid", grade="FAQ", arrival_date=AS_OF, modal_price=2400.0, type="price_spike",
                              log_dev=0.7, robust_z=6.0, ref_mean_price=1190.0)])
    (g / "meta.json").write_text(json.dumps({
        "data_as_of": AS_OF.isoformat(), "generated_at": "2026-10-22T00:00:00Z", "data_origin": "archive",
        "model_version": "test_exp", "horizons": ["next", "h3", "h7", "h14"], "price_unit": "INR/quintal",
        "decision_rules_version": "t", "source": {"name": "synthetic fixture", "licence": "n/a", "url": ""}}))
    return TestClient(create_app(gold=str(g), results=str(tmp_path_factory.mktemp("res")), app_dir=""))


def test_health_ready_meta(client):
    assert client.get("/api/v1/health").json()["status"] == "ok"
    r = client.get("/api/v1/ready")
    assert r.status_code == 200 and r.json()["data_as_of"] == "2026-04-21"
    m = client.get("/api/v1/meta").json()
    assert m["data_origin"] == "archive" and m["days_since_data"] > 3 and len(m["languages"]) == 6
    assert r.headers["X-Data-As-Of"] == "2026-04-21"


def test_not_ready_without_gold(tmp_path):
    c = TestClient(create_app(gold=str(tmp_path / "missing"), results=str(tmp_path), app_dir=""))
    assert c.get("/api/v1/ready").status_code == 503
    r = c.get("/api/v1/meta")
    assert r.status_code == 503 and r.json()["error"]["code"] == "unavailable"
    assert "missing" not in r.text  # no paths leaked


def test_latest_prices_paging_and_freshness(client):
    r = client.get("/api/v1/prices/latest", params={"state": "Tamil Nadu", "limit": 2}).json()
    assert r["total"] == 4 and len(r["items"]) == 2
    stale = client.get("/api/v1/prices/latest", params={"q": "Omalur"}).json()["items"][0]
    assert stale["freshness"] == {"last_date": "2026-04-01", "days_old": 20, "stale": True}
    assert isinstance(stale["entity"]["entity_id"], str)


def test_empty_search(client):
    assert client.get("/api/v1/prices/latest", params={"q": "zzzz"}).json() == {"total": 0, "limit": 50, "offset": 0, "items": []}


def test_input_validation(client):
    assert client.get("/api/v1/prices/latest", params={"q": "x" * 200}).status_code == 400
    assert client.get("/api/v1/prices/latest", params={"limit": 10_000}).status_code == 422
    assert client.get("/api/v1/series/does-not-exist").status_code == 404


def test_series_summary(client):
    s = client.get("/api/v1/series/1001").json()
    assert s["points"][0]["date"] < s["points"][-1]["date"]
    assert s["summary"]["trend"] == "rising" and s["summary"]["volatility_level"] == "medium"


def test_forecast_payload_and_decision(client):
    f = client.get("/api/v1/forecast/1001").json()
    assert f["supported"] and [h["horizon"] for h in f["horizons"]] == ["next", "h3", "h7", "h14"]
    h7 = f["horizons"][2]
    assert h7["lo80"] < h7["median"] < h7["hi80"] and "lo80_log" not in h7
    # the fixture's data date (2026-04-21) is long past: the card must not give present-tense advice
    assert f["decision"]["signal"] == "WATCH" and f["decision"]["reason_codes"] == ["forecast_expired"]
    assert f["decision"]["kind"] == "market_outlook"
    # what the rule said on the data date is kept, labelled historical: lo80(h7)=+10.5% >= cost 6% -> HOLD
    assert f["decision"]["at_snapshot"] == {"as_of": "2026-04-21", "signal": "HOLD",
                                            "reason_codes": ["lower_bound_above_cost", "perishable_cost_applied"]}
    assert "archive_data" in f["warnings"]


def test_forecast_unsupported_and_unknown_commodity(client):
    f = client.get("/api/v1/forecast/1003").json()
    assert not f["supported"] and f["horizons"] == [] and f["decision"]["signal"] == "WATCH"
    g = client.get("/api/v1/forecast/1004").json()
    assert g["unsupported_reason"] == "not_in_forecast_commodities" and g["decision"]["reason_codes"] == []


def test_compare_marks_stale_markets_not_comparable(client):
    c = client.get("/api/v1/compare/1001").json()
    by = {i["entity"]["market"]: i for i in c["items"]}
    assert by["Attur"]["comparable"] and not by["Omalur"]["comparable"]
    assert c["items"][0]["entity"]["market"] == "Attur"  # stale never ranked above fresh


def test_alerts_and_trends(client):
    a = client.get("/api/v1/alerts", params={"state": "Tamil Nadu"}).json()["items"]
    assert a[0]["type"] == "price_spike"
    t = client.get("/api/v1/trends", params={"state": "Tamil Nadu"}).json()
    assert "rising" in t and "falling" in t


def test_rate_limit(tmp_path, monkeypatch, client):
    monkeypatch.setenv("AGRI_API_RATE_PER_MIN", "3")
    c = TestClient(create_app(gold=str(tmp_path), results=str(tmp_path), app_dir=""))
    codes = [c.get("/api/v1/health").status_code for _ in range(5)]
    assert codes[:3] == [200] * 3 and 429 in codes


def test_rate_limit_behind_proxy_is_per_visitor_only_when_trusted(tmp_path, monkeypatch, client):
    monkeypatch.setenv("AGRI_API_RATE_PER_MIN", "3")
    def codes(c):
        return [c.get("/api/v1/health", headers={"X-Forwarded-For": f"203.0.113.{i}, 10.0.0.1"}).status_code for i in range(6)]
    # without trust, a spoofable header must not bypass the limit
    assert 429 in codes(TestClient(create_app(gold=str(tmp_path), results=str(tmp_path), app_dir="")))
    monkeypatch.setenv("AGRI_API_TRUST_PROXY", "1")  # each visitor has its own budget behind the proxy
    assert codes(TestClient(create_app(gold=str(tmp_path), results=str(tmp_path), app_dir=""))) == [200] * 6


def test_cors_only_allows_configured_origin(client):
    ok = client.get("/api/v1/health", headers={"Origin": "http://localhost:8000"})
    bad = client.get("/api/v1/health", headers={"Origin": "https://evil.example"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:8000"
    assert "access-control-allow-origin" not in bad.headers


def test_like_escaping(client):
    assert client.get("/api/v1/prices/latest", params={"q": "%"}).json()["total"] == 0


def test_ready_does_not_leak_exception_class(tmp_path):
    c = TestClient(create_app(gold=str(tmp_path / "missing"), results=str(tmp_path), app_dir=""))
    assert c.get("/api/v1/ready").json() == {"ready": False, "reason": "data_unavailable"}
