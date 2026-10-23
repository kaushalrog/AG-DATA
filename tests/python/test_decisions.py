"""The API's decision rule against the shared fixtures (also run by the app and Scala test suites)."""
import json
from pathlib import Path

import pytest

from agri.api.decisions import decide, load_rules

FIX = json.loads(Path("conf/decision_fixtures.json").read_text())


def test_fixtures_match_rules_version():
    assert FIX["rules_version"] == load_rules()["version"]


@pytest.mark.parametrize("case", FIX["cases"], ids=[c["name"] for c in FIX["cases"]])
def test_decision_fixture(case):
    i = case["input"]
    d = decide(i["commodity"], supported=i["supported"], unsupported_reason=i["unsupported_reason"], expired=i["expired"],
               stale=i["stale"], today=i["today"], days=i["days"], lo80=i["lo80"], hi80=i["hi80"],
               compare=i["compare"], transport=i["transport"])
    assert (d.signal, d.reason_codes) == (case["expected"]["signal"], case["expected"]["reasons"])
