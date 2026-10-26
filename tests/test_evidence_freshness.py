"""Staleness must be evaluated when evidence is read, not only when fetched."""
import json
from datetime import datetime,timezone
import backend.main as api

def test_old_weather_snapshot_cannot_retain_fresh_status(tmp_path,monkeypatch):
    monkeypatch.setattr(api,'ROOT',tmp_path)
    p=tmp_path/'data/cache/probe_openmeteo.json';p.parent.mkdir(parents=True)
    p.write_text(json.dumps({'retrieved_at':'2020-01-01T00:00:00+00:00','stale':False,'payload':{'hourly':{}}}))
    result=api.evidence('openmeteo')
    assert result['stale'] and result['live'] is False
    assert result['retrieved_at']=='2020-01-01T00:00:00+00:00'

def test_frozen_fixture_is_identified_and_not_live(tmp_path,monkeypatch):
    monkeypatch.setattr(api,'ROOT',tmp_path)
    p=tmp_path/'data/fixtures/fsis_recalls.json';p.parent.mkdir(parents=True)
    p.write_text(json.dumps({'retrieved_at':datetime.now(timezone.utc).isoformat(),'payload':[]}))
    result=api.evidence('fsis_recalls')
    assert result['fixture'] and result['live'] is False
    assert not result['stale']

def test_invalid_retrieval_timestamp_is_a_coverage_warning_not_freshness(tmp_path,monkeypatch):
    monkeypatch.setattr(api,'ROOT',tmp_path)
    p=tmp_path/'data/cache/probe_nws_alerts.json';p.parent.mkdir(parents=True)
    p.write_text(json.dumps({'retrieved_at':None,'payload':{'features':[]}}))
    assert api.evidence('nws_alerts')['stale']
