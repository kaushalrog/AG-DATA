"""Seal/verify a feature build against input, output, configuration and builder hashes."""
import argparse, json, subprocess
from pathlib import Path
from agri.research.revision import sha

SOURCES=['src/main/scala/com/agribigdata/forecast/'+n+'.scala' for n in ['BuildForecastFeatures','Features','ForecastConfig']]

def fingerprint(root):
    files=sorted(Path('data/processed/daily_market_prices_v2').glob('*/*.parquet'))+sorted(Path('data/forecast/panel_entities').glob('*.parquet'))
    return {'inputs':{str(p):sha(p) for p in files},'builder_sources':{p:sha(p) for p in SOURCES},
        'configuration':{'history_start':'2022-10-01','jump_rule':False,'panel':'data/forecast/panel_entities',
          'shards':{str(p):sha(p) for p in sorted(Path('conf/shards').glob('*.txt'))}},
        'outputs':{str(p):sha(p) for p in sorted(Path(root,'features').glob('*/*.parquet'))}}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['seal','verify']);ap.add_argument('--root',default='data/revision_unfiltered');a=ap.parse_args()
    root=Path(a.root);p=root/'BUILD_MANIFEST.json'
    if not (root/'RESEARCH_COMPLETE').exists():raise RuntimeError('Partial build cannot be sealed/reused')
    current=fingerprint(root)
    if not current['outputs']:raise RuntimeError('Empty features')
    if a.mode=='verify':
        old=json.loads(p.read_text())
        if old['fingerprint']!=current:raise RuntimeError('Feature build inputs, sources, config or outputs changed')
    else:
        if p.exists():raise RuntimeError('Build already sealed; verify rather than overwrite')
        reports={}
        for report in Path('results/revision_q1').glob('panel_report_*.json'):
            m=json.loads(report.read_text())
            if m.get('jump_rule_applied') is not False or m['history_start']!='2022-10-01':raise RuntimeError('Wrong build settings')
            reports[str(report)]=m
        if len(reports)!=4:raise RuntimeError('Missing shard reports')
        p.write_text(json.dumps({'builder_last_commit':subprocess.check_output(['git','log','-1','--format=%H','--']+SOURCES,text=True).strip(),
                                'fingerprint':current,'shard_reports':reports},indent=1))
    print(a.mode,'feature build:',len(current['outputs']),'hashed files')
if __name__=='__main__':main()
