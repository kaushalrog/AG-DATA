"""Adapter for the data.gov.in Open Government Data (OGD) mandi price API.

Resource: "Current Daily Price of Various Commodities from Various Markets
(Mandi)", published by the Ministry of Agriculture and Farmers Welfare on the
OGD Platform India. See docs/DATA_SOURCES.md for what has and has not been
verified about this endpoint (auth, limits, history).

The adapter never ships a key. Set AGRI_DATA_GOV_IN_API_KEY in the environment
(.env.example lists it). Without a key, `fetch_all` raises MissingCredentials and
the pipeline falls back to replaying the archived dataset, which is labelled
data_origin="replay" end to end, so it is never presented as live data.

Behaviour:
  * pagination with offset/limit until a short page is returned
  * retry with exponential backoff + jitter on 429 / 5xx / network errors
  * client-side rate limit (min seconds between requests)
  * JSON checkpoint per filter set (last completed offset and run), so an
    interrupted pull resumes instead of starting again
  * provenance: request URL WITHOUT the api-key, fetch time, resource id
  * the API key is redacted from every log line and exception
"""
from __future__ import annotations

import json
import logging
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator
from urllib.parse import urlencode

import requests

from .schema import PriceEvent, make_event

log = logging.getLogger("agri.ingest.datagovin")

DEFAULT_RESOURCE_ID = os.environ.get("AGRI_DATA_GOV_IN_RESOURCE_ID", "9ef84268-d588-465a-a308-a864a43d0070")
BASE_URL = os.environ.get("AGRI_DATA_GOV_IN_BASE_URL", "https://api.data.gov.in/resource")

# Field names as documented for the resource; mapping is explicit so a schema
# change surfaces as a validation failure instead of silently empty columns.
FIELD_MAP = {
    "state": "state", "district": "district", "market": "market", "commodity": "commodity",
    "variety": "variety", "grade": "grade", "arrival_date": "arrival_date",
    "min_price": "min_price", "max_price": "max_price", "modal_price": "modal_price",
}
# The resource metadata (api.data.gov.in/lists, checked 2026-10-22) lists
# `state.keyword` as the filterable state field; the other fields filter by name.
FILTER_FIELDS = {"state": "state.keyword"}
REQUIRED_FIELDS = ("state", "market", "commodity", "arrival_date", "modal_price")


@dataclass
class PageEnd:
    """Marker yielded after each page when defer_checkpoint=True. The caller commits it with
    client.save_checkpoint(m.filters, m.state) only after its sink confirmed delivery."""
    filters: dict
    state: dict


class MissingCredentials(RuntimeError):
    pass


class SchemaChanged(RuntimeError):
    pass


@dataclass
class FetchStats:
    requests: int = 0
    retries: int = 0
    records: int = 0
    rejected: int = 0
    pages: int = 0


class DataGovInClient:
    def __init__(self, api_key: str | None = None, resource_id: str = DEFAULT_RESOURCE_ID,
                 page_size: int = 500, min_interval_s: float = 1.0, max_retries: int = 5,
                 timeout_s: float = 30.0, session: requests.Session | None = None,
                 checkpoint_dir: str | Path = "data/ingest/checkpoints",
                 sleep: Callable[[float], None] = time.sleep):
        self.api_key = api_key if api_key is not None else os.environ.get("AGRI_DATA_GOV_IN_API_KEY")
        self.resource_id = resource_id
        self.page_size = page_size
        self.min_interval_s = min_interval_s
        self.max_retries = max_retries
        self.timeout_s = timeout_s
        self.session = session or requests.Session()
        self.checkpoint_dir = Path(checkpoint_dir)
        self._sleep = sleep
        self._last_request = 0.0
        self.stats = FetchStats()

    # -- helpers -------------------------------------------------------------
    def _redact(self, s: str) -> str:
        return s.replace(self.api_key, "***") if self.api_key else s

    def public_url(self, params: dict[str, Any]) -> str:
        """Provenance URL: identical request, key removed."""
        safe = {k: v for k, v in params.items() if k != "api-key"}
        return f"{BASE_URL}/{self.resource_id}?{urlencode(safe)}"

    def _throttle(self) -> None:
        wait = self.min_interval_s - (time.monotonic() - self._last_request)
        if wait > 0:
            self._sleep(wait)
        self._last_request = time.monotonic()

    def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{BASE_URL}/{self.resource_id}"
        for attempt in range(self.max_retries + 1):
            retry_after = None
            self._throttle()
            self.stats.requests += 1
            try:
                r = self.session.get(url, params=params, timeout=self.timeout_s)
            except requests.RequestException as e:
                err = f"network error: {self._redact(str(e))}"
                retryable = True
            else:
                if r.status_code == 200:
                    try:
                        return r.json()
                    except ValueError:
                        err, retryable = "invalid JSON body", True
                else:
                    err = f"HTTP {r.status_code}"
                    retryable = r.status_code == 429 or r.status_code >= 500
                    retry_after = getattr(r, "headers", {}).get("Retry-After")
                    if r.status_code in (401, 403):
                        raise MissingCredentials(f"data.gov.in rejected the API key ({err})")
            if not retryable or attempt == self.max_retries:
                raise RuntimeError(f"data.gov.in request failed after {attempt + 1} attempts: {err} "
                                   f"[{self.public_url(params)}]")
            backoff = min(60.0, 2 ** attempt) * (0.5 + random.random())
            ra = retry_after
            if ra and str(ra).isdigit():  # the server's own instruction wins (capped at 5 minutes)
                backoff = min(300.0, float(ra))
            self.stats.retries += 1
            log.warning("retrying data.gov.in (%s), attempt %d, sleeping %.1fs", err, attempt + 1, backoff)
            self._sleep(backoff)
        raise AssertionError("unreachable")

    def _checkpoint_path(self, filters: dict[str, str]) -> Path:
        tag = "_".join(f"{k}-{v}" for k, v in sorted(filters.items())) or "all"
        return self.checkpoint_dir / f"datagovin_{self.resource_id}_{tag.replace(' ', '_').replace('/', '-')}.json"

    def load_checkpoint(self, filters: dict[str, str]) -> dict[str, Any]:
        p = self._checkpoint_path(filters)
        return json.loads(p.read_text()) if p.exists() else {"offset": 0, "completed": False}

    def save_checkpoint(self, filters: dict[str, str], state: dict[str, Any]) -> None:
        p = self._checkpoint_path(filters)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2))
        tmp.replace(p)  # atomic on POSIX

    # -- public API ------------------------------------------------------------
    def validate_record(self, rec: dict[str, Any]) -> dict[str, Any]:
        missing = [f for f in REQUIRED_FIELDS if FIELD_MAP[f] not in rec]
        if missing:
            raise SchemaChanged(f"record is missing documented fields {missing}; got keys {sorted(rec)}")
        return {k: rec.get(src) for k, src in FIELD_MAP.items()}

    def fetch_all(self, filters: dict[str, str] | None = None, resume: bool = True,
                  max_pages: int | None = None, defer_checkpoint: bool = False) -> Iterator[PriceEvent | PageEnd]:
        if not self.api_key:
            raise MissingCredentials("AGRI_DATA_GOV_IN_API_KEY is not set; use the archive replay adapter instead")
        filters = filters or {}
        state = self.load_checkpoint(filters) if resume else {"offset": 0, "completed": False}
        if state.get("completed"):
            state = {"offset": 0, "completed": False}
        offset = int(state["offset"])
        pages = 0
        while True:
            params: dict[str, Any] = {"api-key": self.api_key, "format": "json",
                                      "limit": self.page_size, "offset": offset}
            params.update({f"filters[{FILTER_FIELDS.get(k, k)}]": v for k, v in filters.items()})
            body = self._get(params)
            records = body.get("records")
            if records is None:
                raise SchemaChanged(f"response has no 'records' key; keys={sorted(body)}")
            fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            src = f"data.gov.in:{self.resource_id}"
            for rec in records:
                try:
                    mapped = self.validate_record(rec)
                except SchemaChanged:
                    self.stats.rejected += 1
                    raise
                ev = make_event(mapped, source=src, data_origin="live", source_record_ts=body.get("updated_date"))
                self.stats.records += 1
                yield ev
            self.stats.pages += 1
            pages += 1
            offset += len(records)
            done = len(records) < self.page_size
            ck = {"offset": 0 if done else offset, "completed": done, "last_page_at": fetched_at,
                  "last_url": self.public_url(params), "total_reported": body.get("total")}
            if defer_checkpoint:
                yield PageEnd(filters, ck)
            else:
                self.save_checkpoint(filters, ck)
            if done or (max_pages is not None and pages >= max_pages):
                return
