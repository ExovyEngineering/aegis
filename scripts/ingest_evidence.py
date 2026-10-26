import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.paths import ROOT,data_dir,write_json
from backend.ingestion.nors import NORSAdapter
from backend.ingestion.beam import BEAMAdapter
from backend.ingestion.establishments import EstablishmentAdapter
def main():
    reports=[]
    for adapter,pattern,name in [(NORSAdapter(),'NORS*.csv','nors'),(BEAMAdapter(),'BEAM*.csv','beam'),(EstablishmentAdapter(),'MPI*.csv','establishments')]:
        for i,p in enumerate(data_dir().glob(pattern)):
            try:
                df=adapter.read(p); dest=ROOT/f'data/processed/{name}_{i}.parquet'; dest.parent.mkdir(parents=True,exist_ok=True); df.to_parquet(dest,index=False); reports.append({'file':p.name,'source':name,'rows':len(df),'columns':list(df),'output':str(dest)})
            except Exception as e: reports.append({'file':p.name,'error':f'{type(e).__name__}: {e}'})
    write_json(ROOT/'reports/evidence_ingestion.json',reports)
if __name__=='__main__':main()
