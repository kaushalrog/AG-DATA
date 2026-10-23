"""Research safeguards: date purging and uncertainty computation, no network/data required."""
import numpy as np
import pandas as pd
import duckdb
from agri.research.revision import SPLITS, condition, holm, block_ci


def test_all_four_periods_disjoint_and_each_target_is_purged():
    spans=list(SPLITS.values())
    for left,right in zip(spans,spans[1:]):
        assert pd.Timestamp(left[1]) < pd.Timestamp(right[0])
    df=pd.DataFrame({'in_panel':[True]*3,'arrival_date':pd.to_datetime(['2025-06-29','2025-06-29','2025-07-01']),
        'y_h7':[.1]*3,'tday_h7':[(pd.Timestamp(d)-pd.Timestamp('1970-01-01')).days for d in ['2025-06-30','2025-07-01','2025-07-08']]})
    c=duckdb.connect();c.register('t',df)
    assert c.execute(f"SELECT count(*) FROM t WHERE {condition('h7',*SPLITS['selection'])}").fetchone()[0]==1
    assert c.execute(f"SELECT count(*) FROM t WHERE {condition('h7',*SPLITS['calibration'])}").fetchone()[0]==1


def test_holm_is_monotone_and_correct_in_original_order():
    assert np.allclose(holm([.03,.001,.8,.02]),[.06,.004,.8,.06])


def test_paired_bootstrap_preserves_known_ratio_and_effect():
    ci=block_ci(np.tile([8.,10.,2.],(100,1)),28,50)
    assert np.allclose(ci['relative_mae_95'],[.8,.8])
    assert np.allclose(ci['mae_difference_95'],[-1.,-1.])
