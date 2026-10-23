"""Pre/post build attestation and isolated clean-source feature rebuild.

This records observed execution, not an independent or cryptographic build witness.
No historical outputs are reused and production data is never overwritten.
"""
import argparse, json, os, shutil, subprocess, time
from pathlib import Path
from agri.research.revision import sha

JAR=Path('target/scala-2.13/agri-bigdata-assembly.jar')
SOURCE_PATHS=['py','src','scripts','conf','build.sbt','project','docs/RELEASE_PROTOCOL.md','docs/REVISION_PROTOCOL.md']

def source_state():
    dirty=subprocess.check_output(['git','status','--porcelain','--untracked-files=all','--']+SOURCE_PATHS,text=True)
    if dirty:raise RuntimeError('Commit build implementation/configuration first: '+dirty)
    return {'commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            'files':{p:sha(p) for p in subprocess.check_output(['git','ls-files','--']+SOURCE_PATHS,text=True).splitlines() if Path(p).is_file()}}

def snapshot(config):
    groups=[sorted(Path(root).rglob('*.parquet')) for root in [config['silver'],config['panel']]]
    if any(not group for group in groups):raise RuntimeError('Missing build inputs')
    inputs=[p for group in groups for p in group]
    return {'source':source_state(),'inputs':{str(p):sha(p) for p in inputs},'jar_sha256':sha(JAR),
            'config':config,'shards':{f'conf/shards/commodities_{s}.txt':sha(f'conf/shards/commodities_{s}.txt') for s in 'abcd'}}

def verify_snapshot(before,after):
    if before != after:raise RuntimeError('Input, source, configuration or executed JAR changed during build')

def output_hashes(root):
    files=sorted(Path(root,'features').glob('*/*.parquet'))
    if not files:raise RuntimeError('Empty feature outputs')
    return {str(p):sha(p) for p in files}

def verify(root):
    p=Path(root,'BUILD_MANIFEST.json');m=json.loads(p.read_text())
    if m.get('status')!='completed' or m.get('kind')!='observed_pre_post_build':raise RuntimeError('Unverified build')
    # Current HEAD may include documentation/results commits after the build.
    # Compare actual source bytes and artifact bytes, retaining the original commit.
    current=snapshot(m['before']['config']);current['source']['commit']=m['before']['source']['commit']
    verify_snapshot(m['before'],current)
    if output_hashes(root)!=m['outputs']:raise RuntimeError('Feature outputs changed')
    return m

def build(config,root,results):
    root=Path(root);results=Path(results)
    if root.exists():raise RuntimeError('Refusing to overwrite existing build: '+str(root))
    if shutil.disk_usage('.').free<10*1024**3:raise RuntimeError('Need 10 GiB free before build')
    before=snapshot(config);root.mkdir(parents=True);results.mkdir(parents=True,exist_ok=True)
    runtime=subprocess.run(['bash','-c','source scripts/env.sh; java -version; spark-submit --version'],capture_output=True,text=True,check=True)
    manifest={'runtime_versions':runtime.stdout+runtime.stderr,'kind':'observed_pre_post_build','status':'running','started_epoch':time.time(),'before':before,'commands':[]}
    record=root/'BUILD_MANIFEST.json'
    record.write_text(json.dumps(manifest,indent=2))
    for shard in 'abcd':
        if shutil.disk_usage('.').free<7*1024**3:raise RuntimeError('Disk guard: need 7 GiB free')
        verify_snapshot(before,snapshot(config))
        overrides={'MASTER':'local[4]','AGRI_DRIVER_MEMORY':'4g','AGRI_SHUFFLE_PARTITIONS':'32',
          'AGRI_SILVER_DAILY':config['silver'],'AGRI_FORECAST_ROOT':str(root),'AGRI_RESULTS_ROOT':str(results),
          'AGRI_HISTORY_START':config['history_start'],'AGRI_PANEL_FROM':config['panel'],
          'AGRI_FORECAST_COMMODITIES':f'conf/shards/commodities_{shard}.txt','AGRI_SHARD_TAG':shard,
          'AGRI_FEATURES_WRITE_MODE':'overwrite' if shard=='a' else 'append',
          'AGRI_APPLY_JUMP_RULE':str(config['jump_rule']).lower(),
          'AGRI_EXCLUDED_SAMPLE':str(root/f'excluded_{shard}')}
        env={k:v for k,v in os.environ.items() if not k.startswith('AGRI_') and k not in ['MASTER','JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','SPARK_SUBMIT_OPTS']};env.update(overrides)
        command=['bash','-c','source scripts/env.sh; exec scripts/submit.sh com.agribigdata.forecast.BuildForecastFeatures']
        entry={'shard':shard,'command':command,'overrides':overrides,'started_epoch':time.time(),'jar_sha256':sha(JAR)}
        manifest['commands'].append(entry);record.write_text(json.dumps(manifest,indent=2))
        with (results/f'build_{shard}.log').open('w') as log:
            proc=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
        entry.update(returncode=proc.returncode,finished_epoch=time.time())
        record.write_text(json.dumps(manifest,indent=2))
        if proc.returncode:raise RuntimeError('Feature shard failed: '+shard)
        print(root,shard,'complete',flush=True)
    after=snapshot(config);verify_snapshot(before,after)
    reports={str(p):json.loads(p.read_text()) for p in results.glob('panel_report_*.json')}
    if len(reports)!=4 or any(r['jump_rule_applied']!=config['jump_rule'] or r['history_start']!=config['history_start'] for r in reports.values()):raise RuntimeError('Incomplete or wrong build settings')
    manifest.update(status='completed',after=after,outputs=output_hashes(root),reports=reports,finished_epoch=time.time())
    record.write_text(json.dumps(manifest,indent=2));return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['build','verify']);p.add_argument('--root',required=True);p.add_argument('--results');p.add_argument('--jump-rule',choices=['true','false']);a=p.parse_args()
    if a.mode=='verify':verify(a.root)
    else:build({'silver':'data/processed/daily_market_prices_v2','panel':'data/forecast/panel_entities','history_start':'2022-10-01','jump_rule':a.jump_rule=='true'},a.root,a.results)
