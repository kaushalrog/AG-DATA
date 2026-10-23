"""Sanity checks on the PUBLISHED gold layer (skipped when it has not been built)."""
from pathlib import Path

import duckdb
import pytest

GOLD = Path("data/gold")
pytestmark = pytest.mark.skipif(not (GOLD / "meta.json").exists(), reason="gold layer not built")


def q(sql):
    return duckdb.connect().execute(sql).fetchall()


def test_supported_forecasts_have_ordered_nested_intervals():
    bad = q(f"""SELECT count(*) FROM read_parquet('{GOLD}/latest_forecasts/*.parquet') WHERE supported AND NOT
               (lo90 <= lo80 AND lo80 <= median AND median <= hi80 AND hi80 <= hi90 AND lo80 > 0)""")[0][0]
    assert bad == 0


def test_every_supported_entity_has_all_horizons_and_one_origin():
    rows = q(f"""SELECT entity_id, count(*), count(DISTINCT origin_date) FROM read_parquet('{GOLD}/latest_forecasts/*.parquet')
                WHERE supported GROUP BY 1 HAVING count(*) <> 4 OR count(DISTINCT origin_date) <> 1""")
    assert rows == []


def test_latest_prices_unique_and_valid():
    dup, bad = q(f"""SELECT count(*) - count(DISTINCT entity_id), count(*) FILTER (WHERE NOT (min_price <= modal_price AND modal_price <= max_price))
                    FROM read_parquet('{GOLD}/latest_prices/*.parquet')""")[0]
    assert dup == 0 and bad == 0
