"""Ingestion command line.

  # replay real archived reports into Kafka (no credentials needed)
  python -m agri.ingest.cli replay --start 2026-04-01 --end 2026-04-21 --limit 20000 --rate 2000

  # same, with labelled fault injection for streaming tests
  python -m agri.ingest.cli replay --start 2026-04-15 --end 2026-04-21 --duplicates 0.05 --late 0.02 --shuffle 50 --invalid 0.01

  # pull the live data.gov.in resource (needs AGRI_DATA_GOV_IN_API_KEY)
  python -m agri.ingest.cli live --filter state=Tamil\\ Nadu --to-kafka

  # write events to a newline-delimited JSON landing file instead of Kafka
  python -m agri.ingest.cli replay ... --ndjson data/ingest/landing/replay.ndjson
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

from .datagovin import DataGovInClient, MissingCredentials, PageEnd
from .replay import read_archive, replay_events

log = logging.getLogger("agri.ingest")

TOPIC = "agri.prices.v1"
DLQ_TOPIC = "agri.prices.dlq.v1"


def kafka_producer(bootstrap: str):
    from confluent_kafka import Producer
    return Producer({
        "bootstrap.servers": bootstrap,
        # Idempotent producer: retries cannot create duplicates within a producer session.
        "enable.idempotence": True,
        "acks": "all",
        "linger.ms": 20,
        "compression.type": "lz4",
    })


class DeliveryFailed(RuntimeError):
    pass


def emit(events, *, bootstrap: str | None, ndjson: str | None, rate: float, client: DataGovInClient | None = None) -> dict:
    prod = kafka_producer(bootstrap) if bootstrap else None
    out = open(ndjson, "a", encoding="utf-8") if ndjson else None
    sent = errors = 0
    failures: list[str] = []

    def on_delivery(err, msg):
        nonlocal errors
        if err is not None:
            errors += 1
            failures.append(str(err))

    t0 = time.monotonic()
    for i, ev in enumerate(events):
        if isinstance(ev, PageEnd):
            # commit the source checkpoint only after every event of the page is durably delivered
            if prod:
                prod.flush(60)
            if out:
                out.flush()
            if errors:
                raise DeliveryFailed(f"{errors} delivery errors; checkpoint not advanced: {failures[:3]}")
            client.save_checkpoint(ev.filters, ev.state)
            continue
        if isinstance(ev, str):              # invalid raw payload (fault injection)
            key, value = b"invalid", ev.encode()
        else:
            # re-stamp ingest_ts at send time so latency measurements start here, not when the
            # (possibly pre-built, rate-limited) event list was created
            ev = dataclasses.replace(ev, ingest_ts=datetime.now(timezone.utc).isoformat(timespec="milliseconds"))
            key, value = ev.key().encode(), ev.to_json().encode()
        if prod:
            while True:
                try:
                    prod.produce(TOPIC, key=key, value=value, on_delivery=on_delivery)
                    break
                except BufferError:
                    prod.poll(0.1)  # local queue full: back-pressure
            prod.poll(0)
        if out:
            out.write(value.decode() + "\n")
        sent += 1
        if rate > 0:
            target = t0 + sent / rate
            delay = target - time.monotonic()
            if delay > 0:
                time.sleep(delay)
    if prod:
        prod.flush(60)
    if out:
        out.close()
    return {"sent": sent, "delivery_errors": errors, "first_errors": failures[:5],
            "seconds": round(time.monotonic() - t0, 3)}


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    p = argparse.ArgumentParser(prog="agri.ingest")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("replay", help="replay archived real reports")
    r.add_argument("--start", type=date.fromisoformat, required=True)
    r.add_argument("--end", type=date.fromisoformat, required=True)
    r.add_argument("--limit", type=int)
    r.add_argument("--state", action="append")
    r.add_argument("--duplicates", type=float, default=0.0)
    r.add_argument("--late", type=float, default=0.0)
    r.add_argument("--shuffle", type=int, default=0)
    r.add_argument("--invalid", type=float, default=0.0)
    l = sub.add_parser("live", help="pull data.gov.in (requires API key)")
    l.add_argument("--filter", action="append", default=[], help="field=value")
    l.add_argument("--max-pages", type=int)
    for sp in (r, l):
        sp.add_argument("--bootstrap", default=None, help="Kafka bootstrap servers, e.g. localhost:9092")
        sp.add_argument("--ndjson", default=None)
        sp.add_argument("--rate", type=float, default=0.0, help="events per second (0 = as fast as possible)")
    a = p.parse_args(argv)

    if not a.bootstrap and not a.ndjson:
        p.error("choose at least one sink: --bootstrap and/or --ndjson")
    if a.ndjson:
        Path(a.ndjson).parent.mkdir(parents=True, exist_ok=True)

    if a.cmd == "replay":
        rows = read_archive(a.start, a.end, a.limit, a.state)
        events = replay_events(rows, duplicates=a.duplicates, late=a.late, shuffle_window=a.shuffle, invalid=a.invalid)
        res = emit(events, bootstrap=a.bootstrap, ndjson=a.ndjson, rate=a.rate)
        res.update({"mode": "replay", "data_origin": "replay", "archive_rows": len(rows)})
    else:
        client = DataGovInClient()
        filters = dict(f.split("=", 1) for f in a.filter)
        try:
            res = emit(client.fetch_all(filters, max_pages=a.max_pages, defer_checkpoint=True),
                       bootstrap=a.bootstrap, ndjson=a.ndjson, rate=a.rate, client=client)
        except MissingCredentials as e:
            log.error("%s", e)
            return 2
        except DeliveryFailed as e:
            log.error("%s", e)
            return 3
        res.update({"mode": "live", "stats": client.stats.__dict__})
    print(json.dumps(res, default=str))
    return 0 if res.get("delivery_errors", 0) == 0 else 3


if __name__ == "__main__":
    sys.exit(main())
