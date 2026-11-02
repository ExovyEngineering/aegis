import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.ingestion.fsis import FSISPoultryAdapter
from backend.paths import data_dir
if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Ingest metadata-confirmed primary FSIS poultry exports, recording file-level failures.')
    parser.add_argument('--data-dir',type=Path,default=data_dir());args=parser.parse_args()
    print('FSIS primary rows:',len(FSISPoultryAdapter().ingest(args.data_dir)))
