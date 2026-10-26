"""Acquire a bounded five-station daily NOAA extract; cache original response bytes."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse,hashlib,json,time,os
from datetime import datetime,timezone
from urllib.parse import urlencode
import httpx
from backend.paths import ROOT,write_json
from backend.weather_coverage import CITIES,profile_station,coverage_report,requested_dates

def acquire(start,end,refresh=False,stations=CITIES):
    requested_dates(start,end);results=[]
    folder=ROOT/'data/external/noaa';folder.mkdir(parents=True,exist_ok=True)
    for station in stations:
        station_id=station['station_id'];stem=f'{station_id}_{start}_{end}'
        params=dict(dataset='daily-summaries',stations=station_id,startDate=start,endDate=end,dataTypes='TMAX,TMIN,PRCP',units='metric',format='json',includeStationLocation='true',includeStationName='true',includeAttributes='true')
        url='https://www.ncei.noaa.gov/access/services/data/v1?'+urlencode(params)
        raw=folder/(stem+'.response.json');meta=folder/(stem+'.metadata.json')
        try:
            if raw.exists() and meta.exists() and not refresh:
                metadata=json.loads(meta.read_text(encoding='utf-8'));body=raw.read_bytes()
                if hashlib.sha256(body).hexdigest()!=metadata['sha256']:raise ValueError('Cached NOAA response checksum mismatch')
            else:
                with httpx.stream('GET',url,timeout=20,follow_redirects=True,headers={'User-Agent':os.getenv('AEGIS_USER_AGENT','AEGIS-student-research/0.1')}) as response:
                    response.raise_for_status();chunks=[];length=0
                    for chunk in response.iter_bytes(65536):
                        length+=len(chunk)
                        if length>10*1024*1024:raise ValueError('Response exceeded 10 MiB acquisition safety bound')
                        chunks.append(chunk)
                    body=b''.join(chunks)
                    # Confirm syntax before retaining a new response as cache evidence.
                    payload=json.loads(body)
                    if isinstance(payload,dict) and 'error' in payload:raise ValueError(str(payload))
                    metadata={'source_url':url,'retrieved_at':datetime.now(timezone.utc).isoformat(),'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'http_status':response.status_code,'content_type':response.headers.get('content-type'),'request_parameters':params,'provenance':'observed historical weather'}
                    if raw.exists():
                        archive_stem=stem+'.'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
                        (folder/(archive_stem+'.response.json')).write_bytes(raw.read_bytes())
                        if meta.exists():(folder/(archive_stem+'.metadata.json')).write_bytes(meta.read_bytes())
                    raw.write_bytes(body);write_json(meta,metadata)
                time.sleep(.3)
            result=profile_station(json.loads(body),station,start,end,metadata['retrieved_at'],url)
            result['raw_response_path']=str(raw.relative_to(ROOT));result['sha256']=metadata['sha256'];results.append(result)
            print(station['city'],result['status'],f"{result['observed_days']}/{result['expected_days']} days",result['station_name'],flush=True)
        except Exception as e:
            error=f'{type(e).__name__}: {e}';results.append(dict(station,status='failed',error=error,source_url=url,observed_days=0));print(station['city'],error,flush=True)
    report=coverage_report(results,start,end);write_json(ROOT/'reports/noaa_coverage.json',report)
    lines=['# Bounded NOAA/NCEI coverage',f"Generated {report['generated_at']}",'',f"Status: **{report['status']}**. {report['observed_station_days']} of {report['expected_station_days']} requested station-days. {report['start_date']} through {report['end_date']}.",'','| City | Station | Coordinates | Observed / expected | TMAX quality pass | TMIN quality pass | PRCP quality pass | Status |','|---|---|---|---:|---:|---:|---:|---|']
    for s in results:
        metrics=s.get('metric_coverage',{});lines.append(f"| {s['city']} | {s['station_id']} | {s.get('latitude','?')}, {s.get('longitude','?')} | {s.get('observed_days',0)} / {s.get('expected_days',len(requested_dates(start,end)))} | {metrics.get('TMAX',{}).get('quality_pass_days','?')} | {metrics.get('TMIN',{}).get('quality_pass_days','?')} | {metrics.get('PRCP',{}).get('quality_pass_days','?')} | {s.get('error',s['status'])} |")
    lines+=['',report['model_join_status'],'']+['- '+x for x in report['limitations']]+['','Sources: [NCEI Access Data Service](https://www.ncei.noaa.gov/support/access-data-service-api-user-documentation), [GHCN-Daily format and quality flags](https://www.ncei.noaa.gov/pub/data/ghcn/daily/readme.txt).','Original response bytes and SHA-256 metadata: `data/external/noaa/`. No supplied raw downloads modified.']
    (ROOT/'reports/noaa_coverage.md').write_text('\n'.join(lines),encoding='utf-8')
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--start',default='2025-01-01');p.add_argument('--end',default='2026-06-30');p.add_argument('--refresh',action='store_true');args=p.parse_args();acquire(args.start,args.end,args.refresh)
if __name__=='__main__':main()
