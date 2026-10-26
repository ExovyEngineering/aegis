"""Validate bounded NOAA/NCEI daily observations without inventing observations.

The Access Data Service returns metric units when explicitly requested. Its
attribute tuple is measurement flag, quality flag, source flag, observation time.
Original date-only reporting periods and attribute strings are preserved.
"""
from collections import Counter
from datetime import date, datetime, timezone
import math
from backend.adapters import distance

METRICS=('TMAX','TMIN','PRCP')
CITIES=(
    {'city':'Columbia','station_id':'USW00003945','coordinates':[-92.3341,38.9517]},
    {'city':'Kansas City','station_id':'USW00003947','coordinates':[-94.5786,39.0997]},
    {'city':'Jefferson City','station_id':'USW00003963','coordinates':[-92.1735,38.5767]},
    {'city':'Springfield','station_id':'USW00013995','coordinates':[-93.2923,37.2090]},
    {'city':'St. Louis','station_id':'USW00013994','coordinates':[-90.1994,38.6270]},
)

def requested_dates(start,end):
    from datetime import timedelta
    first,last=date.fromisoformat(start),date.fromisoformat(end)
    if first>last: raise ValueError('start must be on or before end')
    if (last-first).days>730: raise ValueError('Acquisition is bounded to at most 731 calendar days per station')
    return {(first+timedelta(days=i)).isoformat() for i in range((last-first).days+1)}

def numeric_value(value):
    if value in (None,'','NULL','-9999',-9999): return None
    try:value=float(value)
    except (ValueError,TypeError):return None
    return value if math.isfinite(value) else None

def profile_station(payload,station,start,end,retrieved_at,source_url=None):
    """Return actual coverage and quality counts; reject identity/location mismatches."""
    if not isinstance(payload,list) or not payload:raise ValueError('NCEI returned no observation rows')
    expected=requested_dates(start,end)
    required={'DATE','STATION','LATITUDE','LONGITUDE'}
    if not required<=payload[0].keys():raise ValueError(f'NCEI missing fields: {sorted(required-payload[0].keys())}')
    ids={r.get('STATION') for r in payload}
    if ids!={station['station_id']}:raise ValueError(f'Station identity mismatch: requested {station["station_id"]}, received {sorted(map(str,ids))}')
    latitude=numeric_value(payload[0].get('LATITUDE'));longitude=numeric_value(payload[0].get('LONGITUDE'))
    if latitude is None or longitude is None or not(-90<=latitude<=90 and -180<=longitude<=180):raise ValueError('Missing or invalid verified station coordinates')
    gap=distance(station['coordinates'],[longitude,latitude])/1000
    if gap>60:raise ValueError(f'Station location is {gap:.1f} km from {station["city"]}; exceeds 60 km representative-station screening limit')
    dates=[r.get('DATE') for r in payload]
    for value in dates:
        try:date.fromisoformat(value)
        except (TypeError,ValueError) as e:raise ValueError(f'Unexpected observation DATE: {value!r}') from e
    duplicates=[d for d,n in Counter(dates).items() if n>1]
    if duplicates:raise ValueError(f'Duplicate station/day rows: {duplicates[:5]}')
    if set(dates)-expected:raise ValueError('Returned dates outside the requested interval')
    metric_coverage={}
    for metric in METRICS:
        numeric=0;quality_pass=0;flagged=0;unknown=0;measurement_flags=Counter();quality_flags=Counter()
        for row in payload:
            value=numeric_value(row.get(metric))
            if value is None:continue
            numeric+=1;raw=row.get(metric+'_ATTRIBUTES')
            if not isinstance(raw,str):unknown+=1;continue
            flags=raw.split(',')
            if len(flags)<3:unknown+=1;continue
            measurement_flags[flags[0] or '(blank)']+=1;quality_flags[flags[1] or '(blank)']+=1
            if flags[1].strip():flagged+=1
            else:quality_pass+=1
        metric_coverage[metric]={'numeric_days':numeric,'quality_pass_days':quality_pass,'flagged_days':flagged,'quality_unknown_days':unknown,'missing_days':len(expected)-numeric,'measurement_flags':dict(measurement_flags),'quality_flags':dict(quality_flags),'units':'mm' if metric=='PRCP' else 'degrees C'}
    missing=sorted(expected-set(dates))
    metrics_complete=all(c['quality_pass_days']==len(expected) for c in metric_coverage.values())
    return {'city':station['city'],'station_id':station['station_id'],'station_name':payload[0].get('NAME'),'latitude':latitude,'longitude':longitude,'distance_to_city_km':round(gap,3),'expected_days':len(expected),'observed_days':len(dates),'missing_days':len(missing),'missing_date_sample':missing[:15],'date_start':min(dates),'date_end':max(dates),'metric_coverage':metric_coverage,'retrieved_at':retrieved_at,'source_url':source_url,'status':'complete bounded extract' if not missing and metrics_complete else 'partial','original_date_semantics':'DATE is the provider daily reporting-period label. Not converted to local midnight; observation times remain in *_ATTRIBUTES.'}

def coverage_report(stations,start,end):
    expected=len(requested_dates(start,end))*len(stations);observed=sum(s.get('observed_days',0) for s in stations);success=sum('error' not in s for s in stations)
    complete=success==len(stations) and observed==expected and all(s['status']=='complete bounded extract' for s in stations)
    observed_metrics=sum(c['numeric_days'] for s in stations for c in s.get('metric_coverage',{}).values())
    return {'status':'complete bounded extract' if complete else 'partial' if success else 'failed','generated_at':datetime.now(timezone.utc).isoformat(),'provenance':'observed historical weather','start_date':start,'end_date':end,'station_count':success,'requested_station_count':len(stations),'expected_station_days':expected,'observed_station_days':observed,'coverage_fraction':observed/expected if expected else 0,'metric_coverage_fraction':observed_metrics/(expected*len(METRICS)) if expected else 0,'missing_metric_values':expected*len(METRICS)-observed_metrics,'stations':stations,'model_join_status':'not joined; publication timing and scientific linkage unvalidated','limitations':['Coverage applies only to the requested station/date window, not all Missouri establishments or historical training years.','Station-day coverage counts returned date rows; per-variable numeric and quality coverage are separate and may be incomplete.','Station airport observations are ambient weather, not shipment exposure or cargo telemetry.','Daily reporting periods may use local observation times; UTC/local midnight equivalence is not assumed.','Blank quality flags mean no failed documented quality check; they do not prove zero measurement error.','Actual observation publication/availability timestamps are not present; retrieval timestamps are preserved separately.','Metric units are requested explicitly through the documented NCEI Access Data Service; no tenths-to-units reinterpretation is applied.']}
