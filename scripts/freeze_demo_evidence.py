"""Freeze actual successful responses as explicit dated offline fixtures, never synthesize."""
import sys, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.paths import ROOT,write_json
def main():
    for source in ['fsis_recalls','openmeteo','nws_alerts','ncei_historical','openmeteo_archive','modot','osrm_route']:
        p=ROOT/f'data/cache/probe_{source}.json'
        if not p.exists():continue
        item=json.loads(p.read_text()); item['fixture_note']='Actual dated API response frozen for offline demo; not live. Never use as current operational evidence.'
        if source=='fsis_recalls' and isinstance(item['payload'],list):
            item['fixture_total_original_records']=len(item['payload']);item['payload']=item['payload'][:5];item['fixture_note']+=' Only first five returned recalls retained; not comprehensive.'
        write_json(ROOT/f'data/fixtures/{source}.json',item)
if __name__=='__main__':main()
