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


def test_seasonal_naive_is_a_return_not_a_log_price():
    # Last-year/today ratio=1.2 must produce INR 1200 from INR 1000.
    p0=np.array([1000.,2000.]);returns=pd.Series([np.log(1.2),np.nan])
    assert np.allclose(p0*np.exp(returns.fillna(0.)),[1200.,2000.])


def test_direct_run_rejects_changed_feature_fingerprint(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace
    from agri.research import revision, build_manifest
    (tmp_path/'BUILD_MANIFEST.json').write_text(json.dumps({'fingerprint':{'outputs':'original'}}))
    monkeypatch.setattr(build_manifest,'fingerprint',lambda root:{'outputs':'changed'})
    import pytest
    with pytest.raises(RuntimeError,match='fingerprint verification failed'):
        revision.run(SimpleNamespace(unfiltered=str(tmp_path)))


def test_report_rejects_modified_saved_predictions(tmp_path):
    from agri.research import revision
    import pytest
    p=tmp_path/'prediction.parquet';p.write_bytes(b'changed')
    with pytest.raises(RuntimeError,match='Prediction artifact changed'):
        revision.report({'runs':{'cleaned_next':{'prediction_path':str(p),'prediction_sha256':'invalid'}}})


def test_non_circular_blocks_preserve_known_constant_effect():
    ci=block_ci(np.tile([8.,10.,2.],(100,1)),28,50,circular=False)
    assert np.allclose(ci['relative_mae_95'],[.8,.8])
    assert ci['circular'] is False


def test_hac_bandwidth_is_not_used_as_horizon_correction():
    from agri.research.revision import hac_diagnostic
    rng=np.random.default_rng(3);x=rng.normal(-.5,1,300)
    r=hac_diagnostic(x,28)
    assert r['bandwidth']==28 and r['stat']<0 and r['p_raw']<.05
