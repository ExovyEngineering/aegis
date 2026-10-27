"""Exercise the local source-refresh actions sequentially, preserving fallback truth.

This invokes existing public adapters through the local FastAPI server. It does
not edit the registry, probe catalog pages, reset logistics state, use keys or
download bulk archives. Local HTTP 200 is separate from fresh provider success.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlparse

import httpx

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ('openmeteo', 'nws_alerts', 'ncei_historical', 'fsis_recalls', 'modot')


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def shape(payload):
    if isinstance(payload, dict):
        return {'type':'object', 'keys':list(payload.keys())}
    if isinstance(payload, list):
        return {'type':'array', 'rows':len(payload),
                'item_fields':list(payload[0].keys()) if payload and isinstance(payload[0], dict) else [],
                'first_item_type':type(payload[0]).__name__ if payload else None}
    return {'type':type(payload).__name__}


def expected_schema(source, payload):
    if source == 'openmeteo':
        hourly=payload.get('hourly') if isinstance(payload,dict) else None
        if not isinstance(hourly,dict) or not isinstance(hourly.get('time'),list) or not hourly['time']:return False
        return all(isinstance(hourly.get(field),list) and len(hourly[field])==len(hourly['time'])
                   for field in ('temperature_2m','precipitation','wind_speed_10m'))
    if source == 'nws_alerts':
        return isinstance(payload, dict) and payload.get('type') == 'FeatureCollection' and isinstance(payload.get('features'), list)
    if source == 'ncei_historical':
        return isinstance(payload, list) and bool(payload) and isinstance(payload[0], dict) and {'DATE','STATION'} <= payload[0].keys()
    if source == 'fsis_recalls':
        return isinstance(payload, list) or isinstance(payload, dict) and any(isinstance(payload.get(key), list) for key in ('results','data','recalls','items'))
    return isinstance(payload, dict) and isinstance(payload.get('layers'), list)


def describe(source, body):
    payload = body.get('payload')
    row = {
        'response_status':body.get('status'),
        'payload_present':'payload' in body and payload is not None,
        'response_shape':shape(payload),
        'retrieved_at':body.get('retrieved_at'),
        'source_url':body.get('source_url'),
        'cache':body.get('cache'),
        'stale':body.get('stale'),
        'refresh_error':body.get('refresh_error'),
        'error':body.get('error'),
        'provenance':body.get('provenance'),
        'coverage_warning':body.get('coverage_warning'),
        'schema_valid':bool(expected_schema(source, payload)),
        'freshness_reasons':[],
    }
    if body.get('status') == 'failed' or body.get('error'):
        row['freshness_reasons'].append(body.get('error') or 'Adapter returned failed status')
    if body.get('stale'):
        row['freshness_reasons'].append('Top-level stale cached fallback')
    if body.get('refresh_error'):
        row['freshness_reasons'].append(body['refresh_error'])
    if not row['payload_present']:
        row['freshness_reasons'].append('No adapter payload returned')
    elif not row['schema_valid']:
        row['freshness_reasons'].append('Payload does not match the supported source schema')
    if not row['retrieved_at']:
        row['freshness_reasons'].append('No successful retrieval timestamp recorded')
    if source == 'openmeteo' and isinstance(payload, dict):
        times=payload.get('hourly',{}).get('time',[])
        row['forecast_coverage']={'timezone':payload.get('timezone'), 'hourly_steps':len(times),
                                  'first_timestep':times[0] if times else None, 'last_timestep':times[-1] if times else None}
    elif source == 'nws_alerts' and isinstance(payload, dict):
        row['alert_features']=len(payload.get('features',[]))
    elif source == 'ncei_historical':
        records=payload if isinstance(payload,list) else []
        dates=sorted({item.get('DATE') for item in records if isinstance(item,dict) and item.get('DATE')})
        row['historical_coverage']={'rows':len(records), 'station_ids':sorted({str(item.get('STATION')) for item in records if isinstance(item,dict) and item.get('STATION')}),
                                    'first_reporting_date':dates[0] if dates else None, 'last_reporting_date':dates[-1] if dates else None,
                                    'scope':'The existing refresh adapter requests one station for July 1–7, 2024. This does not complete the broader NOAA stream or establish a weather-to-FSIS join.'}
    elif source == 'modot':
        layers=body.get('incident_layers',[])
        details=[]
        for layer in layers:
            features=layer.get('payload',{}).get('features',[])
            detail={'layer_id':layer.get('layer_id'), 'layer_name':layer.get('layer_name'),
                    'retrieved_at':layer.get('retrieved_at'), 'cache':layer.get('cache'),
                    'stale':layer.get('stale'), 'refresh_error':layer.get('refresh_error'),
                    'feature_count':len(features) if isinstance(features,list) else None,
                    'exceeded_transfer_limit':bool(layer.get('payload',{}).get('exceededTransferLimit')),
                    'schema_valid':layer.get('payload',{}).get('type')=='FeatureCollection' and isinstance(features,list)}
            details.append(detail)
            if detail['stale'] or detail['refresh_error']:
                row['freshness_reasons'].append(f"MoDOT layer {detail['layer_id']} stale/error: {detail['refresh_error'] or 'stale cached fallback'}")
            if not detail['schema_valid'] or detail['exceeded_transfer_limit']:
                row['freshness_reasons'].append(f"MoDOT layer {detail['layer_id']} is truncated or has an unexpected schema")
        failures=body.get('layer_failures',[])
        for failure in failures:
            row['freshness_reasons'].append(f"MoDOT layer {failure.get('layer_id')} failed: {failure.get('error')}")
        if not layers:row['freshness_reasons'].append('MoDOT returned no incident-layer responses')
        if not body.get('coverage_complete'):row['freshness_reasons'].append('MoDOT adapter reports incomplete coverage')
        row['modot']={'layer_count':len(layers), 'layer_failure_count':len(failures), 'layer_failures':failures,
                      'coverage_complete':body.get('coverage_complete'), 'layers':details,
                      'stale_layer_count':sum(bool(d['stale'] or d['refresh_error']) for d in details),
                      'cache_layer_count':sum(d['cache'] is True for d in details),
                      'feature_geometry_count':sum(d['feature_count'] or 0 for d in details),
                      'note':'Point/line layers can duplicate a single event. Geometry count is not a count of unique disruptions.'}
    return row


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',default='http://127.0.0.1:8001')
    args=parser.parse_args(argv)
    location=urlparse(args.base_url)
    if location.hostname not in ('127.0.0.1','localhost','::1'):
        parser.error('Source-action checks require a loopback FastAPI server')
    report={'started_at':utc_now(), 'base_url':args.base_url, 'actions':[],
            'method':'Sequential POSTs to existing local refresh actions. HTTP status is the local endpoint status; upstream HTTP status is not supplied by adapter payloads.',
            'fresh_success_definition':'Payload and schema present, no failed/stale/refresh_error state, successful retrieval time, and a new provider response (cache=false). MoDOT additionally requires complete, valid nonstale incident layers and no cached layer responses.',
            'usable_response_definition':'Expected payload/schema and retrieval time with no failed/stale/error state. A fresh TTL cache may be usable but is not counted as a new provider request success.',
            'registry_or_inventory_modified':False, 'logistics_state_mutations_performed':False}
    print(f"{'Source':18} {'HTTP':5} {'Seconds':8} {'Cache':7} {'Stale':7} Result",flush=True)
    with httpx.Client(base_url=args.base_url,timeout=240,follow_redirects=False) as client:
        for source in SOURCES:
            print(f'Requesting {source} refresh through the local adapter...',file=sys.stderr,flush=True)
            started=time.monotonic()
            row={'source':source, 'checked_at':utc_now(), 'http_status':None, 'upstream_http_status':None,
                 'fresh_success':False, 'new_public_request_success':False, 'fresh_payload_usable':False}
            try:
                response=client.post('/api/refresh/'+source)
                row.update(http_status=response.status_code, content_type=response.headers.get('content-type'))
                response.raise_for_status()
                body=response.json()
                if not isinstance(body,dict):raise ValueError('Expected an adapter response object')
                row.update(describe(source,body))
                row['fresh_payload_usable']=not row['freshness_reasons']
                all_new_layers=source!='modot' or all(layer['cache'] is False for layer in row['modot']['layers'])
                row['fresh_success']=row['fresh_payload_usable'] and row['cache'] is False and all_new_layers
                row['new_public_request_success']=row['fresh_success']
                if row['fresh_success']:row['result']='new provider response verified'
                elif row['fresh_payload_usable']:row['result']='usable TTL cache; no new provider success claimed'
                else:row['result']='failed or stale fallback; inspect exact reasons'
            except Exception as error:
                row.update(error=f'{type(error).__name__}: {error}', result='action failed',freshness_reasons=[f'{type(error).__name__}: {error}'])
            row['duration_seconds']=round(time.monotonic()-started,3)
            row['finished_at']=utc_now()
            report['actions'].append(row)
            print(f"{source:18} {str(row['http_status']):5} {row['duration_seconds']:8.3f} {str(row.get('cache')):7} {str(row.get('stale')):7} {row['result']}",flush=True)
            for reason in row.get('freshness_reasons',[]):print('  '+reason,flush=True)
            # Preserve partial results if the next adapter is slow or interrupted.
            report['finished_at']=utc_now()
            output=ROOT/'reports/source_actions.json'
            output.parent.mkdir(parents=True,exist_ok=True)
            output.write_text(json.dumps(report,indent=2),encoding='utf-8')
            time.sleep(.35)
    report.update(finished_at=utc_now(),fresh_success_count=sum(r['fresh_success'] for r in report['actions']),
                  usable_response_count=sum(r['fresh_payload_usable'] for r in report['actions']),
                  failed_or_stale_count=sum(not r['fresh_payload_usable'] for r in report['actions']),
                  all_actions_returned_http_success=all(r['http_status'] and 200<=r['http_status']<300 for r in report['actions']))
    output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({key:report[key] for key in ('fresh_success_count','usable_response_count','failed_or_stale_count')},indent=2),flush=True)
    return 0 if report['usable_response_count']==len(SOURCES) else 1


if __name__=='__main__':sys.exit(main())
