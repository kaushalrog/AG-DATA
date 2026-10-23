"""Resumable, idempotent historical backfill from the data.gov.in variety-wise resource.

    AGRI_DATA_GOV_IN_API_KEY=... python -m agri.ingest.backfill --from 2025-11-01 --to 2026-10-22

One request series per arrival date (filters[Arrival_Date]=dd/mm/yyyy), 5,000 records per
page, >= 1 s between requests. Each date is written to
    data/ingest/landing/datagovin_variety/arrival_date=YYYY-MM-DD/part-0.ndjson.gz
via a temporary file and an atomic rename, followed by a _SUCCESS marker. Re-running skips
completed dates, so an interrupted backfill resumes where it stopped, and re-fetching a
date (--refresh) replaces it atomically. Events carry data_origin="backfill" and the
resource id in `source`. A JSON manifest of the run is written to results/ingest/.
"""
from __future__ import annotations

import argparse
import gzip
import json
import logging
import os
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .datagovin import VARIETY_HISTORY, DataGovInClient, MissingCredentials

log = logging.getLogger("agri.ingest.backfill")
LANDING = Path(os.environ.get("AGRI_LANDING", "data/ingest/landing/datagovin_variety"))


def day_dir(d: date) -> Path:
    return LANDING / f"arrival_date={d.isoformat()}"


def fetch_day(client: DataGovInClient, d: date) -> dict:
    out = day_dir(d)
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / "part-0.ndjson.gz.tmp"
    n, flags = 0, {}
    t0 = time.monotonic()
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        # resume=False: a day is fetched as a whole; completeness is marked by _SUCCESS
        for ev in client.fetch_all({"arrival_date": d.strftime("%d/%m/%Y")}, resume=False, data_origin="backfill"):
            f.write(ev.to_json() + "\n")
            n += 1
            flags[ev.quality_flag] = flags.get(ev.quality_flag, 0) + 1
    tmp.replace(out / "part-0.ndjson.gz")
    meta = {"arrival_date": d.isoformat(), "records": n, "quality": flags, "seconds": round(time.monotonic() - t0, 1),
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "resource": client.resource_id}
    (out / "_SUCCESS").write_text(json.dumps(meta))
    return meta


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", type=date.fromisoformat, required=True)
    ap.add_argument("--to", dest="end", type=date.fromisoformat, required=True)
    ap.add_argument("--refresh", action="store_true", help="re-fetch dates that already completed")
    ap.add_argument("--page-size", type=int, default=5000)
    ap.add_argument("--min-interval", type=float, default=1.0)
    a = ap.parse_args(argv)
    client = DataGovInClient(resource_id=VARIETY_HISTORY, page_size=a.page_size, min_interval_s=a.min_interval)
    if not client.api_key:
        log.error("AGRI_DATA_GOV_IN_API_KEY is not set")
        return 2
    days, d = [], a.start
    while d <= a.end:
        days.append(d); d += timedelta(days=1)
    done, fetched, failed = [], [], []
    for d in days:
        if (day_dir(d) / "_SUCCESS").exists() and not a.refresh:
            done.append(d.isoformat()); continue
        try:
            m = fetch_day(client, d)
            fetched.append(m)
            log.info("%s: %d records in %.1fs", d, m["records"], m["seconds"])
        except MissingCredentials:
            raise
        except Exception as e:  # keep going; the date stays incomplete and is retried next run
            failed.append({"arrival_date": d.isoformat(), "error": str(e)[:300]})
            log.error("%s failed: %s", d, e)
    run = {"resource": VARIETY_HISTORY, "range": [a.start.isoformat(), a.end.isoformat()], "skipped_completed": len(done),
           "fetched_days": len(fetched), "records": sum(m["records"] for m in fetched), "failed": failed,
           "requests": client.stats.requests, "retries": client.stats.retries,
           "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    Path("results/ingest").mkdir(parents=True, exist_ok=True)
    Path(f"results/ingest/backfill_{a.start}_{a.end}.json").write_text(json.dumps(run, indent=1))
    print(json.dumps({k: v for k, v in run.items() if k != "failed"} | {"failed_days": len(failed)}))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
