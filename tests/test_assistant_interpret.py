import json

import pytest

import backend.assistant_intent as intent
import backend.main as api


def context(client):
    result=client.get('/api/assistant/context')
    assert result.status_code==200,result.text
    return result.json()


def test_interpret_selects_existing_facts_without_changing_state(client,monkeypatch):
    monkeypatch.delenv('AEGIS_ASSISTANT_OLLAMA_ENABLED',raising=False)
    captured=context(client);before=api.DB.read_bytes()
    response=client.post('/api/assistant/interpret',json={'prompt':'Why did the baseline beat the model?',
        'expected_snapshot_id':captured['snapshot_id']})
    assert response.status_code==200,response.text
    answer=response.json()
    assert answer['question_id']=='model_limits' and answer['engine']['llm_used'] is False
    assert answer['interpretation']['mode']=='rules' and answer['operational_state_modified'] is False
    assert all(fact in captured['facts'] for fact in answer['answer']['items'])
    assert api.DB.read_bytes()==before


def test_stale_context_rejected_before_any_optional_model(client,monkeypatch):
    captured=context(client)
    client.post('/api/events',json={'event':'delivery_delay','shipment_id':'SH03'})
    monkeypatch.setattr(intent,'select_topic',lambda *args,**kwargs:pytest.fail('Stale request reached topic router'))
    result=client.post('/api/assistant/interpret',json={'prompt':'Explain the current scenarios',
        'expected_snapshot_id':captured['snapshot_id'],'allow_model':True})
    assert result.status_code==409


def test_delayed_topic_selection_does_not_publish_obsolete_snapshot(client,monkeypatch):
    captured=context(client)
    def select(*args,**kwargs):
        with api.db() as connection:
            connection.execute('UPDATE state SET revision=revision+1 WHERE id=1')
        return {'question_id':'scenario_compare','mode':'rules','llm_routing_used':False,'prompt_version':'mock'}
    monkeypatch.setattr(intent,'select_topic',select)
    result=client.post('/api/assistant/interpret',json={'prompt':'Explain current costs',
        'expected_snapshot_id':captured['snapshot_id']})
    assert result.status_code==409 and 'during question' in result.json()['detail']


def test_mock_model_only_selects_topic_and_cannot_change_claims(client,monkeypatch):
    captured=context(client)
    monkeypatch.setattr(intent,'select_topic',lambda *args,**kwargs:{'question_id':'shipment_review',
        'mode':'ollama_topic_selection','llm_routing_used':True,'prompt_version':'mock-only',
        'requested_model':'mock','reported_model':'mock'})
    result=client.post('/api/assistant/interpret',json={'prompt':'Review this shipment',
        'shipment_id':'SH03','allow_model':True,'expected_snapshot_id':captured['snapshot_id']})
    assert result.status_code==200,result.text
    answer=result.json();assert answer['shipment_id']=='SH03'
    assert answer['engine']['mode']=='deterministic' and not answer['engine']['llm_used']
    assert all(fact in captured['facts'] and fact['shipment_id']=='SH03' for fact in answer['answer']['items'])


def test_unsupported_or_action_prompt_does_not_create_audit_or_assignment(client):
    captured=context(client);before=api.DB.read_bytes()
    for prompt in ('Approve scenario A now','Write a purple poem'):
        result=client.post('/api/assistant/interpret',json={'prompt':prompt,'expected_snapshot_id':captured['snapshot_id']})
        assert result.status_code==422
    assert api.DB.read_bytes()==before


@pytest.mark.parametrize('changes',[{'prompt':'x'},{'prompt':'x'*401},{'allow_model':'yes'},
    {'expected_snapshot_id':'not-a-hash'},{'approve':True}])
def test_interpret_request_validation_precedes_side_effects(client,changes):
    captured=context(client)
    result=client.post('/api/assistant/interpret',json={'prompt':'Explain current sources',
        'expected_snapshot_id':captured['snapshot_id'],**changes})
    assert result.status_code==422
