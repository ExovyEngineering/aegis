import json
import copy
from pathlib import Path
import pytest
from scripts.build_submission_report import load_evidence,build_text,number

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
    assert 'Optional freshness evidence was not supplied' in report

def test_missing_required_input_stops_compiler_instead_of_inventing_metrics(tmp_path):
    with pytest.raises(FileNotFoundError,match='Required report evidence'):load_evidence(tmp_path,tmp_path/'missing.json')

def test_report_inputs_are_hashed_and_optional_inputs_are_not_filled(tmp_path):
    data=evidence();inventory=tmp_path/'inventory.json';inventory.write_text(json.dumps(data['inventory']))
    for name in ['api_status','model_evaluation','demo_results']:(tmp_path/(name+'.json')).write_text(json.dumps(data[name]))
    result,manifest=load_evidence(tmp_path,inventory)
    assert 'noaa_coverage' not in result and 'model_timing' not in result
    assert len(manifest)==4 and all(len(row['sha256'])==64 for row in manifest)


def saved_freshness():
    return json.loads((Path(__file__).resolve().parents[1]/'reports/freshness_demo.json').read_text(encoding='utf-8'))


def test_freshness_appendix_uses_actual_saved_cases_and_preserves_core_report():
    data=evidence();before=copy.deepcopy(data);base=build_text(data,figures=False)
    saved=saved_freshness();data['freshness_demo']=saved
    report=build_text(data,figures=False)
    assert report.split('\n## Appendix: Save the Load')[0]==base.split('\n## Appendix: Save the Load')[0]
    assert {key:value for key,value in data.items() if key!='freshness_demo'}==before
    assert data['freshness_demo']==saved_freshness()
    quality=saved['quality']
    assert f"point forward window: {number(quality['point_forward_hours'])} h" in report
    assert f"conservative chosen-case window: {number(quality['conservative_case_hours'])} h" in report
    for case in quality['sensitivity']['cases']:
        assert '| '+' | '.join(number(case[key]) for key in ('q10','equivalent_age_hours','remaining_reference_hours','remaining_hours_at_forecast_temperature'))+' |' in report
    for policy in ('fefo','fifo'):
        assert '| '+policy.upper()+' | '+' | '.join(number(saved['warehouse'][policy][key]) for key in ('supplied_kg','unmet_demand_kg','projected_expiry_exposure_kg'))+' |' in report
    driver=saved['driver']
    assert f"trip {driver['shipment_id']}, truck {driver['truck_id']}, destination {driver['destination_id']}" in report
    assert 'not a statistical confidence interval' in report and 'not observed waste' in report
    assert 'uncalibrated quality-planning experiment' in report and 'not authentic human presentation evidence' in report
    assert 'new telemetry flags driver review without redispatch: passed=True' in report
    assert 'physical sensors' in report and '../docs/freshness_science.md' in report


@pytest.mark.parametrize('payload',[None,[],{'passed':False,'error':'intentional failed replay'},{'passed':True,'simulation':True,'physical_hardware_connected':False,'checks':[]}])
def test_unusable_optional_freshness_never_awards_results(payload):
    data=evidence();data['freshness_demo']=payload
    report=build_text(data,figures=False).split('## Appendix: Save the Load')[1]
    assert 'no numerical' in report or 'no results are inferred' in report or 'outcomes and successful workflow claims are withheld' in report
    assert 'point forward window:' not in report and '| FEFO |' not in report
    assert 'automated checks passed' not in report and 'Saved exact driver handoff:' not in report


@pytest.mark.parametrize('value',[None,True,'4.5',float('nan'),float('inf'),-1])
def test_malformed_freshness_numbers_do_not_become_metrics(value):
    data=evidence();data['freshness_demo']=saved_freshness()
    data['freshness_demo']['quality']['point_forward_hours']=value
    report=build_text(data,figures=False).split('## Appendix: Save the Load')[1]
    assert 'missing or malformed' in report
    assert 'point forward window:' not in report and 'automated checks passed' not in report


def test_inconsistent_freshness_cases_and_missing_warehouse_are_disclosed():
    data=evidence();data['freshness_demo']=saved_freshness()
    data['freshness_demo']['quality']['conservative_case_hours']=999
    assert 'inconsistent point/conservative cases' in build_text(data,figures=False)
    data['freshness_demo']=saved_freshness();data['freshness_demo'].pop('warehouse')
    report=build_text(data,figures=False)
    assert 'FEFO/FIFO quantity or exposure evidence is missing or malformed' in report
    assert 'point forward window:' in report and '| FEFO |' not in report


@pytest.mark.parametrize('payload',[b'{broken json',b'\xff'])
def test_malformed_optional_freshness_is_hashed_and_disclosed_without_blocking_report(tmp_path,payload):
    data=evidence();inventory=tmp_path/'inventory.json';inventory.write_text(json.dumps(data['inventory']))
    for name in ('api_status','model_evaluation','demo_results'):(tmp_path/(name+'.json')).write_text(json.dumps(data[name]))
    path=tmp_path/'freshness_demo.json';path.write_bytes(payload)
    loaded,manifest=load_evidence(tmp_path,inventory)
    assert path.read_bytes()==payload
    assert 'freshness_demo_error' in loaded and len(manifest)==5
    assert len(next(row['sha256'] for row in manifest if row['input']==str(path)))==64
    report=build_text(loaded,figures=False)
    assert 'unreadable or malformed' in report and '0.08123456' in report


def test_optional_freshness_is_loaded_without_changing_source_bytes(tmp_path):
    data=evidence();inventory=tmp_path/'inventory.json';inventory.write_text(json.dumps(data['inventory']))
    for name in ('api_status','model_evaluation','demo_results'):(tmp_path/(name+'.json')).write_text(json.dumps(data[name]))
    saved=saved_freshness();path=tmp_path/'freshness_demo.json';path.write_text(json.dumps(saved))
    before=path.read_bytes();loaded,manifest=load_evidence(tmp_path,inventory)
    assert loaded['freshness_demo']==saved and path.read_bytes()==before
    assert len(manifest)==5
