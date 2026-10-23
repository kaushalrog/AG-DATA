"""Local frozen-model future-window issuance ledger; not trusted external timestamping.

No historical backcasts are accepted. CLI never accepts an issuance-time override.
"""
import argparse, fcntl, importlib.metadata, json, os, shutil, subprocess, tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from agri.forecast import lgbm as L
from agri.research.revision import sha

IST=ZoneInfo('Asia/Kolkata')
SOURCES=['py/agri/research/prospective.py','py/agri/forecast/lgbm.py',
 'src/main/scala/com/agribigdata/forecast/Features.scala','src/main/scala/com/agribigdata/forecast/ForecastConfig.scala']

def now():return datetime.now(timezone.utc)
def versions():return {n:importlib.metadata.version(n) for n in ['lightgbm','duckdb','numpy','pandas','pyarrow']}
def fingerprints(root):
    files=sorted(Path(root,'features').glob('*/*.parquet'))
    if not files:raise RuntimeError('No features available')
    return {str(p):sha(p) for p in files}

def lock(root,models,results,experiment):
    root=Path(root)
    if root.exists():raise RuntimeError('Refusing to replace an existing lock')
    dirty=subprocess.check_output(['git','status','--porcelain','--']+SOURCES,text=True)
    if dirty:raise RuntimeError('Commit locked implementation first')
    manifest=json.loads(Path(results,experiment,'manifest.json').read_text())
    if not manifest.get('completed') or manifest.get('family')!='lightgbm':raise RuntimeError('Expected completed LightGBM experiment')
    files=[]
    for h in L.HORIZONS:
        metadata=json.loads(Path(models,experiment,h,'lgbm','meta.json').read_text())
        if metadata['features']!=L.features(h):raise RuntimeError('Incompatible frozen feature order')
        files += [Path(models,experiment,h,'lgbm',n) for n in ['model.txt','meta.json']]
        files += [Path(results,experiment,f'conformal_{h}.csv')]
    hashes={str(p):sha(p) for p in files}
    root.mkdir(parents=True)
    record={'status':'locked','created_utc':now().isoformat(),'model_version':experiment,
            'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            'source_sha256':{p:sha(p) for p in SOURCES},'versions':versions(),'original_hashes':hashes,
            'protocol':{'minimum_completed_days':90,'latest_origin_max_age_days':2,'eligible':'in-panel, known commodity; issued strictly before target-window local date',
             'scope':'future-window issuance; same-day/next-report rows can be ineligible; not an exact repeat of retrospective origin protocol'},'artifacts':{}}
    for h in L.HORIZONS:
        dst=root/'artifacts'/h;dst.mkdir(parents=True)
        for name,src in [('model.txt',Path(models,experiment,h,'lgbm','model.txt')),('meta.json',Path(models,experiment,h,'lgbm','meta.json')),
                         ('conformal.csv',Path(results,experiment,f'conformal_{h}.csv'))]:
            shutil.copyfile(src,dst/name)
            if sha(src)!=hashes[str(src)] or sha(dst/name)!=hashes[str(src)]:raise RuntimeError('Model changed during locking')
            record['artifacts'][str((dst/name).relative_to(root))]=sha(dst/name)
    (root/'lock.json').write_text(json.dumps(record,indent=2));return record

def verify(root):
    root=Path(root);record=json.loads((root/'lock.json').read_text())
    if record['status']!='locked' or record['versions']!=versions():raise RuntimeError('Lock/dependencies changed')
    if any(sha(p)!=v for p,v in record['source_sha256'].items()):raise RuntimeError('Locked preprocessing/issuance source changed')
    if any(sha(root/p)!=v for p,v in record['artifacts'].items()):raise RuntimeError('Frozen model/calibration changed')
    return record

def eligible(frame,today,max_age=2):
    origin=pd.to_datetime(frame.origin_date).dt.date; target=pd.to_datetime(frame.target_from).dt.date
    return frame[(origin<today)&(origin>=today-timedelta(days=max_age))&(target>today)].copy()

def ledger(root):
    root=Path(root);previous=None;seen=set();batches=[]
    for p in sorted((root/'batches').glob('*/manifest.json')):
        if p.parent.name.startswith('.'):continue
        m=json.loads(p.read_text())
        if m['previous_manifest_sha256']!=previous or sha(p.parent/'forecasts.parquet')!=m['predictions_sha256'] or m['lock_sha256']!=sha(root/'lock.json'):
            raise RuntimeError('Issuance ledger integrity failure')
        rows=pd.read_parquet(p.parent/'forecasts.parquet')
        keys=list(zip(rows.entity_id.astype(str),rows.origin_date.astype(str),rows.horizon))
        if len(keys)!=len(set(keys)) or seen.intersection(keys):raise RuntimeError('Duplicate issuance keys')
        seen.update(keys);previous=sha(p);batches.append(m)
    return previous,seen,batches

def issue(root,features):
    root=Path(root)
    with (root/'.issue.lock').open('a') as guard:
        fcntl.flock(guard,fcntl.LOCK_EX)
        record=verify(root);previous,seen,batches=ledger(root)
        instant=now()
        if instant<datetime.fromisoformat(record['created_utc']):raise RuntimeError('System clock precedes model lock')
        if batches and instant<=datetime.fromisoformat(batches[-1]['issued_at']):raise RuntimeError('Issuance clock not increasing')
        today=instant.astimezone(IST).date();before=fingerprints(features)
        con=duckdb.connect();con.execute('SET threads=4')
        glob=str(Path(features,'features','*','*.parquet')).replace("'","''")
        # No data with a future observation date may enter this issuance.
        maximum=con.execute(f"SELECT max(arrival_date) FROM read_parquet('{glob}',hive_partitioning=true)").fetchone()[0]
        if maximum>today:raise RuntimeError('Future-dated input observations')
        parts=[]
        for h,days in L.HORIZONS.items():
            cols=list(dict.fromkeys(L.features(h)+['entity_id','commodity','arrival_date','modal_price','std30']))
            sql=f"SELECT {','.join(cols)} FROM read_parquet('{glob}',hive_partitioning=true) WHERE in_panel AND arrival_date>=? AND arrival_date<? QUALIFY row_number() OVER(PARTITION BY entity_id ORDER BY arrival_date DESC)=1"
            df=con.execute(sql,[today-timedelta(days=2),today]).df()
            if df.empty:continue
            meta=json.loads((root/'artifacts'/h/'meta.json').read_text());df=df[df.commodity.isin(meta['categories'])].copy()
            df['origin_date']=pd.to_datetime(df.arrival_date).dt.date
            df['target_from']=df.origin_date.map(lambda d:d+timedelta(days=days))
            df=eligible(df,today)
            if df.empty:continue
            df[L.features(h)]=df[L.features(h)].fillna(0.)
            booster=lgb.Booster(model_file=str(root/'artifacts'/h/'model.txt'))
            pred=booster.predict(L.matrix(df,h,meta['categories']),num_threads=4)
            edges,q=L.read_conformal(root/'artifacts'/h/'conformal.csv');iv=L.intervals(pred,df.std30.to_numpy(),edges,q)
            out=df[['entity_id','commodity','origin_date','target_from']].copy();out['entity_id']=out.entity_id.astype(str)
            out['target_to']=out.origin_date.map(lambda d:d+timedelta(days=7 if h=='next' else days+3))
            out['horizon']=h;out['origin_price']=df.modal_price.to_numpy();out['forecast']=df.modal_price.to_numpy()*np.exp(pred)
            for k,v in iv.items():out[k]=df.modal_price.to_numpy()*np.exp(v)
            out['issued_at']=instant.isoformat();out['model_version']=record['model_version']
            mask=[(str(r.entity_id),str(r.origin_date),r.horizon) not in seen for r in out.itertuples()];parts.append(out.loc[mask])
        con.close()
        if before!=fingerprints(features):raise RuntimeError('Inputs changed during issuance')
        verify(root)
        rows=pd.concat(parts,ignore_index=True) if parts else pd.DataFrame()
        instant=now()
        if instant<datetime.fromisoformat(record['created_utc']) or (batches and instant<=datetime.fromisoformat(batches[-1]['issued_at'])):raise RuntimeError('Issuance clock not increasing')
        if not rows.empty:
            rows=eligible(rows,instant.astimezone(IST).date());rows['issued_at']=instant.isoformat()
        if rows.empty:return {'status':'NO_ELIGIBLE_NEW_FORECASTS','issued_at':instant.isoformat()}
        values=rows[['origin_price','forecast','lo80','hi80','lo90','hi90']].to_numpy()
        if not np.isfinite(values).all() or (values<=0).any() or not ((rows.lo90<=rows.lo80)&(rows.lo80<=rows.hi80)&(rows.hi80<=rows.hi90)).all():raise RuntimeError('Invalid issued prices/intervals')
        parent=root/'batches';parent.mkdir(exist_ok=True);stage=Path(tempfile.mkdtemp(prefix='.pending-',dir=parent))
        rows.to_parquet(stage/'forecasts.parquet',index=False)
        m={'issued_at':instant.isoformat(),'rows':len(rows),'lock_sha256':sha(root/'lock.json'),'input_sha256':before,
           'previous_manifest_sha256':previous,'predictions_sha256':sha(stage/'forecasts.parquet'),
           'counts_by_horizon':rows.horizon.value_counts().to_dict(),'earliest_target':str(rows.target_from.min()),
           'timestamp_assurance':'Local system clock and hash chain only; not externally witnessed',
           'status':'ISSUED_LOCALLY_NOT_EVALUATED'}
        (stage/'manifest.json').write_text(json.dumps(m,indent=2))
        if now().astimezone(IST).date()>=rows.target_from.min():raise RuntimeError('Target window started before publication')
        for path in [stage/'manifest.json',stage/'forecasts.parquet']:
            with path.open('rb') as stream:os.fsync(stream.fileno())
        dest=parent/instant.strftime('%Y%m%dT%H%M%S%fZ');os.replace(stage,dest)
        return m

def status(root):
    verify(root);_,_,batches=ledger(root)
    return {'status':'NOT_EVALUATED','batches':len(batches),'issued_rows':sum(b['rows'] for b in batches),
            'first_issued_at':batches[0]['issued_at'] if batches else None,'minimum_completed_days':90,
            'limitations':'No external timestamp witness; no outcomes scored; no installed schedule; human review pending'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['lock','issue','status']);p.add_argument('--root',default='data/prospective_v1');p.add_argument('--features',default='data/forecast_v2');p.add_argument('--models',default='data/forecast_v3/models');p.add_argument('--results',default='results/forecast');p.add_argument('--experiment',default='fc_lgbm_2025');a=p.parse_args()
    r=lock(a.root,a.models,a.results,a.experiment) if a.command=='lock' else issue(a.root,a.features) if a.command=='issue' else status(a.root)
    print(json.dumps(r,indent=2))
