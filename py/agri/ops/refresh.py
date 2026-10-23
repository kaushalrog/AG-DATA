"""Idempotent scheduled refresh: official back-fill -> silver v2 -> features -> staged gold -> validate -> atomic swap.

    python -m agri.ops.refresh                      # normal daily run (needs AGRI_DATA_GOV_IN_API_KEY)
    python -m agri.ops.refresh --dry-run            # show the plan, run nothing
    python -m agri.ops.refresh --skip-fetch         # rebuild/publish from data already landed

Guarantees
* **Single run at a time.** An exclusive `flock` on `data/refresh/.lock`; a second run exits with code 75.
* **Idempotent.** The back-fill skips completed days, except the last `--revision-days` days, which are re-fetched to pick up revisions. Silver, features and gold are rebuilt from scratch.
* **A failed refresh never changes what is served.** Gold is published to `data/gold_releases/<run_id>/` and validated there. `data/gold` is a symlink, switched with one atomic `os.replace` only after validation passes. On failure the symlink is untouched, the status is `ok=false`, and an alert is written (plus a webhook and a macOS notification if configured).
* **Honest freshness.** Validation rejects a release whose `data_as_of` is older than the live one. `results/refresh/status.json` records `data_as_of`, `model_version`, `last_success` and `last_failure`. The API exposes them in `/meta`, so the app's stale-data banner (`days_since_data > 3`) appears automatically when refreshes keep failing.
* **Model-version tracking.** Every release records the experiment id it was scored with, and validation checks that the model artifacts for that id exist.

Retries: network steps (the back-fill) are retried `--retries` times with exponential back-off, and the adapter itself also retries each request. Spark steps are retried once.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

log = logging.getLogger("agri.refresh")

ROOT = Path(os.environ.get("AGRI_PROJECT_HOME", Path(__file__).resolve().parents[3]))
GOLD_LINK = ROOT / "data" / "gold"
RELEASES = ROOT / "data" / "gold_releases"
STATE = ROOT / "results" / "refresh"
LOCK = ROOT / "data" / "refresh" / ".lock"
# Serving model. fc_lgbm_2025 replaced fc_main_v3 on 2026-10-23 under docs/PREREG_LGBM_SWITCH.md;
# set AGRI_SERVING_MODEL=fc_main_v3 to roll back.
MODEL_EXP = os.environ.get("AGRI_SERVING_MODEL", "fc_lgbm_2025")
CUTOFF = "2025-10-01"


class RefreshError(RuntimeError):
    def __init__(self, step: str, msg: str):
        super().__init__(f"{step}: {msg}")
        self.step = step


@dataclass
class Step:
    name: str
    cmd: list[str]
    env: dict = field(default_factory=dict)
    retries: int = 0
    timeout_s: int = 6 * 3600


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_step(step: Step, runner: Callable[[Step], int], logf) -> None:
    for attempt in range(step.retries + 1):
        logf.write(f"\n== {now_iso()} {step.name} attempt {attempt + 1}: {' '.join(step.cmd)}\n"); logf.flush()
        rc = runner(step)
        if rc == 0:
            return
        if attempt < step.retries:
            delay = min(600, 30 * 2 ** attempt)
            log.warning("%s failed (rc=%s); retrying in %ss", step.name, rc, delay)
            time.sleep(delay if os.environ.get("AGRI_REFRESH_NO_SLEEP") != "1" else 0)
    raise RefreshError(step.name, f"exit code {rc} after {step.retries + 1} attempt(s)")


def subprocess_runner(logf):
    def _run(step: Step) -> int:
        env = os.environ.copy(); env.update(step.env)
        try:
            return subprocess.run(step.cmd, cwd=ROOT, env=env, stdout=logf, stderr=subprocess.STDOUT,
                                  timeout=step.timeout_s).returncode
        except subprocess.TimeoutExpired:
            return 124
    return _run


def plan(run_dir: Path, today: date, revision_days: int, skip_fetch: bool) -> list[Step]:
    py = [sys.executable, "-m"]
    pyenv = {"PYTHONPATH": str(ROOT / "py")}
    steps: list[Step] = []
    if not skip_fetch:
        end = today - timedelta(days=1)
        steps.append(Step("backfill_new_days", py + ["agri.ingest.backfill", "--from", CUTOFF, "--to", end.isoformat()],
                          pyenv, retries=2))
        steps.append(Step("refetch_revision_window", py + ["agri.ingest.backfill", "--refresh", "--from",
                          (end - timedelta(days=revision_days - 1)).isoformat(), "--to", end.isoformat()], pyenv, retries=2))
    spark_env = {"AGRI_SILVER_DAILY": "data/processed/daily_market_prices_v2", "AGRI_FORECAST_ROOT": "data/forecast_v2"}
    steps.append(Step("silver_v2", ["scripts/submit.sh", "com.agribigdata.ingestion.IngestLanding", f"cutoff={CUTOFF}"], retries=1))
    steps.append(Step("features_v2", ["scripts/submit.sh", "com.agribigdata.forecast.BuildForecastFeatures"],
                      spark_env | {"AGRI_HISTORY_START": "2023-10-01", "AGRI_PANEL_FROM": "data/forecast/panel_entities",
                                   "AGRI_RESULTS_ROOT": "results/forecast_v2"}, retries=1))
    serving = serving_manifest()
    models = serving.get("models_path", f"data/forecast/models/{MODEL_EXP}")
    publish = ["scripts/submit.sh", "com.agribigdata.forecast.ForecastPublish", f"exp={MODEL_EXP}", "origin=official", f"models={models}"]
    if "lgbm" in serving.get("selected_on_validation", {}).values():
        # LightGBM is scored outside Spark on the freshly built features; the publish joins the predictions
        preds = str(ROOT / "data" / "refresh" / run_dir.name / "lgbm_predictions.parquet")
        steps.append(Step("score_lgbm", py + ["agri.forecast.lgbm", "score", "--exp", MODEL_EXP, "--features-root", "data/forecast_v2",
                                             "--models-root", str(Path(models).parent), "--out", preds], pyenv, retries=1))
        publish.append(f"lgbmPredictions={preds}")
    steps.append(Step("publish_staged", publish, spark_env | {"AGRI_GOLD_ROOT": str(run_dir)}, retries=1))
    return steps


def serving_manifest(model_exp: str | None = None) -> dict:
    model_exp = model_exp or MODEL_EXP
    p = ROOT / os.environ.get("AGRI_RESULTS_ROOT", "results/forecast") / model_exp / "manifest.json"
    return json.loads(p.read_text()) if p.exists() else {}


def validate_release(release: Path, live: Path | None, model_exp: str | None = None) -> dict:
    """Raises RefreshError if the staged gold must not be served."""
    model_exp = model_exp or MODEL_EXP
    import duckdb
    meta_p = release / "meta.json"
    if not meta_p.exists():
        raise RefreshError("validate", "meta.json missing")
    meta = json.loads(meta_p.read_text())
    if meta.get("model_version") != model_exp:
        raise RefreshError("validate", f"model_version {meta.get('model_version')} != {model_exp}")
    mp = serving_manifest(model_exp).get("models_path")
    models = ROOT / mp if mp else Path(os.environ.get("AGRI_MODELS_ROOT", ROOT / "data" / "forecast" / "models")) / model_exp
    if not models.exists():
        raise RefreshError("validate", f"model artifacts for {model_exp} not found")
    if live is not None and (live / "meta.json").exists():
        prev = json.loads((live / "meta.json").read_text())["data_as_of"]
        if meta["data_as_of"] < prev:
            raise RefreshError("validate", f"data_as_of {meta['data_as_of']} is older than live {prev}")
    con = duckdb.connect()
    n_prices = con.execute(f"SELECT count(*) FROM read_parquet('{release}/latest_prices/*.parquet')").fetchone()[0]
    n_fc, bad = con.execute(f"""SELECT count(*) FILTER (WHERE supported), count(*) FILTER (WHERE supported AND NOT
        (lo90 <= lo80 AND lo80 <= median AND median <= hi80 AND hi80 <= hi90 AND lo80 > 0))
        FROM read_parquet('{release}/latest_forecasts/*.parquet')""").fetchone()
    min_prices = int(os.environ.get("AGRI_REFRESH_MIN_PRICES", "10000"))
    min_fc = int(os.environ.get("AGRI_REFRESH_MIN_FORECASTS", "4000"))
    if n_prices < min_prices or n_fc < min_fc:
        raise RefreshError("validate", f"too few rows: latest_prices={n_prices} (min {min_prices}), supported forecasts={n_fc} (min {min_fc})")
    if bad:
        raise RefreshError("validate", f"{bad} forecasts with mis-ordered intervals")
    return {"data_as_of": meta["data_as_of"], "model_version": meta["model_version"], "latest_prices": n_prices,
            "supported_forecasts": n_fc // 4 if n_fc else 0}


def swap_gold(release: Path, link: Path | None = None) -> Path | None:
    """Atomically points `link` at `release`. A plain directory at `link` is first moved into releases/."""
    link = link or GOLD_LINK
    prev = None
    if link.is_symlink():
        prev = link.resolve()
    elif link.exists():  # first run: adopt the existing directory as a release
        prev = link.parent / "gold_releases" / f"adopted_{datetime.now().strftime('%Y%m%dT%H%M%S')}"
        prev.parent.mkdir(parents=True, exist_ok=True)
        link.rename(prev)
    tmp = link.with_name(link.name + ".next")
    if tmp.is_symlink() or tmp.exists():
        tmp.unlink()
    tmp.symlink_to(release.resolve(), target_is_directory=True)
    os.replace(tmp, link)  # atomic on POSIX
    return prev


def prune(keep: int = 3) -> None:
    if not RELEASES.exists():
        return
    live = GOLD_LINK.resolve() if GOLD_LINK.is_symlink() else None
    rel = sorted([p for p in RELEASES.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
    for p in rel[keep:]:
        if p != live:
            shutil.rmtree(p, ignore_errors=True)


def alert(status: dict) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    line = json.dumps({"at": now_iso(), "run_id": status["run_id"], "step": status.get("failed_step"), "error": status.get("error")})
    with open(STATE / "alerts.log", "a") as f:
        f.write(line + "\n")
    hook = os.environ.get("AGRI_ALERT_WEBHOOK")
    if hook:
        try:
            req = urllib.request.Request(hook, data=json.dumps({"text": f"AG-DATA refresh failed: {status.get('error')}"}).encode(),
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:  # an alert failure must not mask the refresh failure
            log.error("webhook alert failed: %s", e)
    if sys.platform == "darwin" and os.environ.get("AGRI_ALERT_MACOS") == "1":
        subprocess.run(["osascript", "-e", f'display notification "refresh failed at {status.get("failed_step")}" with title "AG-DATA"'],
                       check=False)


def write_status(status: dict) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    prev = json.loads((STATE / "status.json").read_text()) if (STATE / "status.json").exists() else {}
    if status["ok"]:
        status["last_success"] = status["finished_at"]
        status["last_failure"] = prev.get("last_failure")
    else:
        status["last_success"] = prev.get("last_success")
        status["last_failure"] = status["finished_at"]
        # what is still being served
        status["serving_data_as_of"] = prev.get("serving_data_as_of", prev.get("data_as_of"))
        status["serving_model_version"] = prev.get("serving_model_version", prev.get("model_version"))
    if status["ok"]:
        status["serving_data_as_of"], status["serving_model_version"] = status["data_as_of"], status["model_version"]
    tmp = STATE / "status.json.tmp"
    tmp.write_text(json.dumps(status, indent=1))
    os.replace(tmp, STATE / "status.json")
    with open(STATE / "history.jsonl", "a") as f:
        f.write(json.dumps(status) + "\n")


def refresh(today: date | None = None, revision_days: int = 3, skip_fetch: bool = False, dry_run: bool = False,
            runner_factory=subprocess_runner, validator=validate_release) -> dict:
    today = today or date.today()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = RELEASES / run_id
    n = 0
    while run_dir.exists():  # never reuse a directory, least of all the live release
        n += 1
        run_dir = RELEASES / f"{run_id}_{n}"
    steps = plan(run_dir, today, revision_days, skip_fetch)
    if dry_run:
        return {"run_id": run_id, "plan": [{"name": s.name, "cmd": " ".join(s.cmd), "env": s.env} for s in steps]}
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    lockf = open(LOCK, "w")
    try:
        fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit(75)
    STATE.mkdir(parents=True, exist_ok=True)
    status = {"run_id": run_id, "started_at": now_iso(), "ok": False, "release": str(run_dir)}
    logp = STATE / f"run_{run_id}.log"
    with open(logp, "w") as logf:
        try:
            run_dir.mkdir(parents=True, exist_ok=True)
            runner = runner_factory(logf)
            for s in steps:
                run_step(s, runner, logf)
            live = GOLD_LINK.resolve() if GOLD_LINK.exists() else None
            status.update(validator(run_dir, live))
            prev = swap_gold(run_dir)
            status.update({"ok": True, "previous_release": str(prev) if prev else None})
            prune()
        except RefreshError as e:
            status.update({"failed_step": e.step, "error": str(e)})
        except Exception as e:  # unexpected: still never swap
            status.update({"failed_step": "unexpected", "error": f"{type(e).__name__}: {e}"})
    status["finished_at"] = now_iso()
    status["log"] = str(logp)
    live_target = GOLD_LINK.resolve() if GOLD_LINK.is_symlink() else None
    if not status["ok"] and run_dir.resolve() != live_target:
        shutil.rmtree(run_dir, ignore_errors=True)  # never leave a half-built release behind (and never touch the live one)
        alert(status)
    write_status(status)
    fcntl.flock(lockf, fcntl.LOCK_UN)
    return status


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--revision-days", type=int, default=3)
    ap.add_argument("--skip-fetch", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    st = refresh(revision_days=a.revision_days, skip_fetch=a.skip_fetch, dry_run=a.dry_run)
    print(json.dumps(st, indent=1))
    return 0 if a.dry_run or st.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
