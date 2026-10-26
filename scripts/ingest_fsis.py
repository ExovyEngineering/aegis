import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.ingestion.fsis import FSISPoultryAdapter
if __name__=='__main__': print('FSIS primary rows:',len(FSISPoultryAdapter().ingest()))
