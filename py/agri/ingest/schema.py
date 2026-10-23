"""Canonical price-event schema shared by every ingestion adapter.

One event = one published price report: (state, district, market, commodity,
variety, grade, arrival_date) with min/max/modal prices in Rs./quintal.

The same quality rules are implemented in Scala (preprocessing/DataQuality.scala)
for the batch path; tests/python/test_schema.py and the Scala parity spec pin
both implementations to the same expected classifications.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from typing import Any

SCHEMA_VERSION = 1
PRICE_UNIT = "INR/quintal"

BUSINESS_KEY = ("state", "district", "market", "commodity", "variety", "grade", "arrival_date")

# Order matters: the first failing rule is reported (mirrors DataQuality.classify).
QUALITY_FLAGS = (
    "VALID", "MISSING_DATE", "MISSING_PRICE", "NEGATIVE_PRICE", "ZERO_MIN_MAX",
    "ZERO_MAX", "MIN_GT_MAX", "MODAL_OUTSIDE_RANGE",
)


def _clean(s: Any) -> str:
    return " ".join(str(s).split()) if s is not None else ""


def _price(v: Any) -> float | None:
    if v is None or (isinstance(v, str) and v.strip() in ("", "NA", "-")):
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return None


def parse_date(v: Any) -> date | None:
    """Accepts ISO (2026-04-21), Indian (21/04/2026) and AGMARKNET (21 Apr 2026) forms."""
    if v is None:
        return None
    if isinstance(v, date):
        return v
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def classify(arrival_date: date | None, min_p: float | None, max_p: float | None, modal: float | None) -> str:
    if arrival_date is None:
        return "MISSING_DATE"
    if modal is None or modal == 0:
        return "MISSING_PRICE"
    if (min_p is not None and min_p < 0) or (max_p is not None and max_p < 0) or modal < 0:
        return "NEGATIVE_PRICE"
    if (min_p is None or min_p == 0) and (max_p is None or max_p == 0):
        return "ZERO_MIN_MAX"
    if max_p is None or max_p == 0:
        return "ZERO_MAX"
    if min_p is not None and min_p > max_p:
        return "MIN_GT_MAX"
    if (min_p is not None and modal < min_p) or modal > max_p:
        return "MODAL_OUTSIDE_RANGE"
    return "VALID"


@dataclass(frozen=True)
class PriceEvent:
    state: str
    district: str
    market: str
    commodity: str
    variety: str
    grade: str
    arrival_date: str            # ISO date (event time)
    min_price: float | None
    max_price: float | None
    modal_price: float | None
    source: str                  # e.g. "data.gov.in:9ef84268-..." or "replay:daily_market_prices_archive"
    source_record_ts: str | None  # timestamp published by the source, if any
    ingest_ts: str               # when this adapter produced the event (UTC, ISO)
    quality_flag: str
    data_origin: str             # live | replay | fixture | synthetic
    schema_version: int = SCHEMA_VERSION
    price_unit: str = PRICE_UNIT
    event_id: str = field(default="")

    def key(self) -> str:
        return "|".join(str(getattr(self, k)) for k in BUSINESS_KEY)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)


def make_event(raw: dict[str, Any], *, source: str, data_origin: str,
               source_record_ts: str | None = None, now: datetime | None = None) -> PriceEvent:
    """Normalise one raw record (any adapter's field names already mapped) into a PriceEvent."""
    d = parse_date(raw.get("arrival_date"))
    mn, mx, md = _price(raw.get("min_price")), _price(raw.get("max_price")), _price(raw.get("modal_price"))
    ts = (now or datetime.now(timezone.utc)).isoformat(timespec="milliseconds")
    base = dict(
        state=_clean(raw.get("state")), district=_clean(raw.get("district")), market=_clean(raw.get("market")),
        commodity=_clean(raw.get("commodity")), variety=_clean(raw.get("variety")), grade=_clean(raw.get("grade")),
        arrival_date=d.isoformat() if d else "", min_price=mn, max_price=mx, modal_price=md,
    )
    # event_id identifies the CONTENT: an exact re-send has the same id (dropped as duplicate);
    # a corrected price for the same business key has a new id (kept and tracked as a revision).
    digest = hashlib.sha1(json.dumps(base, sort_keys=True).encode()).hexdigest()[:20]
    return PriceEvent(**base, source=source, source_record_ts=source_record_ts, ingest_ts=ts,
                      quality_flag=classify(d, mn, mx, md), data_origin=data_origin, event_id=digest)
