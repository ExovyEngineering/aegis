"""Independent HTTP adapters; cached payloads retain retrieval timestamps."""
import hashlib, json, math, os
from datetime import datetime, timezone
import httpx
from backend.paths import ROOT, write_json, read_json

def now(): return datetime.now(timezone.utc).isoformat()
class CachedHTTP:
    def get(self,url,ttl=3600):
        p=ROOT/'data/cache'/(hashlib.sha256(url.encode()).hexdigest()+'.json')
        previous=read_json(p) if p.exists() else None
        if previous and (datetime.now(timezone.utc)-datetime.fromisoformat(previous['retrieved_at'])).total_seconds()<ttl:
            return dict(previous,cache=True,stale=False)
        try:
            r=httpx.get(url,timeout=10,follow_redirects=True,headers={'User-Agent':os.getenv('AEGIS_USER_AGENT','AEGIS-student-research/0.1'),'Accept':'application/json'}); r.raise_for_status()
            obj={'source_url':url,'retrieved_at':now(),'payload':r.json(),'cache':False,'stale':False}; write_json(p,obj); return obj
        except Exception as e:
            if previous: return dict(previous,cache=True,stale=True,refresh_error=f'{type(e).__name__}: {e}')
            raise

class OpenMeteoForecastAdapter(CachedHTTP):
    def fetch(self):
        return dict(self.get('https://api.open-meteo.com/v1/forecast?latitude=38.9517&longitude=-92.3341&hourly=temperature_2m,precipitation,wind_speed_10m&forecast_days=3&timezone=America%2FChicago'),provenance='weather forecast')
class NWSAlertsAdapter(CachedHTTP):
    def fetch(self): return dict(self.get('https://api.weather.gov/alerts/active?area=MO',300),provenance='official weather alerts')
class NCEIHistoricalAdapter(CachedHTTP):
    def fetch(self,station='USW00003945',start='2024-07-01',end='2024-07-07'):
        from urllib.parse import urlencode
        url='https://www.ncei.noaa.gov/access/services/data/v1?'+urlencode(dict(dataset='daily-summaries',stations=station,startDate=start,endDate=end,dataTypes='TMAX,TMIN,PRCP',units='metric',format='json',includeStationLocation='true'))
        obj=self.get(url,86400)
        if not isinstance(obj['payload'],list) or not obj['payload'] or not {'DATE','STATION'}<=obj['payload'][0].keys(): raise ValueError('NCEI observations absent or schema unexpected')
        return dict(obj,provenance='observed historical weather',coverage_warning='One station/week only; no validated FSIS weather join')
class FSISRecallAdapter(CachedHTTP):
    def fetch(self): return dict(self.get('https://www.fsis.usda.gov/fsis/api/recall/v/1',3600),provenance='official recalls; traceability matching not established')
class MoDOTAdapter(CachedHTTP):
    def fetch(self):
        base='https://mapping.modot.mo.gov/arcgis/rest/services/TravelerInformation/TravelerInformationData/MapServer'
        discovery=self.get(base+'?f=pjson',300)
        if 'error' in discovery['payload']: raise ValueError(str(discovery['payload']['error']))
        layers=discovery['payload'].get('layers',[]); results=[]; failures=[]
        for layer in layers:
            if 'future' in layer['name'].lower(): continue
            try:
                item=self.get(base+f"/{layer['id']}/query?where=1%3D1&outFields=*&outSR=4326&f=geojson",300)
                if 'error' in item['payload']: raise ValueError(str(item['payload']['error']))
                if item['payload'].get('type')!='FeatureCollection': raise ValueError('Expected GeoJSON FeatureCollection')
                results.append(dict(item,layer_id=layer['id'],layer_name=layer['name']))
            except Exception as e: failures.append({'layer_id':layer['id'],'error':f'{type(e).__name__}: {e}'})
        incomplete=bool(failures) or any(r['payload'].get('exceededTransferLimit',False) for r in results)
        stale=bool(discovery.get('stale')) or any(item.get('stale',False) for item in results)
        refresh_error=discovery.get('refresh_error') or '; '.join(f"Layer {item['layer_id']}: {item['refresh_error']}" for item in results if item.get('refresh_error')) or None
        return dict(discovery,stale=stale,refresh_error=refresh_error,incident_layers=results,layer_failures=failures,provenance='official road incidents',coverage_complete=bool(results) and not incomplete,coverage_warning='Partial coverage: failed or truncated layers; absence does not imply a clear road' if incomplete else 'Queried current incident, work-zone, flood and winter layers; future work zones excluded. Point/line duplicates may describe the same event.')

def distance(a,b):
    lon1,lat1,lon2,lat2=map(math.radians,[*a,*b]); d=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371000*2*math.asin(min(1,math.sqrt(d)))
class OSRMRoutingAdapter(CachedHTTP):
    @staticmethod
    def validate(coordinates):
        if len(coordinates)<2 or any(len(c)!=2 or not -180<=c[0]<=180 or not -90<=c[1]<=90 for c in coordinates): raise ValueError('At least two valid longitude,latitude pairs required')
    def route(self,coordinates,alternatives=False):
        self.validate(coordinates)
        url=os.getenv('OSRM_BASE_URL','https://router.project-osrm.org')+'/route/v1/driving/'+';'.join(f'{x},{y}' for x,y in coordinates)+f'?overview=full&geometries=geojson&alternatives={str(alternatives).lower()}'
        try:
            obj=self.get(url)
            if obj['payload'].get('code')!='Ok' or not obj['payload'].get('routes'): raise ValueError('No OSRM route')
            return dict(obj,provenance='OSRM driving route; truck restrictions and MoDOT closures not incorporated',fallback=False)
        except Exception as e:
            meters=sum(distance(a,b)*1.25 for a,b in zip(coordinates,coordinates[1:])); return {'fallback':True,'provenance':'estimated travel; straight-line visualization, not road geometry','error':str(e),'payload':{'routes':[{'geometry':{'type':'LineString','coordinates':coordinates},'distance':meters,'duration':meters/(65000/3600)}]}}
    def matrix(self,coordinates):
        self.validate(coordinates)
        url=os.getenv('OSRM_BASE_URL','https://router.project-osrm.org')+'/table/v1/driving/'+';'.join(f'{x},{y}' for x,y in coordinates)+'?annotations=duration,distance'
        try:
            obj=self.get(url)
            if obj['payload'].get('code')!='Ok': raise ValueError('No OSRM matrix')
            return dict(obj,fallback=False)
        except Exception as e: return {'fallback':True,'error':str(e),'provenance':'estimated haversine distance x 1.25 / 65 km/h','payload':{'durations':[[distance(a,b)*1.25/(65000/3600) for b in coordinates] for a in coordinates],'distances':[[distance(a,b)*1.25 for b in coordinates] for a in coordinates]}}
