"""Real loopback HTTP check of the built UI and backend, without mutating state."""
import sys,re,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from backend.paths import ROOT,write_json
def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--base-url',default='http://127.0.0.1:8000');args=parser.parse_args()
    result=[]
    with httpx.Client(base_url=args.base_url,timeout=15) as client:
        response=client.get('/');response.raise_for_status();assert 'AEGIS' in response.text;result.append({'path':'/','status':response.status_code})
        assets=re.findall(r'(?:src|href)="(/assets/[^\"]+)"',response.text)
        assert assets,'No built frontend assets found'
        for path in assets:
            response=client.get(path);response.raise_for_status();result.append({'path':path,'status':response.status_code})
        for path in ['health','network','coverage','scenarios','model','inventory','evidence/fsis_recalls','evidence/openmeteo','evidence/modot','facilities','driver','audit','dispatch','operations/presets','planning/projects','data/catalog','data/fsis_poultry?limit=2','project-status','drive/T01']:
            response=client.get('/api/'+path);response.raise_for_status();response.json();result.append({'path':'/api/'+path,'status':response.status_code})
    write_json(ROOT/'reports/http_smoke.json',{'base_url':args.base_url,'checks':result,'passed':len(result),'browser_visual_qa':False});print(json.dumps(result,indent=2))
if __name__=='__main__':main()
