"""Refresh workflow guarantees, with fake steps (no Spark, no network)."""
import fcntl
import json
import math
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from agri.ops import refresh as R


def make_gold(d: Path, as_of="2026-10-22", model="fc_main_v3", n_prices=5, n_fc=2, bad=False):
    (d / "latest_prices").mkdir(parents=True)
    pq.write_table(pa.Table.from_pylist([{"entity_id": str(i), "modal_price": 1.0} for i in range(n_prices)]),
                   d / "latest_prices" / "p.parquet")
    (d / "latest_forecasts").mkdir()
    rows = []
    for i in range(n_fc):
        for h in ("next", "h3", "h7", "h14"):
            lo80 = 90.0 if not bad else 120.0
            rows.append(dict(entity_id=str(i), horizon=h, supported=True, lo90=80.0, lo80=lo80, median=100.0, hi80=110.0, hi90=120.0))
    pq.write_table(pa.Table.from_pylist(rows), d / "latest_forecasts" / "f.parquet")
    (d / "meta.json").write_text(json.dumps({"data_as_of": as_of, "model_version": model}))


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "ROOT", tmp_path)
    monkeypatch.setattr(R, "GOLD_LINK", tmp_path / "data" / "gold")
    monkeypatch.setattr(R, "RELEASES", tmp_path / "data" / "gold_releases")
    monkeypatch.setattr(R, "STATE", tmp_path / "results" / "refresh")
    monkeypatch.setattr(R, "LOCK", tmp_path / "data" / "refresh" / ".lock")
    monkeypatch.setenv("AGRI_MODELS_ROOT", str(tmp_path / "models"))
    monkeypatch.setenv("AGRI_REFRESH_MIN_PRICES", "1")
    monkeypatch.setenv("AGRI_REFRESH_MIN_FORECASTS", "1")
    monkeypatch.setenv("AGRI_REFRESH_NO_SLEEP", "1")
    (tmp_path / "models" / "fc_main_v3").mkdir(parents=True)
    live = tmp_path / "data" / "gold"
    make_gold(live, as_of="2026-10-20")  # a plain directory, as on first deployment
    return tmp_path


def runner_that(fail_step=None, publish=lambda d: make_gold(d)):
    def factory(logf):
        def run(step):
            if step.name == fail_step:
                return 1
            if step.name == "publish_staged":
                publish(Path(step.env["AGRI_GOLD_ROOT"]))
            return 0
        return run
    return factory


def served(env):
    return json.loads((env / "data" / "gold" / "meta.json").read_text())["data_as_of"]


def test_success_swaps_atomically_and_records_status(env):
    st = R.refresh(today=date(2026, 10, 23), runner_factory=runner_that())
    assert st["ok"] and served(env) == "2026-10-22"
    assert (env / "data" / "gold").is_symlink()
    status = json.loads((env / "results" / "refresh" / "status.json").read_text())
    assert status["serving_data_as_of"] == "2026-10-22" and status["serving_model_version"] == "fc_main_v3"
    assert status["last_success"] and not (env / "results" / "refresh" / "alerts.log").exists()
    # the previous directory was adopted as a release, not deleted
    assert any(p.name.startswith("adopted_") for p in (env / "data" / "gold_releases").iterdir())


@pytest.mark.parametrize("step", ["backfill_new_days", "silver_v2", "features_v2", "publish_staged"])
def test_failed_step_never_changes_served_gold_and_alerts(env, step):
    st = R.refresh(today=date(2026, 10, 23), runner_factory=runner_that(fail_step=step))
    assert not st["ok"] and st["failed_step"] == step
    assert served(env) == "2026-10-20"
    assert not Path(st["release"]).exists()  # half-built release removed
    assert json.loads((env / "results" / "refresh" / "alerts.log").read_text().splitlines()[-1])["step"] == step


def test_validation_rejects_older_data(env):
    st = R.refresh(today=date(2026, 10, 23), runner_factory=runner_that(publish=lambda d: make_gold(d, as_of="2026-10-01")))
    assert not st["ok"] and "older than live" in st["error"] and served(env) == "2026-10-20"


def test_validation_rejects_bad_intervals_and_wrong_model(env):
    st = R.refresh(today=date(2026, 10, 23), runner_factory=runner_that(publish=lambda d: make_gold(d, bad=True)))
    assert not st["ok"] and "mis-ordered" in st["error"]
    st = R.refresh(today=date(2026, 10, 23), runner_factory=runner_that(publish=lambda d: make_gold(d, model="other")))
    assert not st["ok"] and "model_version" in st["error"] and served(env) == "2026-10-20"


def test_status_after_failure_keeps_last_success_and_serving_info(env):
    R.refresh(today=date(2026, 10, 23), runner_factory=runner_that())
    R.refresh(today=date(2026, 10, 24), runner_factory=runner_that(fail_step="silver_v2"))
    status = json.loads((env / "results" / "refresh" / "status.json").read_text())
    assert status["ok"] is False and status["last_success"] and status["last_failure"]
    assert status["serving_data_as_of"] == "2026-10-22"
    assert len((env / "results" / "refresh" / "history.jsonl").read_text().splitlines()) == 2


def test_concurrent_run_is_refused(env):
    R.LOCK.parent.mkdir(parents=True, exist_ok=True)
    with open(R.LOCK, "w") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        with pytest.raises(SystemExit) as e:
            R.refresh(today=date(2026, 10, 23), runner_factory=runner_that())
        assert e.value.code == 75
    assert served(env) == "2026-10-20"


def test_dry_run_plan_refetches_revision_window(env):
    p = R.refresh(today=date(2026, 10, 23), dry_run=True)["plan"]
    names = [s["name"] for s in p]
    assert names == ["backfill_new_days", "refetch_revision_window", "silver_v2", "features_v2", "publish_staged"]
    assert "--refresh" in p[1]["cmd"] and "2026-10-20" in p[1]["cmd"] and "2026-10-22" in p[1]["cmd"]


def test_api_reloads_when_release_switches_and_reports_refresh(env, monkeypatch):
    from fastapi.testclient import TestClient
    from agri.api.app import create_app
    monkeypatch.setenv("AGRI_REFRESH_STATUS", str(env / "results" / "refresh" / "status.json"))
    R.refresh(today=date(2026, 10, 23), runner_factory=runner_that(publish=lambda d: full_gold(d, "2026-10-22")))
    c = TestClient(create_app(gold=str(env / "data" / "gold"), results=str(env / "res"), app_dir=""))
    assert c.get("/api/v1/ready").json()["data_as_of"] == "2026-10-22"
    R.refresh(today=date(2026, 10, 24), runner_factory=runner_that(publish=lambda d: full_gold(d, "2026-10-23")))
    assert c.get("/api/v1/ready").json()["data_as_of"] == "2026-10-23"
    assert c.get("/api/v1/meta").json()["refresh"]["last_run_ok"] is True
    R.refresh(today=date(2026, 10, 25), runner_factory=runner_that(fail_step="features_v2"))
    m = c.get("/api/v1/meta").json()
    assert m["data_as_of"] == "2026-10-23" and m["refresh"] == {"last_run_ok": False, "last_success": m["refresh"]["last_success"],
                                                               "last_failure": m["refresh"]["last_failure"], "failed_step": "features_v2"}


def full_gold(d: Path, as_of: str):
    """Gold layer complete enough for the API (and the validator)."""
    make_gold(d, as_of=as_of)
    meta = json.loads((d / "meta.json").read_text())
    meta.update({"generated_at": "x", "data_origin": "official", "horizons": ["next", "h3", "h7", "h14"],
                 "price_unit": "INR/quintal", "decision_rules_version": "t", "source": {"name": "t", "licence": "t", "url": ""}})
    (d / "meta.json").write_text(json.dumps(meta))
    for t in ("price_history", "alerts"):
        (d / t).mkdir()
    pq.write_table(pa.Table.from_pylist([{"entity_id": "0", "arrival_date": date(2026, 10, 1), "min_price": 1.0, "max_price": 2.0,
                                          "modal_price": 1.5}]), d / "price_history" / "h.parquet")
    pq.write_table(pa.Table.from_pylist([{"entity_id": "0", "arrival_date": date(2026, 10, 1), "type": "price_spike"}]),
                   d / "alerts" / "a.parquet")
    pq.write_table(pa.Table.from_pylist([{"entity_id": str(i), "modal_price": 1.0, "arrival_date": date(2026, 10, 1)} for i in range(5)]),
                   d / "latest_prices" / "p.parquet")
    rows = [dict(entity_id="0", commodity="Tomato", horizon=h, horizon_days=k, supported=True, lo90=80.0, lo80=90.0,
                 median=100.0, hi80=110.0, hi90=120.0) for h, k in (("next", 1), ("h3", 3), ("h7", 7), ("h14", 14))]
    pq.write_table(pa.Table.from_pylist(rows), d / "latest_forecasts" / "f.parquet")


def test_back_to_back_runs_never_share_or_delete_the_live_release(env):
    a = R.refresh(today=date(2026, 10, 23), runner_factory=runner_that())
    b = R.refresh(today=date(2026, 10, 23), runner_factory=runner_that(fail_step="publish_staged"))
    assert a["release"] != b["release"]
    assert Path(a["release"]).exists() and served(env) == "2026-10-22"
