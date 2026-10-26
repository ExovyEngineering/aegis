import sys, json, time, csv
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from backend.adapters import now
from backend.paths import ROOT, write_json
def main():
    registry=json.loads((ROOT/'config/api_registry.yaml').read_text()); results=[]
    print(f"{'Source':22} {'HTTP':5} {'ms':8} {'Content type':28} Result")
    for source in registry['sources']:
        started=time.monotonic(); row={'id':source['id'],'tested_at':now(),'success':False,'http_status':None,'content_type':None,'failure':None}
        try:
            r=httpx.get(source['endpoint'],timeout=8,follow_redirects=True,headers={'User-Agent':'AEGIS-student-research/0.1','Accept':'*/*'}); row.update(http_status=r.status_code,content_type=r.headers.get('content-type','')); r.raise_for_status()
            if 'json' in row['content_type'] or r.text.lstrip().startswith(('{','[')):
                payload=r.json()
                if isinstance(payload,dict) and ('error' in payload or payload.get('code','Ok')!='Ok'): raise ValueError(str(payload)[:300])
                row['response_schema']=list(payload)[:30] if isinstance(payload,dict) else {'type':'array','rows':len(payload),'item_fields':list(payload[0]) if payload and isinstance(payload[0],dict) else []}
                path=ROOT/f"data/cache/probe_{source['id']}.json"
                existing=json.loads(path.read_text()) if path.exists() else {}
                if 'incident_layers' in existing or 'road_review' in existing:
                    # A connectivity probe must not discard richer separately retrieved evidence.
                    path=ROOT/f"data/cache/connectivity_{source['id']}.json"
                write_json(path,dict(source_url=source['endpoint'],retrieved_at=row['tested_at'],payload=payload))
            elif any(x in source['data_type'] for x in ['JSON','GeoJSON','matrix']): raise ValueError('Expected JSON but received '+row['content_type'])
            row['success']=True; source['last_successful_request']=row['tested_at']
        except Exception as e: row['failure']=f'{type(e).__name__}: {e}'
        row['latency_ms']=round((time.monotonic()-started)*1000); results.append(row); source['test_status']='HTTP success' if row['success'] else 'failed'; source['response_schema']=row.get('response_schema',source['response_schema'])
        print(f"{row['id']:22} {str(row['http_status']):5} {row['latency_ms']:8} {str(row['content_type'])[:28]:28} {row['failure'] or 'success'}",flush=True); time.sleep(.3)
    write_json(ROOT/'reports/api_status.json',results); write_json(ROOT/'config/api_registry.yaml',registry)
    with (ROOT/'config/api_registry.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(registry['sources'][0])); w.writeheader(); w.writerows(registry['sources'])
if __name__=='__main__': main()
