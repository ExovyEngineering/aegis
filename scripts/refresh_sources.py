import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.adapters import MoDOTAdapter, NCEIHistoricalAdapter, OpenMeteoForecastAdapter,NWSAlertsAdapter,FSISRecallAdapter,OSRMRoutingAdapter
from backend.paths import ROOT,write_json
def main():
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument('--source',choices=['all','modot','ncei_historical','openmeteo','nws_alerts','fsis_recalls','osrm_route'],default='all'); args=parser.parse_args()
    adapters={'modot':MoDOTAdapter,'ncei_historical':NCEIHistoricalAdapter,'openmeteo':OpenMeteoForecastAdapter,'nws_alerts':NWSAlertsAdapter,'fsis_recalls':FSISRecallAdapter}
    for key,adapter in adapters.items():
        if args.source not in ('all',key):continue
        try:
            result=adapter().fetch(); write_json(ROOT/f'data/cache/probe_{key}.json',result); print(key, 'captured at',result['retrieved_at'],result.get('coverage_warning',''),flush=True)
        except Exception as e:print(key,f'{type(e).__name__}: {e}',flush=True)
    if args.source in ('all','osrm_route'):
        result=OSRMRoutingAdapter().route([[-92.3341,38.9517],[-90.1994,38.6270]],True)
        from backend.route_review import review_routes
        import json
        p=ROOT/'data/cache/probe_modot.json'; result['road_review']=review_routes(result,json.loads(p.read_text()) if p.exists() else None)
        write_json(ROOT/'data/cache/probe_osrm_route.json',result);write_json(ROOT/'reports/route_review.json',result['road_review']); print('OSRM route alternatives',len(result['payload']['routes']),flush=True)
if __name__=='__main__':main()
