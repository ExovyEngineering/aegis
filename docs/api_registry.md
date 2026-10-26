# API registry

Canonical registry: `config/api_registry.yaml` (YAML-compatible JSON). Google Sheets import: `config/api_registry.csv`. Probe evidence: `reports/api_status.json`. Documentation/catalog HTTP success does not establish a working data integration.

- **fsis_recalls** — USDA FSIS: https://www.fsis.usda.gov/fsis/api/recall/v/1
  Type: official recall JSON. Fallback: Local dated response cache; unavailable banner.
- **fsis_sampling** — USDA FSIS: https://www.fsis.usda.gov/science-data/data-sets-visualizations/laboratory-sampling-data
  Type: download catalog. Fallback: Supplied validated JSON files.
- **fsis_directory** — USDA FSIS: https://www.fsis.usda.gov/inspection/establishments/meat-poultry-and-egg-product-inspection-directory
  Type: download catalog. Fallback: Supplied directory CSV.
- **cdc_beam** — CDC: https://www.cdc.gov/beam/dashboard/
  Type: surveillance dashboard. Fallback: Supplied BEAM exports; separate evidence.
- **cdc_nors** — CDC: https://www.cdc.gov/nors/data/
  Type: outbreak download catalog. Fallback: Supplied NORS; separate evidence.
- **ncei_docs** — NOAA NCEI: https://www.ncei.noaa.gov/support/access-data-service-api-user-documentation
  Type: documentation HTML. Fallback: Coverage warning; no substitution with forecasts.
- **ncei_historical** — NOAA NCEI: https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&stations=USW00003945&startDate=2024-07-01&endDate=2024-07-07&dataTypes=TMAX,TMIN,PRCP&units=metric&format=json
  Type: observed historical weather. Fallback: Coverage warning; forecast remains distinct.
- **nws_alerts** — NOAA NWS: https://api.weather.gov/alerts/active?area=MO
  Type: GeoJSON warnings. Fallback: Dated cached alerts; stale label.
- **nws_points** — NOAA NWS: https://api.weather.gov/points/38.9517,-92.3341
  Type: forecast discovery JSON. Fallback: Open-Meteo forecast.
- **openmeteo** — Open-Meteo: https://api.open-meteo.com/v1/forecast?latitude=38.9517&longitude=-92.3341&hourly=temperature_2m,precipitation,wind_speed_10m&forecast_days=3&timezone=America%2FChicago
  Type: weather forecast JSON. Fallback: Dated cache or coverage warning.
- **openmeteo_archive** — Open-Meteo: https://archive-api.open-meteo.com/v1/archive?latitude=38.9517&longitude=-92.3341&start_date=2024-07-01&end_date=2024-07-07&daily=temperature_2m_max,precipitation_sum&timezone=America%2FChicago
  Type: historical reanalysis JSON. Fallback: Unavailable; not NOAA observations.
- **modot** — MoDOT: https://mapping.modot.mo.gov/arcgis/rest/services/TravelerInformation/TravelerInformationData/MapServer?f=pjson
  Type: ArcGIS layer discovery JSON. Fallback: Report failure; no assertion roads are clear.
- **osrm_route** — OSRM: https://router.project-osrm.org/route/v1/driving/-92.3341,38.9517;-90.1994,38.6270?overview=full&geometries=geojson
  Type: route GeoJSON. Fallback: Straight-line estimated geometry; road factor 1.25 at 65 km/h.
- **osrm_table** — OSRM: https://router.project-osrm.org/table/v1/driving/-92.3341,38.9517;-90.1994,38.6270
  Type: duration matrix JSON. Fallback: Estimated haversine matrix.
- **osrm_docs** — OSRM: https://project-osrm.org/docs/v26.6.1/http
  Type: documentation HTML. Fallback: Bundled request contract.
- **osm_missouri** — Geofabrik / OpenStreetMap: https://download.geofabrik.de/north-america/us/missouri.html
  Type: extract catalog HTML. Fallback: OSM online tiles require internet.
- **food_access** — USDA ERS: https://ers.usda.gov/data-products/food-access-research-atlas/download-the-data
  Type: download catalog HTML. Fallback: Supplied workbook.
- **food_environment** — USDA ERS: https://ers.usda.gov/data-products/food-environment-atlas/data-access-and-documentation-downloads
  Type: download catalog HTML. Fallback: Supplied workbook.