"""Audit availability assumptions and evaluate a frozen earlier-snapshot baseline.

Metadata creation dates are not proof of public release or user availability.
This is an additional retrospective stress test, never a prospective claim.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from backend.paths import ROOT,write_json
from scripts.train_model import evaluate

def split_by_snapshot(df,sources):
    """Freeze all rows from snapshots strictly earlier than the newest snapshot.

    Use the latest creation date among training sources as a conservative split
    boundary. All held-out collection dates must be strictly after that date.
    No row-level availability date is inferred or filled.
    """
    snapshots={Path(s['path']).name:pd.Timestamp(s['metadata_creation_date']).normalize() for s in sources}
    if len(set(snapshots.values()))<2:raise ValueError('Need at least two distinct source snapshot creation dates')
    latest=max(snapshots.values());prior={name:d for name,d in snapshots.items() if d<latest}
    cutoff=max(prior.values())
    work=df.copy();work['collection_date']=pd.to_datetime(work.collection_date,errors='coerce')
    valid=work.salmonella_sp_analysis.isin(['Positive','Negative']) & work.salmonella_sp_analysis_canceled.isin(['NULL','',None]) & work.collection_date.notna()
    work=work[valid].copy();work['y']=work.salmonella_sp_analysis.eq('Positive').astype(int)
    train=work[work.source_file.isin(prior) & (work.collection_date<=cutoff)].sort_values('collection_date')
    newest=[name for name,d in snapshots.items() if d==latest]
    validation=work[work.source_file.isin(newest) & (work.collection_date>cutoff)].sort_values('collection_date')
    if train.empty or validation.empty:raise ValueError('No nonoverlapping earlier-snapshot training and later-date validation rows')
    if set(train.source_file)&set(validation.source_file):raise ValueError('Training/validation source snapshots overlap')
    return train,validation,cutoff,snapshots

def run():
    path=ROOT/'data/processed/fsis_poultry.parquet';provenance=json.loads((ROOT/'data/processed/fsis_provenance.json').read_text(encoding='utf-8'))
    df=pd.read_parquet(path);train,validation,cutoff,snapshots=split_by_snapshot(df,provenance['sources'])
    if len(train)<100 or len(validation)<100 or train.y.nunique()<2:raise ValueError('Insufficient rows/classes for snapshot-consistent evaluation')
    probability=float((train.y.sum()+1)/(len(train)+2));y=validation.y.to_numpy();base=np.full(len(validation),probability)
    def calendar(frame):
        months=frame.collection_date.dt.month.to_numpy();return np.column_stack([np.sin(months*2*np.pi/12),np.cos(months*2*np.pi/12)])
    estimator=LogisticRegression(max_iter=1000,random_state=20261026).fit(calendar(train),train.y)
    predicted=estimator.predict_proba(calendar(validation))[:,1]
    baseline=evaluate(y,base,validation.collection_date);diagnostic=evaluate(y,predicted,validation.collection_date)
    result={'status':'snapshot-consistent retrospective sensitivity study; creation is not verified public release','generated_at':pd.Timestamp.now(tz='UTC').isoformat(),'snapshot_release_verified':False,'prospective_validation_feasible':False,'target':'Salmonella positivity in selected FSIS raw-poultry primary samples; not consumer illness','strict_split':{'training_snapshot_cutoff':cutoff.date().isoformat(),'training_rows':len(train),'validation_rows':len(validation),'training_start':train.collection_date.min().date().isoformat(),'training_end':train.collection_date.max().date().isoformat(),'validation_start':validation.collection_date.min().date().isoformat(),'validation_end':validation.collection_date.max().date().isoformat(),'training_files':sorted(train.source_file.unique().tolist()),'validation_files':sorted(validation.source_file.unique().tolist()),'snapshot_creation_dates':{name:d.date().isoformat() for name,d in snapshots.items()}},'snapshot_baseline':baseline,'calendar_logistic':diagnostic,'frozen_historical_prevalence':probability,'feature_availability':'Training labels are frozen to earlier source snapshots and are not updated using held-out outcomes. Calendar month is known at the selected sample date. Metadata creation dates precede validation collection dates; first public release and row-level result availability are unverified. No availability dates were invented.','operational_selection':'Frozen smoothed historical prevalence remains the transparent estimator; this sensitivity study does not validate prospective deployment.','limitations':['The FY2024/FY2025 files were created March 19, 2026, but that is not proof they were publicly released or accessible on that day.','FY2026 outcomes come from an October 9, 2026 snapshot and may contain retrospective revisions; no historical as-of archive was supplied.','Sampling schedules and publication latency are unknown, so this evaluates selected future-dated samples conditional on being sampled.','Single later-date holdout; no evidence of transportability to farms, shipments or consumers.','No held-out labels enter frozen model parameters or historical prevalence.','No CDC surveillance or weather feature is joined to this target.','Intervals resample validation weeks and exclude publication-lag and selection uncertainty.'],'availability_audit':{'row_level_result_dates_present':False,'actual_download_dates_known':False,'metadata_creation_dates_present':True,'prior_90_day_assumption_validated':False,'original_evaluation_status':'Existing 90-day-lag evaluation remains retrospective feasibility; 90 days is an assumption, not measured latency.'}}
    write_json(ROOT/'reports/model_timing.json',result)
    lines=['# Model timing and earlier-snapshot stress test','',result['status'],'',f"Earlier source snapshots created **{cutoff.date()}** supply {len(train):,} training rows. Validation contains {len(validation):,} selected samples dated {result['strict_split']['validation_start']} through {result['strict_split']['validation_end']}, from a different, later source snapshot.",'',result['feature_availability'],'','| Estimator | Brier | PR-AUC (AP) | ROC-AUC |','|---|---:|---:|---:|',f"| Frozen historical prevalence | {baseline['brier']:.8f} | {baseline['pr_auc_average_precision']:.6f} | {baseline['roc_auc']:.6f} |",f"| Calendar-only logistic diagnostic | {diagnostic['brier']:.8f} | {diagnostic['pr_auc_average_precision']:.6f} | {diagnostic['roc_auc']:.6f} |",'',result['operational_selection'],'']+['- '+x for x in result['limitations']]
    (ROOT/'reports/model_timing.md').write_text('\n'.join(lines),encoding='utf-8')
    print(f"Snapshot boundary {cutoff.date()}; train {len(train)}, validation {len(validation)}; baseline Brier {baseline['brier']:.8f}; calendar logistic Brier {diagnostic['brier']:.8f}")
    return result

if __name__=='__main__':run()
