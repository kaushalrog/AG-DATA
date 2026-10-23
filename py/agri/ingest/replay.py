"""Replay archived REAL price reports as an event stream.

This is how the streaming path is exercised without live credentials. Every
event carries data_origin="replay" and source="replay:<dataset>", and the API
and app show replayed data as historical, never as live.

Optional fault injection (--duplicates/--late/--shuffle/--invalid) produces a
documented, labelled test workload for the streaming correctness tests; injected
events are tagged in their `source` field so they can be counted downstream.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone
from typing import Iterator

import duckdb

from .schema import PriceEvent, make_event

SILVER_GLOB = "data/processed/daily_market_prices/*/*.parquet"


def read_archive(start: date, end: date, limit: int | None = None, states: list[str] | None = None,
                 glob: str = SILVER_GLOB) -> list[dict]:
    con = duckdb.connect()
    where = ["arrival_date BETWEEN ? AND ?"]
    params: list = [start, end]
    if states:
        where.append(f"state IN ({','.join('?' * len(states))})")
        params += states
    sql = (f"SELECT state, district, market, commodity, variety, grade, arrival_date, min_price, max_price, modal_price "
           f"FROM read_parquet('{glob}', hive_partitioning=true) WHERE {' AND '.join(where)} "
           f"ORDER BY arrival_date, state, market, commodity, variety, grade")
    if limit:
        sql += f" LIMIT {int(limit)}"
    cur = con.execute(sql, params)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def replay_events(rows: list[dict], *, dataset: str = "daily_market_prices_archive", duplicates: float = 0.0,
                  late: float = 0.0, shuffle_window: int = 0, invalid: float = 0.0,
                  seed: int = 7) -> Iterator[PriceEvent | str]:
    """Yields PriceEvents (or raw invalid strings when invalid > 0)."""
    rng = random.Random(seed)
    src = f"replay:{dataset}"
    buf: list[PriceEvent | str] = []
    held_back: list[PriceEvent] = []
    for r in rows:
        ev = make_event(r, source=src, data_origin="replay")
        buf.append(ev)
        if duplicates and rng.random() < duplicates:
            buf.append(make_event(r, source=src + "+dup", data_origin="replay"))
        if late and rng.random() < late:
            held_back.append(make_event(r, source=src + "+late", data_origin="replay"))
        if invalid and rng.random() < invalid:
            buf.append('{"state": "Tamil Nadu", "modal_price": "not-a-number"')  # truncated JSON
    if shuffle_window > 1:
        for i in range(0, len(buf), shuffle_window):
            chunk = buf[i:i + shuffle_window]
            rng.shuffle(chunk)
            buf[i:i + shuffle_window] = chunk
    yield from buf
    yield from held_back  # late arrivals come after the rest of the stream
