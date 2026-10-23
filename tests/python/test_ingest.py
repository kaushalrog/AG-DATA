"""Ingestion adapter tests. No network access: HTTP is faked; fixtures are labelled SYNTHETIC."""
import json
from datetime import date
from pathlib import Path

import pytest

from agri.ingest.datagovin import DataGovInClient, MissingCredentials, SchemaChanged
from agri.ingest.replay import replay_events
from agri.ingest.schema import classify, make_event, parse_date

FIX = json.loads((Path(__file__).parent / "fixtures" / "datagovin_page_SYNTHETIC.json").read_text())


class FakeResp:
    def __init__(self, status, body, headers=None):
        self.status_code, self._body, self.headers = status, body, headers or {}

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, params=None, timeout=None):
        self.calls.append(dict(params))
        return self.responses.pop(0)


def client(responses, tmp_path, **kw):
    return DataGovInClient(api_key="SECRET123", session=FakeSession(responses), checkpoint_dir=tmp_path,
                           min_interval_s=0, sleep=lambda s: None, **kw)


@pytest.mark.parametrize("mn,mx,md,flag", [
    (100, 200, 150, "VALID"), (0, 0, 150, "ZERO_MIN_MAX"), (100, 0, 150, "ZERO_MAX"),
    (300, 200, 250, "MIN_GT_MAX"), (100, 200, 250, "MODAL_OUTSIDE_RANGE"), (100, 200, None, "MISSING_PRICE"),
    (-1, 200, 150, "NEGATIVE_PRICE"),
])
def test_quality_rules_match_batch_classifier(mn, mx, md, flag):
    assert classify(date(2026, 1, 1), mn, mx, md) == flag


def test_missing_date_is_flagged():
    assert classify(None, 1, 2, 1.5) == "MISSING_DATE"


@pytest.mark.parametrize("s", ["2026-04-21", "21/04/2026", "21-04-2026", "21 Apr 2026"])
def test_date_formats(s):
    assert parse_date(s) == date(2026, 4, 21)


def test_event_id_is_content_based():
    r = dict(state="TN", district="Salem", market="M", commodity="Tomato", variety="V", grade="FAQ",
             arrival_date="2026-04-21", min_price=1, max_price=3, modal_price=2)
    a, b = make_event(r, source="s", data_origin="fixture"), make_event(r, source="s", data_origin="fixture")
    c = make_event({**r, "modal_price": 2.5}, source="s", data_origin="fixture")
    assert a.event_id == b.event_id          # exact re-send -> duplicate
    assert a.event_id != c.event_id          # correction -> new revision
    assert a.key() == c.key()                # ...of the same business key


def test_fetch_paginates_validates_and_redacts(tmp_path):
    page = dict(FIX, records=FIX["records"])
    c = client([FakeResp(200, page)], tmp_path, page_size=500)
    evs = list(c.fetch_all({"state": "Tamil Nadu"}))
    assert [e.quality_flag for e in evs] == ["VALID", "ZERO_MIN_MAX", "MIN_GT_MAX"]
    assert all(e.data_origin == "live" and e.arrival_date == "2026-10-22" for e in evs)
    call = c.session.calls[0]
    assert call["filters[state.keyword]"] == "Tamil Nadu"
    ckpt = next(tmp_path.glob("*.json")).read_text()
    assert "SECRET123" not in ckpt and json.loads(ckpt)["completed"] is True


def test_retries_on_429_then_succeeds(tmp_path):
    c = client([FakeResp(429, {}), FakeResp(503, {}), FakeResp(200, FIX)], tmp_path)
    assert len(list(c.fetch_all())) == 3
    assert c.stats.retries == 2


def test_gives_up_after_max_retries_without_leaking_key(tmp_path):
    c = client([FakeResp(500, {})] * 3, tmp_path, max_retries=2)
    with pytest.raises(RuntimeError) as e:
        list(c.fetch_all())
    assert "SECRET123" not in str(e.value)


def test_auth_failure_is_not_retried(tmp_path):
    c = client([FakeResp(403, {"error": "Key not authorised"})], tmp_path)
    with pytest.raises(MissingCredentials):
        list(c.fetch_all())
    assert len(c.session.calls) == 1


def test_no_key_refuses(tmp_path, monkeypatch):
    monkeypatch.delenv("AGRI_DATA_GOV_IN_API_KEY", raising=False)
    c = DataGovInClient(api_key=None, checkpoint_dir=tmp_path)
    c.api_key = None
    with pytest.raises(MissingCredentials):
        next(c.fetch_all())


def test_schema_change_is_detected(tmp_path):
    bad = dict(FIX, records=[{"State": "TN", "Modal_Price": "1"}])
    with pytest.raises(SchemaChanged):
        list(client([FakeResp(200, bad)], tmp_path).fetch_all())


def test_empty_response_yields_nothing_and_completes(tmp_path):
    c = client([FakeResp(200, dict(FIX, records=[], total=0))], tmp_path)
    assert list(c.fetch_all()) == []


def test_checkpoint_resumes_from_offset(tmp_path):
    full = dict(FIX, records=FIX["records"][:2])
    c = client([FakeResp(200, full)], tmp_path, page_size=2)
    list(c.fetch_all(max_pages=1))
    c2 = client([FakeResp(200, dict(FIX, records=FIX["records"][2:]))], tmp_path, page_size=2)
    list(c2.fetch_all())
    assert c2.session.calls[0]["offset"] == 2


def test_replay_fault_injection_is_labelled():
    rows = [dict(state="TN", district="D", market=f"M{i}", commodity="Tomato", variety="V", grade="FAQ",
                 arrival_date=date(2026, 4, 1), min_price=1, max_price=3, modal_price=2) for i in range(200)]
    out = list(replay_events(rows, duplicates=0.1, late=0.05, invalid=0.05, shuffle_window=10))
    evs = [e for e in out if not isinstance(e, str)]
    assert all(e.data_origin == "replay" for e in evs)
    dups = [e for e in evs if e.source.endswith("+dup")]
    assert dups and all(any(d.event_id == e.event_id for e in evs if e is not d) for d in dups)
    assert any(isinstance(e, str) for e in out)
    assert [e for e in evs if e.source.endswith("+late")] == evs[-len([e for e in evs if e.source.endswith('+late')]):]


def test_deferred_checkpoint_is_committed_only_after_delivery(tmp_path):
    from agri.ingest.cli import emit
    from agri.ingest.datagovin import PageEnd
    c = client([FakeResp(200, FIX)], tmp_path)
    items = list(c.fetch_all(defer_checkpoint=True))
    assert isinstance(items[-1], PageEnd) and not list(tmp_path.glob("*.json"))  # nothing committed yet
    out = tmp_path / "out.ndjson"
    res = emit(iter(items), bootstrap=None, ndjson=str(out), rate=0, client=c)
    assert res["sent"] == 3 and len(out.read_text().splitlines()) == 3
    assert json.loads(next(tmp_path.glob("datagovin_*.json")).read_text())["completed"] is True


def test_retry_after_header_is_honoured(tmp_path):
    slept = []
    c = DataGovInClient(api_key="K", session=FakeSession([FakeResp(429, {}, {"Retry-After": "7"}), FakeResp(200, FIX)]),
                        checkpoint_dir=tmp_path, min_interval_s=0, sleep=slept.append)
    list(c.fetch_all())
    assert 7.0 in slept


VARIETY_PAGE = {  # SYNTHETIC values; field names/types as returned by resource 35985678 on 2026-10-23
    "status": "ok", "total": 2, "count": 2, "records": [
        {"Arrival_Date": "20/04/2026", "Commodity": "Bhindi(Ladies Finger)", "Commodity_Code": "85", "District": "Karur",
         "Grade": "FAQ", "Market": "Karur(Uzhavar Sandhai )", "Max_Price": "3000", "Min_Price": "2000", "Modal_Price": "2500",
         "State": "Tamil Nadu", "Variety": "Bhindi"},
        {"Arrival_Date": "20/04/2026", "Commodity": "Banana", "Commodity_Code": "19", "District": "Malappuram",
         "Grade": "FAQ", "Market": "Moothedam  VFPCK Market", "Max_Price": "6100", "Min_Price": "5900", "Modal_Price": "6000",
         "State": "Keralam", "Variety": "Nendra Bale"}]}


def test_variety_history_profile_maps_capitalised_fields_and_date_filter(tmp_path):
    from agri.ingest.datagovin import VARIETY_HISTORY
    c = DataGovInClient(api_key="K", resource_id=VARIETY_HISTORY, session=FakeSession([FakeResp(200, VARIETY_PAGE)]),
                        checkpoint_dir=tmp_path, min_interval_s=0, sleep=lambda s: None, page_size=5000)
    evs = list(c.fetch_all({"arrival_date": "20/04/2026"}, resume=False, data_origin="backfill"))
    assert c.session.calls[0]["filters[Arrival_Date]"] == "20/04/2026"
    assert [(e.commodity, e.arrival_date, e.modal_price, e.data_origin) for e in evs] == [
        ("Bhindi(Ladies Finger)", "2026-04-20", 2500.0, "backfill"), ("Banana", "2026-04-20", 6000.0, "backfill")]
    assert evs[1].state == "Keralam"  # published spelling kept; harmonised downstream


def test_client_sends_identifying_user_agent():
    import requests
    c = DataGovInClient(api_key="K", session=requests.Session())
    assert c.session.headers["User-Agent"].startswith("AG-DATA-ingest/")


def test_backfill_writes_atomically_and_skips_completed_days(tmp_path, monkeypatch):
    import gzip
    from datetime import date
    from agri.ingest import backfill
    from agri.ingest.datagovin import VARIETY_HISTORY
    monkeypatch.setattr(backfill, "LANDING", tmp_path)
    c = DataGovInClient(api_key="K", resource_id=VARIETY_HISTORY, session=FakeSession([FakeResp(200, VARIETY_PAGE)]),
                        checkpoint_dir=tmp_path, min_interval_s=0, sleep=lambda s: None)
    m = backfill.fetch_day(c, date(2026, 4, 20))
    d = tmp_path / "arrival_date=2026-04-20"
    assert m["records"] == 2 and (d / "_SUCCESS").exists() and not (d / "part-0.ndjson.gz.tmp").exists()
    lines = gzip.open(d / "part-0.ndjson.gz", "rt").read().splitlines()
    assert len(lines) == 2 and json.loads(lines[0])["source"].endswith(VARIETY_HISTORY)
