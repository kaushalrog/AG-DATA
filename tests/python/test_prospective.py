"""Clearly synthetic unit/integration data; never a live-forecast evidence source."""
from datetime import datetime,timezone,date,timedelta
from pathlib import Path
import json
import pandas as pd
import numpy as np
import pytest
import lightgbm as lgb
from agri.forecast import lgbm as L
from agri.research import prospective as P


def test_eligibility_requires_recent_past_origin_and_strictly_future_window():
    today=date(2026,10,23)
    f=pd.DataFrame({'origin_date':[date(2026,10,22),date(2026,10,22),today,date(2026,10,19)],
                    'target_from':[date(2026,10,25),today,date(2026,10,26),date(2026,11,2)]})
    assert list(P.eligible(f,today).index)==[0]

@pytest.fixture
def setup(tmp_path,monkeypatch):
    clock=[datetime(2026,10,23,10,tzinfo=timezone.utc)]
    monkeypatch.setattr(P,'now',lambda:clock[0])
    monkeypatch.setattr(P,'SOURCES',[])
    monkeypatch.setattr(P.subprocess,'check_output',lambda args,**kw:'' if 'status' in args else 'synthetic-source')
    models=tmp_path/'models';results=tmp_path/'results';exp='synthetic'
    (results/exp).mkdir(parents=True)
    (results/exp/'manifest.json').write_text(json.dumps({'completed':True,'family':'lightgbm'}))
    for h in L.HORIZONS:
        d=models/exp/h/'lgbm';d.mkdir(parents=True)
        df=pd.DataFrame({c:np.linspace(0,1,30) for c in L.features(h)});df['commodity']=pd.Categorical(['CROP']*30,categories=['CROP'])
        model=lgb.train({'objective':'l1','num_leaves':2,'min_data_in_leaf':2,'verbose':-1,'num_threads':1},lgb.Dataset(df,np.zeros(30)),num_boost_round=2)
        model.save_model(str(d/'model.txt'));(d/'meta.json').write_text(json.dumps({'features':L.features(h),'categories':['CROP']}))
        pd.DataFrame([{'bucket':b,'quantile':q,'residual_q':v,'std30_upper_edge':[.1,.2,.3,.4,float('inf')][b]} for b in range(5) for q,v in [(.05,-.2),(.1,-.1),(.9,.1),(.95,.2)]]).to_csv(results/exp/f'conformal_{h}.csv',index=False)
    root=tmp_path/'lock';P.lock(root,models,results,exp)
    features=tmp_path/'features';(features/'features/year=2026').mkdir(parents=True)
    row={c:0. for h in L.HORIZONS for c in L.features(h)};row.update(entity_id=1,commodity='CROP',arrival_date=date(2026,10,22),modal_price=1000.,in_panel=True)
    pd.DataFrame([row]).to_parquet(features/'features/year=2026/part.parquet',index=False)
    return root,features,clock


def test_real_booster_issuance_is_future_only_idempotent_and_hash_checked(setup):
    root,features,clock=setup
    first=P.issue(root,features)
    assert first['counts_by_horizon']=={'h3':1,'h7':1,'h14':1}
    assert first['earliest_target']=='2026-10-25'
    clock[0]+=timedelta(seconds=1)
    assert P.issue(root,features)['status']=='NO_ELIGIBLE_NEW_FORECASTS'
    assert P.status(root)['issued_rows']==3
    pred=next((root/'batches').glob('*/forecasts.parquet'));pred.write_bytes(b'tampered')
    with pytest.raises(RuntimeError,match='ledger integrity'):P.status(root)


def test_changed_booster_is_rejected(setup):
    root,_,_=setup;(root/'artifacts/h7/model.txt').write_text('changed')
    with pytest.raises(RuntimeError,match='Frozen model'):P.verify(root)


def test_future_dated_input_is_rejected(setup):
    root,features,_=setup;p=features/'features/year=2026/part.parquet';df=pd.read_parquet(p);df.arrival_date=date(2026,10,24);df.to_parquet(p,index=False)
    with pytest.raises(RuntimeError,match='Future-dated'):P.issue(root,features)


def test_missing_final_manifest_is_rejected(setup):
    root,features,_=setup;P.issue(root,features)
    next((root/'batches').glob('*/manifest.json')).unlink()
    with pytest.raises(RuntimeError,match='Incomplete visible'):P.status(root)


def test_final_batch_deletion_is_rejected_by_retained_head(setup):
    import shutil
    root,features,_=setup;P.issue(root,features)
    shutil.rmtree(next((root/'batches').iterdir()))
    with pytest.raises(RuntimeError,match='head mismatch or truncation'):P.status(root)


def test_manifest_timestamp_edit_is_rejected(setup):
    root,features,_=setup;P.issue(root,features)
    p=next((root/'batches').glob('*/manifest.json'));m=json.loads(p.read_text());m['issued_at']='2026-10-22T10:00:00+00:00';p.write_text(json.dumps(m))
    with pytest.raises(RuntimeError,match='timestamp inconsistency'):P.status(root)


def test_midnight_crossing_quarantines_uncommitted_batch(setup,monkeypatch):
    root,features,clock=setup
    # Simulate a target starting during fsync/rename, not a real issuance.
    times=iter([clock[0],clock[0],clock[0],datetime(2026,10,25,10,tzinfo=timezone.utc)])
    monkeypatch.setattr(P,'now',lambda:next(times))
    with pytest.raises(RuntimeError,match='quarantined'):P.issue(root,features)
    assert P.status(root)['issued_rows']==0
