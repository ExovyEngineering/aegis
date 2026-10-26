import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.paths import ROOT,write_json
from backend.simulation import seed_network
if __name__=='__main__':
    write_json(ROOT/'data/processed/demo_network.json',seed_network()); print('Seeded deterministic Missouri network: 20261026')
