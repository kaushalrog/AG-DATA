"""Generate release-only manuscript tables/diagnostics from recorded predictions.
No training or model selection. Does not overwrite earlier-study tables.
"""
import hashlib,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
M=ROOT/'results/release_v1/manifest.json'

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()

def interval(b):return '['+', '.join(f'{x:.3f}' for x in b['relative_mae_95'])+']'

def table(name,header,rows,align):
    (ROOT/'paper/tables'/f'{name}.tex').write_text('\\begin{tabular}{@{}'+align+'@{}}\\toprule\n'+header+r'\\\midrule'+'\n'+'\n'.join(rows)+'\n'+r'\bottomrule\end{tabular}'+'\n')

def main():
    m=json.loads(M.read_text());assert m['status']=='completed' and m['verified_builds']
    for r in m['runs'].values():
        assert digest(ROOT/r['prediction_path'])==r['prediction_sha256'],'Changed prediction artifact'
    rows=[];ct=[];nt=[];scaled=[]
    for k,r in m['runs'].items():
        v,h=k.rsplit('_',1);me=r['metrics'];st=r['statistics'];a=me['candidate'];b=me['persistence']
        prefix=f'{v} & {h}'
        rows.append(prefix+f" & {a['n']:,} & {st['calendar_days']} & {a['mae']:.2f}/{b['mae']:.2f} & {a['relative_mae']:.3f} & {a['n']-a['mase_n']:,}"+r' \\')
        scaled.append(prefix+f" & {a['mase']:.3f} & {b['mase']:.3f} & {100*me['interval']['coverage80']:.1f}\\% & {me['interval']['relative_width80']:.3f}"+r' \\')
        for circ,dest in [(True,ct),(False,nt)]:
            items=[x for x in st['block_sensitivity'] if x['circular']==circ]
            dest.append(prefix+' & '+' & '.join(interval(x) for x in items)+r' \\')
    table('release_points','Regime & Horizon & Rows & Days & MAE C/P & Rel. MAE & MASE omitted',rows,'llrrrrr')
    table('release_scaled','Regime & Horizon & MASE C & MASE P & Coverage 80\\% & Rel. width',scaled,'llrrrr')
    for name,rows in [('release_circular',ct),('release_noncircular',nt)]:
        table(name,'Regime & Horizon & 28 days & 42 days & 56 days',rows,'llrrr')
    runs=list(m['runs'].values());ratios=[r['metrics']['candidate']['relative_mae'] for r in runs]
    effects=[r['metrics']['persistence']['mae']-r['metrics']['candidate']['mae'] for r in runs]
    exclusions=[1-r['metrics']['candidate']['mase_n']/r['metrics']['candidate']['n'] for r in runs]
    all_bounds=[b['relative_mae_95'] for r in runs for b in r['statistics']['block_sensitivity']]
    sub=[q for r in runs for groups in r['statistics']['subgroups'].values() for q in groups.values() if q['relative_mae'] is not None]
    subgroup_worse=sum(q['relative_mae']>1 for q in sub)
    text=r'''\paragraph{Clean-source release-study results.}
This is a new end-to-end execution of the smaller study, with identical historical periods and model search budget; it is not an exact replication of the full-size historical experiment. The pre-build source tag is \texttt{agdata-research-source-v1}. Both feature tables were rebuilt, with source/input/executable snapshots checked before and after execution. The fixed historical panel is an explicitly hashed external input, not a reproduced panel-selection process. Source attribution is stronger than in the earlier runs, but an observed execution log is not an independent build witness. All results remain retrospective and conditional on the fitted models and observed panel.
'''
    text+=f"Across the eight fits, observed pooled MAE reductions are {100*(1-max(ratios)):.1f}--{100*(1-min(ratios)):.1f}\\%, or INR {min(effects):.2f}--{max(effects):.2f} per quintal. Table~\\ref{{tab:release_point}} gives absolute errors and exposure. These gains are descriptive historical differences, not evidence of profitable farmer decisions or independent LightGBM superiority over Spark models. MASE excludes {100*min(exclusions):.1f}--{100*max(exclusions):.1f}\\% of rows lacking positive finite training scales, and therefore describes a different population from full-row MAE.\n"
    text+=r'''
\begin{table}[t]\centering\small\setlength{\tabcolsep}{3pt}
\caption{Clean-source release study: candidate/persistence MAE in INR per quintal, forecast rows, calendar days and MASE-excluded rows. Forecast rows are not independent replicates.}\label{tab:release_point}
\input{tables/release_points}
\end{table}

\begin{table}[t]\centering\small\setlength{\tabcolsep}{3pt}
\caption{Circular-block relative-MAE percentile sensitivity intervals (2,000 replicates, nominal 95\%). Actual coverage is unvalidated; all block specifications are shown.}\label{tab:release_circular}
\input{tables/release_circular}
\end{table}

\begin{table}[t]\centering\small\setlength{\tabcolsep}{3pt}
\caption{Non-circular-block sensitivity intervals under the same settings. Long blocks leave few temporal spans and do not establish stationarity or future transportability.}\label{tab:release_noncircular}
\input{tables/release_noncircular}
\end{table}
'''
    text+=f"The sensitivity interval endpoints across all six specifications and eight fits span {min(x[0] for x in all_bounds):.3f}--{max(x[1] for x in all_bounds):.3f}; this range is not a combined confidence interval. State and commodity summaries contain {subgroup_worse} group-by-fit comparisons with relative MAE above one; all subgroup counts and errors are retained, without selecting favourable subgroups. Groups and fits overlap, so this count is descriptive, not a multiplicity-adjusted finding.\n"
    text+=r'''
The daily diagnostics in Figure~\ref{fig:release_dependence} display loss differences, exposure and autocorrelation for the cleaned 7-day fit; diagnostics for all fits are recorded with the release. Substantial long-range correlation, seasonal changes or exposure variation can invalidate short-memory approximations. HAC bandwidth sensitivity is secondary: no horizon correction is claimed and tiny p values are not evidence of validated inference. Independent entity-resampling intervals are exploratory and cannot establish generalisation to independent new markets. Human expert statistical review and genuinely future-issued evaluation remain outstanding.
\begin{figure}[t]\centering
\includegraphics[width=0.88\linewidth]{release_dependence.pdf}
\caption{Release cleaned 7-day daily candidate-minus-persistence total loss divided by mean daily exposure (top), report counts (middle), and descriptive autocorrelation (bottom). No independence threshold is asserted.}\label{fig:release_dependence}
\end{figure}
'''
    (ROOT/'paper/ijf/release_results.tex').write_text(text)
    st=m['runs']['cleaned_h7']['statistics'];daily=st['daily_diagnostics'];fig,axes=plt.subplots(3,1,figsize=(7,7),constrained_layout=True)
    dates=np.array([np.datetime64(x['date']) for x in daily]);axes[0].plot(dates,[x['loss'] for x in daily],lw=.8);axes[0].axhline(0,color='grey',lw=.6);axes[0].set_ylabel('Loss difference\nINR / mean reports')
    axes[1].plot(dates,[x['n'] for x in daily],lw=.8);axes[1].set_ylabel('Reports per day')
    acf=st['acf'];axes[2].stem([int(k) for k in acf],[v for v in acf.values()]);axes[2].set_xlabel('Calendar-day lag');axes[2].set_ylabel('Autocorrelation')
    for ax in axes[:2]:
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2));ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'));ax.tick_params(labelsize=8)
    axes[1].set_xlabel('Observation date (2026)')
    fig.savefig(ROOT/'paper/figures/release_dependence.png',dpi=160);fig.savefig(ROOT/'paper/figures/release_dependence.pdf');plt.close(fig)

if __name__=='__main__':main()
