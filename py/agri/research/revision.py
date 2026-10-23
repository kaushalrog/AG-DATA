"""Locked retrospective revision experiment. See docs/REVISION_PROTOCOL.md.
Run: PYTHONPATH=py .venv/bin/python -m agri.research.revision run --commit <clean-source-sha>
"""
from __future__ import annotations
import argparse, hashlib, importlib.metadata, json, platform, subprocess, time
from pathlib import Path
import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from agri.forecast import lgbm as L
from agri.analysis.forecast_report import dm_test

SEED=20261023
SPLITS={'train':('2024-01-01','2024-12-31'), 'selection':('2025-01-01','2025-06-30'),
        'calibration':('2025-07-01','2025-12-31'), 'evaluation':('2026-01-01','2026-10-22')}
BASELINES=['persistence','ma7','ma30','snaive','sadj']
OUT=Path('results/revision_q1')

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''): h.update(b)
    return h.hexdigest()

def provenance(commit, roots):
    actual=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    if actual!=commit: raise RuntimeError('HEAD differs from locked source commit')
    dirty=subprocess.check_output(['git','diff','HEAD','--','py','src','scripts','conf','docs/REVISION_PROTOCOL.md'],text=True)
    if dirty: raise RuntimeError('Tracked experimental implementation is dirty')
    untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard','py','src','scripts','conf'],text=True).strip()
    if untracked: raise RuntimeError('Untracked implementation files: '+untracked)
    import inspect
    imported={name:str(Path(inspect.getfile(module)).resolve()) for name,module in [('lightgbm',lgb),('duckdb',duckdb),('candidate_helpers',L)]}
    source=subprocess.check_output(['git','ls-files','py','src','scripts','conf','docs/REVISION_PROTOCOL.md'],text=True).splitlines()
    inputs=[p for root in roots for p in sorted(Path(root).glob('features/*/*.parquet'))]
    return {'source_commit':actual,'resolved_modules':imported,'source_sha256':{p:sha(p) for p in source},
            'inputs':{str(p):{'size':p.stat().st_size,'sha256':sha(p)} for p in inputs},
            'python':platform.python_version(),'platform':platform.platform(),
            'versions':{n:importlib.metadata.version(n) for n in ['lightgbm','numpy','pandas','duckdb','scipy','pyarrow']}}

def condition(h,start,end):
    day=(pd.Timestamp(end)-pd.Timestamp('1970-01-01')).days
    return f"in_panel AND arrival_date BETWEEN DATE '{start}' AND DATE '{end}' AND y_{h} IS NOT NULL AND tday_{h}<={day}"

def read(con,root,h,split,limit=None):
    start,end=SPLITS[split]
    cols=list(dict.fromkeys(L.features(h)+['commodity','entity_id','arrival_date','modal_price',f'y_{h}',f'tday_{h}','mean7','mean30',f'snaive_{h}','ly_dev','has_ly']))
    sql=f"SELECT {','.join(cols)} FROM read_parquet('{root}/features/*/*.parquet',hive_partitioning=true) WHERE {condition(h,start,end)}"
    if limit: sql+=f" ORDER BY hash(entity_id, arrival_date, {SEED}),entity_id,arrival_date LIMIT {int(limit)}"
    else: sql+=' ORDER BY arrival_date,entity_id'
    df=con.execute(sql).df()
    df[L.features(h)]=df[L.features(h)].fillna(0.)
    return df

def holm(ps):
    a=np.asarray(ps); order=np.argsort(a); out=np.empty(len(a)); running=0.
    for i,j in enumerate(order):
        running=max(running,min(1.,(len(a)-i)*a[j])); out[j]=running
    return out.tolist()

def block_ci(sums, block=14, reps=500):
    """Resample paired calendar days; columns candidate absolute error, baseline error, count."""
    sums=np.asarray(sums,float); n=len(sums); rng=np.random.default_rng(SEED+block)
    ratios=[]; differences=[]
    for _ in range(reps):
        starts=rng.integers(0,n,size=int(np.ceil(n/block)))
        ix=((starts[:,None]+np.arange(block))%n).ravel()[:n]
        a,b,k=sums[ix].sum(axis=0)
        if b>0 and k>0: ratios.append(a/b); differences.append((a-b)/k)
    return {'block_days':block,'reps':reps,'relative_mae_95':np.quantile(ratios,[.025,.975]).tolist(),
            'mae_difference_95':np.quantile(differences,[.025,.975]).tolist()}

def metrics(pred):
    actual=pred['actual'].to_numpy(); scale=pred['scale'].to_numpy()
    out={}
    for name in ['candidate']+BASELINES:
        f=pred[name].to_numpy(); err=f-actual
        valid=(scale>0)&np.isfinite(scale)
        out[name]={'n':len(err),'mae':float(np.mean(abs(err))),'rmse':float(np.sqrt(np.mean(err**2))),
                   'wape':float(abs(err).sum()/abs(actual).sum()),'bias':float(err.mean()),
                   'mase':float(np.mean(abs(err[valid])/scale[valid])) if valid.any() else None,'mase_n':int(valid.sum())}
    for v in out.values():v['relative_mae']=v['mae']/out['persistence']['mae']
    out['interval']={f'coverage{level}':float(np.mean((actual>=pred[f'lo{level}'])&(actual<=pred[f'hi{level}']))) for level in [80,90]}
    out['interval']['relative_width80']=float(np.mean((pred.hi80-pred.lo80)/pred.p0))
    return out

def statistics(pred,h):
    z=pd.DataFrame({'date':pred.arrival_date,'entity_id':pred.entity_id,
                    'candidate':abs(pred.candidate-pred.actual),'persistence':abs(pred.persistence-pred.actual),'n':1})
    daily=z.groupby('date')[['candidate','persistence','n']].sum()
    calendar=daily.reindex(pd.date_range(daily.index.min(),daily.index.max()),fill_value=0.)
    # Daily TOTAL loss differences on a calendar index, scaled by a constant:
    # their mean has the same sign/estimand as pooled row-weighted MAE.
    loss=(calendar.candidate-calendar.persistence)/calendar.n.mean()
    st,p=dm_test(loss.to_numpy(),7 if h=='next' else L.HORIZONS[h]+3)
    entities=z.groupby('entity_id')[['candidate','persistence','n']].sum()
    rng=np.random.default_rng(SEED); data=entities.to_numpy(); ratios=[]
    for _ in range(500):
        a,b,k=data[rng.integers(0,len(data),len(data))].sum(axis=0); ratios.append(a/b)
    month=z.groupby(z.date.dt.strftime('%Y-%m'))[['candidate','persistence','n']].sum()
    return {'dm_stat':float(st),'dm_p_raw':float(p),'calendar_bootstrap':[block_ci(calendar,14),block_ci(calendar,28)],
            'entity_cluster_relative_mae_95':np.quantile(ratios,[.025,.975]).tolist(),
            'n_entities':len(entities),'share_entities_better':float((entities.candidate<entities.persistence).mean()),
            'monthly':{m:{'n':int(r.n),'relative_mae':float(r.candidate/r.persistence)} for m,r in month.iterrows()}}

def run(a):
    from agri.research.build_manifest import fingerprint
    sealed=json.loads(Path(a.unfiltered,'BUILD_MANIFEST.json').read_text())
    if sealed['fingerprint'] != fingerprint(a.unfiltered):
        raise RuntimeError('Feature build fingerprint verification failed')
    OUT.mkdir(parents=True,exist_ok=True)
    roots={'cleaned':a.cleaned,'unfiltered':a.unfiltered}
    manifest={'status':'running','splits':SPLITS,'protocol':'docs/REVISION_PROTOCOL.md','seed':SEED,
              'max_train':a.max_train,'classification':'retrospective robustness; no independent confirmation',
              'provenance':provenance(a.commit,list(roots.values())),
              'cleaned_feature_provenance':'Historical fc_main_v3/v3 features: input bytes hashed; original build exact code unproven',
              'unfiltered_build':json.loads(Path(a.unfiltered,'BUILD_MANIFEST.json').read_text()), 'runs':{}}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    con=duckdb.connect();con.execute('SET threads=4'); started=time.time()
    for variant,root in roots.items():
        for h in L.HORIZONS:
            key=f'{variant}_{h}'; t=time.time()
            tr=read(con,root,h,'train',a.max_train); va=read(con,root,h,'selection')
            cats=sorted(tr.commodity.unique().tolist()); xt=L.matrix(tr,h,cats); xv=L.matrix(va,h,cats)
            candidates=[]; best=None
            for leaves in [31,63]:
                m=lgb.train(dict(L.PARAMS,num_threads=6,seed=SEED,num_leaves=leaves,deterministic=True,force_col_wise=True),
                    lgb.Dataset(xt,tr[f'y_{h}']),num_boost_round=800,
                    valid_sets=[lgb.Dataset(xv,va[f'y_{h}'])],callbacks=[lgb.early_stopping(75,verbose=False)])
                mae=L.rupee_mae(va.modal_price.to_numpy(),va[f'y_{h}'].to_numpy(),m.predict(xv,num_threads=6))
                candidates.append({'leaves':leaves,'iteration':m.best_iteration,'selection_mae':mae})
                if best is None or mae<best[0]:best=(mae,m)
            model=best[1]; modeldir=Path('data/revision_q1/models')/key;modeldir.mkdir(parents=True,exist_ok=True)
            model.save_model(str(modeldir/'model.txt'))
            ca=read(con,root,h,'calibration'); cp=model.predict(L.matrix(ca,h,cats),num_threads=6)
            edges,q=L.fit_conformal(ca.std30.to_numpy(),ca[f'y_{h}'].to_numpy()-cp)
            calibration={'edges':edges.tolist(),'q':{f'{b}:{p}':v for (b,p),v in q.items()},'categories':cats,'features':L.features(h)}
            (modeldir/'calibration.json').write_text(json.dumps(calibration,indent=1))
            # Scale on ALL training rows, not the training subsample.
            start,end=SPLITS['train']
            scales=con.execute(f"SELECT entity_id,avg(abs(modal_price*(exp(y_{h})-1))) scale FROM read_parquet('{root}/features/*/*.parquet',hive_partitioning=true) WHERE {condition(h,start,end)} GROUP BY entity_id").df()
            te=read(con,root,h,'evaluation').merge(scales,on='entity_id',how='left',validate='many_to_one')
            pp=model.predict(L.matrix(te,h,cats),num_threads=6); iv=L.intervals(pp,te.std30.to_numpy(),edges,q)
            p0=te.modal_price.to_numpy(); pred=te[['entity_id','arrival_date','commodity',f'tday_{h}','scale']].copy()
            pred['p0']=p0; pred['actual']=p0*np.exp(te[f'y_{h}']);pred['candidate']=p0*np.exp(pp);pred['persistence']=p0
            pred['ma7']=np.exp(te.mean7);pred['ma30']=np.exp(te.mean30)
            pred['snaive']=p0*np.exp(te[f'snaive_{h}'].fillna(0.))
            # Seasonal-adjusted naive is the last-year change, not the year-on-year level deviation.
            pred['sadj']=p0*np.exp(te[f'ly_chg_{h}'])
            for name,v in iv.items():pred[name]=p0*np.exp(v)
            pred.to_parquet(f'data/revision_q1/predictions_{key}.parquet',index=False)
            bounds=lambda df:{'rows':len(df),'origin_min':str(df.arrival_date.min().date()),'origin_max':str(df.arrival_date.max().date()),'max_target_day':int(df[f'tday_{h}'].max())}
            r={'candidates':candidates,'selected_leaves':int(model.params['num_leaves']),
               'bounds':{name:bounds(df) for name,df in [('training_sample',tr),('selection',va),('calibration',ca),('evaluation',te)]},
               'metrics':metrics(pred),'statistics':statistics(pred,h),'model_sha256':sha(modeldir/'model.txt'),
               'calibration_sha256':sha(modeldir/'calibration.json'),
               'prediction_path':f'data/revision_q1/predictions_{key}.parquet',
               'prediction_sha256':sha(f'data/revision_q1/predictions_{key}.parquet'),
               'seasonal_fallback_rows':int(te[f'snaive_{h}'].isna().sum()),'seconds':time.time()-t}
            manifest['runs'][key]=r;(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
            print(key,'relative',r['metrics']['candidate']['relative_mae'],'coverage',r['metrics']['interval']['coverage80'],flush=True)
    keys=list(manifest['runs']); adjusted=holm([manifest['runs'][k]['statistics']['dm_p_raw'] for k in keys])
    for k,p in zip(keys,adjusted):manifest['runs'][k]['statistics']['dm_p_holm8']=p
    common={}
    for h in L.HORIZONS:
        c=pd.read_parquet(f'data/revision_q1/predictions_cleaned_{h}.parquet');u=pd.read_parquet(f'data/revision_q1/predictions_unfiltered_{h}.parquet')
        keys=c[['entity_id','arrival_date']].merge(u[['entity_id','arrival_date']],on=['entity_id','arrival_date'],validate='one_to_one')
        common[h]={v:metrics(df.merge(keys,on=['entity_id','arrival_date'],validate='one_to_one')) for v,df in [('cleaned',c),('unfiltered',u)]}
    manifest['common_origins']=common;manifest['status']='completed';manifest['seconds']=time.time()-started
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));report(manifest)

def report(m):
    for key,r in m['runs'].items():
        if sha(r['prediction_path'])!=r['prediction_sha256']: raise RuntimeError('Prediction artifact changed: '+key)
        pred=pd.read_parquet(r['prediction_path'])
        recomputed=metrics(pred)
        if abs(recomputed['candidate']['mae']-r['metrics']['candidate']['mae'])>1e-9:
            raise RuntimeError('Saved aggregate does not reproduce: '+key)
        r['metrics']=recomputed
        r['statistics']=statistics(pred,key.rsplit('_',1)[1])
    runs=list(m['runs'])
    for key,p in zip(runs,holm([m['runs'][k]['statistics']['dm_p_raw'] for k in runs])):
        m['runs'][key]['statistics']['dm_p_holm8']=p
    for h in L.HORIZONS:
        frames={v:pd.read_parquet(m['runs'][f'{v}_{h}']['prediction_path']) for v in ['cleaned','unfiltered']}
        common=frames['cleaned'][['entity_id','arrival_date']].merge(frames['unfiltered'][['entity_id','arrival_date']],on=['entity_id','arrival_date'],validate='one_to_one')
        m['common_origins'][h]={v:metrics(df.merge(common,on=['entity_id','arrival_date'],validate='one_to_one')) for v,df in frames.items()}
    m['report_source_sha256']=sha(__file__)
    (OUT/'manifest.json').write_text(json.dumps(m,indent=2))
    lines=['# Retrospective robustness results','',f"Source commit: `{m['provenance']['source_commit']}`. Generated from saved predictions.",'',
           '| Regime | Horizon | n | Rel. MAE | MASE candidate / persistence | 80% coverage | Rel. width | 95% block CI (28 d) | Holm p |',
           '|---|---|---:|---:|---:|---:|---:|---|---:|']
    for key,r in m['runs'].items():
        v,h=key.rsplit('_',1);me=r['metrics'];st=r['statistics'];ci=st['calendar_bootstrap'][1]['relative_mae_95']
        lines.append(f"| {v} | {h} | {me['candidate']['n']:,} | {me['candidate']['relative_mae']:.3f} | {me['candidate']['mase']:.3f} / {me['persistence']['mase']:.3f} | {me['interval']['coverage80']:.3f} | {me['interval']['relative_width80']:.3f} | [{ci[0]:.3f}, {ci[1]:.3f}] | {st['dm_p_holm8']:.2g} |")
    lines += ['', '## All baselines', '', '| Regime/horizon | Predictor | n | MAE | MASE | Relative MAE |', '|---|---|---:|---:|---:|---:|']
    for key,r in m['runs'].items():
        for name,v in r['metrics'].items():
            if name=='interval':continue
            lines.append(f"| {key} | {name} | {v['n']:,} | {v['mae']:.2f} | {v['mase']:.3f} | {v['relative_mae']:.3f} |")
    lines += ['', '## Monthly and series uncertainty', '', '| Regime/horizon | Entity cluster ratio 95% CI | Share series better | MAE difference 95% CI (28 days) | Seasonal fallbacks |', '|---|---|---:|---|---:|']
    for key,r in m['runs'].items():
        st=r['statistics'];lines.append(f"| {key} | {st['entity_cluster_relative_mae_95']} | {st['share_entities_better']:.3f} | {st['calendar_bootstrap'][1]['mae_difference_95']} | {r['seasonal_fallback_rows']} |")
        lines.append('')
        for mon,v in st['monthly'].items():lines.append(f"* {key}, {mon}: {v['n']:,} rows; relative MAE {v['relative_mae']:.3f}")
    lines += ['', '## Common origins (targets and features may differ)', '', '| Horizon | Regime | n | Rel. MAE | Coverage80 |', '|---|---|---:|---:|---:|']
    for h,regimes in m['common_origins'].items():
        for regime,r in regimes.items():lines.append(f"| {h} | {regime} | {r['candidate']['n']:,} | {r['candidate']['relative_mae']:.3f} | {r['interval']['coverage80']:.3f} |")
    (OUT/'TABLES.md').write_text('\n'.join(lines)+'\n')
    tex=[]
    for key,r in m['runs'].items():
        v,h=key.rsplit('_',1);me=r['metrics'];ci=r['statistics']['calendar_bootstrap'][1]['relative_mae_95']
        tex.append(f"{v} & {h} & {me['candidate']['relative_mae']:.3f} & {me['candidate']['mase']:.2f}/{me['persistence']['mase']:.2f} & {100*me['interval']['coverage80']:.1f}\\% & [{ci[0]:.3f}, {ci[1]:.3f}] \\\\")
    Path('paper/tables/revision_robustness.tex').write_text(
        r'\begin{tabular}{@{}llrrrr@{}}\toprule'+'\n'+
        r'Regime & Horizon & Rel. MAE & MASE & Coverage 80\% & Rel. MAE 95\% interval\\\midrule'+'\n'+
        '\n'.join(tex)+'\n'+r'\bottomrule\end{tabular}'+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['run','report']);p.add_argument('--commit');p.add_argument('--cleaned',default='data/forecast_v3');p.add_argument('--unfiltered',default='data/revision_unfiltered');p.add_argument('--max-train',type=int,default=500000)
    a=p.parse_args();run(a) if a.command=='run' else report(json.loads((OUT/'manifest.json').read_text()))
