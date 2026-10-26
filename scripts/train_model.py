"""Retrospective feasibility study, with explicit assumed availability lag."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss,average_precision_score,roc_auc_score,precision_score,recall_score
from sklearn.calibration import calibration_curve
from backend.paths import ROOT,write_json

def evaluate(y,p,dates):
    bins=calibration_curve(y,p,n_bins=8,strategy='quantile'); rng=np.random.default_rng(20261026)
    # Resample entire calendar weeks to retain within-week dependence.
    weeks=pd.Series(dates).dt.to_period('W').astype(str).to_numpy(); unique=np.unique(weeks); groups=[np.flatnonzero(weeks==w) for w in unique]; scores=[]
    for _ in range(250):
        idx=np.concatenate([groups[i] for i in rng.integers(0,len(groups),len(groups))]); scores.append(brier_score_loss(y[idx],p[idx]))
    return {'n':len(y),'positives':int(y.sum()),'prevalence':float(y.mean()),'brier':float(brier_score_loss(y,p)),'brier_week_block_bootstrap_95_ci':np.quantile(scores,[.025,.975]).tolist(),'pr_auc_average_precision':float(average_precision_score(y,p)) if len(np.unique(y))>1 else None,'roc_auc':float(roc_auc_score(y,p)) if len(np.unique(y))>1 else None,'precision_at_0_5':float(precision_score(y,p>=.5,zero_division=0)),'recall_at_0_5':float(recall_score(y,p>=.5,zero_division=0)),'calibration':{'observed':bins[0].tolist(),'predicted':bins[1].tolist()}}

def main():
    df=pd.read_parquet(ROOT/'data/processed/fsis_poultry.parquet'); n=len(df)
    df=df[df.salmonella_sp_analysis.isin(['Positive','Negative']) & df.salmonella_sp_analysis_canceled.isin(['NULL','',None])].dropna(subset=['collection_date']).sort_values('collection_date').copy()
    df['y']=df.salmonella_sp_analysis.eq('Positive').astype(int)
    # Each origin t uses only outcomes collected by t-90 days, from strictly earlier dates.
    daily=df.groupby('collection_date').y.agg(['sum','count']).sort_index(); daily['pos']=daily['sum'].cumsum(); daily['total']=daily['count'].cumsum()
    cutoff=df.collection_date-pd.Timedelta(days=90); prior=daily[['pos','total']].reindex(cutoff,method='ffill').fillna(0).reset_index(drop=True)
    df['lag90_prevalence']=(prior.pos.to_numpy()+1)/(prior.total.to_numpy()+2)
    df['month_sin']=np.sin(df.collection_date.dt.month*2*np.pi/12); df['month_cos']=np.cos(df.collection_date.dt.month*2*np.pi/12)
    features=['lag90_prevalence','month_sin','month_cos']; dates=np.sort(df.collection_date.unique()); split=dates[int(len(dates)*.7)]
    # Embargo removes labels in 90 days preceding validation start from fitting.
    train=df[df.collection_date<split-pd.Timedelta(days=90)]; test=df[df.collection_date>=split]
    if len(train)<100 or len(test)<100 or train.y.nunique()<2: raise ValueError('Insufficient chronological coverage/classes')
    model=LogisticRegression(max_iter=1000,random_state=20261026).fit(train[features],train.y); p=model.predict_proba(test[features])[:,1]; y=test.y.to_numpy()
    prevalence=(train.y.sum()+1)/(len(train)+2); base=np.full(len(test),prevalence)
    baseline=evaluate(y,base,test.collection_date); fitted=evaluate(y,p,test.collection_date)
    result={'status':'retrospective feasibility only — not a validated prospective forecast','target':'Salmonella positivity in a future selected FSIS raw-poultry primary sample; national','excluded_rows':n-len(df),'training_rows':len(train),'validation_rows':len(test),'training_end':str(train.collection_date.max()),'validation_start':str(test.collection_date.min()),'validation_end':str(test.collection_date.max()),'embargo_days':90,'feature_availability':'Assumed collection date + 90 days. Actual per-result publication timestamps unavailable; historical snapshots were downloaded later. No operational forecast claim.','features':features,'baseline':baseline,'logistic_regression':fitted,'coefficients':dict(zip(features,model.coef_[0].tolist())),'operational_selection':'smoothed historical prevalence; prospective skill not established','historical_prevalence':float(prevalence),'limitations':['Selected surveillance samples are not representative of all poultry','No probability of consumer illness','Single chronological holdout; no external validation','No CDC or weather linkage','Intervals quantify within-holdout weekly variation, not publication-lag uncertainty'],'error_analysis':[]}
    tmp=test.assign(predicted=p)
    for state,g in tmp.groupby('establishment_state'):
        if len(g)>=30: result['error_analysis'].append({'state':state,'n':len(g),'prevalence':float(g.y.mean()),'brier':float(brier_score_loss(g.y,g.predicted))})
    write_json(ROOT/'reports/model_evaluation.json',result)
    (ROOT/'docs/model_card.md').write_text('# Model card\n\n'+result['status']+'\n\n'+result['target']+'\n\n'+result['feature_availability']+'\n\nMeasured results: `reports/model_evaluation.json`. The logistic model is not operationally selected. No gradient boosting until availability and prospective evaluation are defensible. Hold decisions never derive automatically from these scores.\n\n'+ '\n'.join('- '+x for x in result['limitations']),encoding='utf-8')
    print('Baseline Brier:',baseline['brier'],'Logistic Brier:',fitted['brier'],'Validation n:',len(test))
if __name__=='__main__':main()
