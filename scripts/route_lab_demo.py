"""Reproduce farm/fleet routing; use --routing osrm for bounded live road requests."""
import sys,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.route_lab import plan_routes
from backend.paths import ROOT,write_json
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--routing',choices=['estimated','osrm'],default='estimated');parser.add_argument('--preset',choices=['farm','regional','both'],default='both');args=parser.parse_args()
    results=[]
    for preset in (['farm','regional'] if args.preset=='both' else [args.preset]):
        result=plan_routes(preset=preset,routing=args.routing);results.append(result)
        print(preset,result['solver_status'],'matrix fallback:',result['matrix_fallback'],'routes:',len(result['routes']),'geometry fallbacks:',sum(r['fallback'] for r in result['routes']),result['summary'],flush=True)
    write_json(ROOT/f'reports/route_lab_{args.routing}.json',results)
if __name__=='__main__':main()
