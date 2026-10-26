import sys, csv, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.paths import ROOT

SOURCES=[
('fsis_recalls','USDA FSIS','https://www.fsis.usda.gov/fsis/api/recall/v/1','official recall JSON','national','daily','Local dated response cache; unavailable banner'),
('fsis_sampling','USDA FSIS','https://www.fsis.usda.gov/science-data/data-sets-visualizations/laboratory-sampling-data','download catalog','national','quarterly','Supplied validated JSON files'),
('fsis_directory','USDA FSIS','https://www.fsis.usda.gov/inspection/establishments/meat-poultry-and-egg-product-inspection-directory','download catalog','national','monthly','Supplied directory CSV'),
('cdc_beam','CDC','https://www.cdc.gov/beam/dashboard/','surveillance dashboard','national','provider dependent','Supplied BEAM exports; separate evidence'),
('cdc_nors','CDC','https://www.cdc.gov/nors/data/','outbreak download catalog','national','annual','Supplied NORS; separate evidence'),
('ncei_docs','NOAA NCEI','https://www.ncei.noaa.gov/support/access-data-service-api-user-documentation','documentation HTML','global','on demand','Coverage warning; no substitution with forecasts'),
('ncei_historical','NOAA NCEI','https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&stations=USW00003945&startDate=2024-07-01&endDate=2024-07-07&dataTypes=TMAX,TMIN,PRCP&units=metric&format=json','observed historical weather','station USW00003945; location must be verified before joining','daily','Coverage warning; forecast remains distinct'),
('nws_alerts','NOAA NWS','https://api.weather.gov/alerts/active?area=MO','GeoJSON warnings','Missouri','5 minutes','Dated cached alerts; stale label'),
('nws_points','NOAA NWS','https://api.weather.gov/points/38.9517,-92.3341','forecast discovery JSON','Columbia MO','daily','Open-Meteo forecast'),
('openmeteo','Open-Meteo','https://api.open-meteo.com/v1/forecast?latitude=38.9517&longitude=-92.3341&hourly=temperature_2m,precipitation,wind_speed_10m&forecast_days=3&timezone=America%2FChicago','weather forecast JSON','Columbia MO','hourly','Dated cache or coverage warning'),
('openmeteo_archive','Open-Meteo','https://archive-api.open-meteo.com/v1/archive?latitude=38.9517&longitude=-92.3341&start_date=2024-07-01&end_date=2024-07-07&daily=temperature_2m_max,precipitation_sum&timezone=America%2FChicago','historical reanalysis JSON','Columbia MO','on demand','Unavailable; not NOAA observations'),
('modot','MoDOT','https://mapping.modot.mo.gov/arcgis/rest/services/TravelerInformation/TravelerInformationData/MapServer?f=pjson','ArcGIS layer discovery JSON','Missouri','5 minutes','Report failure; no assertion roads are clear'),
('osrm_route','OSRM','https://router.project-osrm.org/route/v1/driving/-92.3341,38.9517;-90.1994,38.6270?overview=full&geometries=geojson','route GeoJSON','Missouri route','on demand','Straight-line estimated geometry; road factor 1.25 at 65 km/h'),
('osrm_table','OSRM','https://router.project-osrm.org/table/v1/driving/-92.3341,38.9517;-90.1994,38.6270','duration matrix JSON','Missouri OD','on demand','Estimated haversine matrix'),
('osrm_docs','OSRM','https://project-osrm.org/docs/v26.6.1/http','documentation HTML','global','on demand','Bundled request contract'),
('osm_missouri','Geofabrik / OpenStreetMap','https://download.geofabrik.de/north-america/us/missouri.html','extract catalog HTML','Missouri','daily','OSM online tiles require internet'),
('food_access','USDA ERS','https://ers.usda.gov/data-products/food-access-research-atlas/download-the-data','download catalog HTML','US census tracts','release dependent','Supplied workbook'),
('food_environment','USDA ERS','https://ers.usda.gov/data-products/food-environment-atlas/data-access-and-documentation-downloads','download catalog HTML','US counties','release dependent','Supplied workbook')]

def main():
    rows=[]
    for key,provider,url,kind,scope,refresh,fallback in SOURCES:
        rows.append(dict(id=key,provider=provider,endpoint=url,documentation=url if key!='ncei_historical' else SOURCES[5][2],authentication='No key used for public probe; NWS requires descriptive User-Agent',request_parameters=url.partition('?')[2] or 'none',data_type=kind,geographic_scope=scope,rate_limits='Not verified; sequential probes, 0.3 second spacing; honor 429',expected_refresh=refresh,test_status='not tested',last_successful_request=None,response_schema='Inspect successful response; HTML catalogs are not data feeds',known_limitations='Coverage and freshness must be validated; public services provide no availability guarantee',operational_fallback=fallback))
    (ROOT/'config').mkdir(exist_ok=True)
    # JSON is valid YAML 1.2 and avoids a bootstrap YAML dependency.
    (ROOT/'config/api_registry.yaml').write_text(json.dumps({'sources':rows},indent=2),encoding='utf-8')
    with (ROOT/'config/api_registry.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    (ROOT/'docs/api_registry.md').write_text('# API registry\n\nCanonical registry: `config/api_registry.yaml` (YAML-compatible JSON). Google Sheets import: `config/api_registry.csv`. Probe evidence: `reports/api_status.json`. Documentation/catalog HTTP success does not establish a working data integration.\n\n'+ '\n'.join(f"- **{r['id']}** — {r['provider']}: {r['endpoint']}\n  Type: {r['data_type']}. Fallback: {r['operational_fallback']}." for r in rows),encoding='utf-8')
if __name__=='__main__': main()
