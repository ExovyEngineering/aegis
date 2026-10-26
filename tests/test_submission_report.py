import json
import pytest
from scripts.build_submission_report import load_evidence,build_text

def metric(value):return {'n':321,'brier':value,'brier_week_block_bootstrap_95_ci':[value-.01,value+.01],'pr_auc_average_precision':.123456,'roc_auc':.5}
def evidence():
    plans=[{'scenario':k,'solver_status':'OPTIMAL','total_logistics_cost':99+i,'unmet_demand_kg':500,'affected_shipments':2,'review_priority_count':1,'constraint_violations':0} for i,k in enumerate('ABCD')]
    return {'inventory':{'files':[{'errors':[],'duplicate_of':None}],'data_dir':'provided'},'api_status':[{'id':'down','success':False,'failure':'HTTP 503'}],'model_evaluation':{'training_rows':1234,'validation_rows':321,'embargo_days':90,'validation_start':'2026-01-01','validation_end':'2026-02-01','baseline':metric(.08123456),'logistic_regression':metric(.09123456)},'demo_results':{'seed':1,'baseline':plans,'after_events':plans,'approved_assignments':3,'acknowledgment_recorded':True,'incident_recorded':True,'production_database_modified':False}}

def test_report_prints_measured_values_and_discloses_missing_evidence():
    report=build_text(evidence(),figures=False)
    assert '0.08123456' in report and '0.09123456' in report
    assert '0/1 HTTP successes' in report and 'HTTP 503' in report
    assert 'expanded-coverage evidence is missing' in report
    assert 'earlier-snapshot timing analysis is absent' in report
    assert 'Saved live route-laboratory results were not supplied' in report
    assert 'genuine Kiro application usage, author signoff, and official-rubric review pending' in report
    assert 'not the probability of consumer illness' in report

def test_missing_required_input_stops_compiler_instead_of_inventing_metrics(tmp_path):
    with pytest.raises(FileNotFoundError,match='Required report evidence'):load_evidence(tmp_path,tmp_path/'missing.json')

def test_report_inputs_are_hashed_and_optional_inputs_are_not_filled(tmp_path):
    data=evidence();inventory=tmp_path/'inventory.json';inventory.write_text(json.dumps(data['inventory']))
    for name in ['api_status','model_evaluation','demo_results']:(tmp_path/(name+'.json')).write_text(json.dumps(data[name]))
    result,manifest=load_evidence(tmp_path,inventory)
    assert 'noaa_coverage' not in result and 'model_timing' not in result
    assert len(manifest)==4 and all(len(row['sha256'])==64 for row in manifest)
