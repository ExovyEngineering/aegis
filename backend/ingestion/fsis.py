from pathlib import Path
import ijson
import pandas as pd
from backend.paths import data_dir, ROOT, write_json

class FSISPoultryAdapter:
    def ingest(self,folder=None):
        rows=[]; sources=[]
        for p in sorted(Path(folder or data_dir()).rglob('*.json')):
            if any(x in p.parts for x in ('.venv','cache','manifests','processed','node_modules','.tools')): continue
            with p.open('rb') as f: metadata=next(ijson.items(f,'item.metadata'),{})
            if 'raw poultry product sampling' not in metadata.get('data_product_name','').lower(): continue
            sources.append({'path':str(p),'metadata_creation_date':metadata.get('creation_date'),'declared_records':metadata.get('data_records')})
            with p.open('rb') as f:
                for r in ijson.items(f,'item.data.primary_table_data.item'):
                    required={'form_id','sample_number','establishment_id','collection_date','salmonella_sp_analysis'}
                    if not required<=r.keys(): raise ValueError(f'{p}: missing fields {required-r.keys()}')
                    rows.append({k:r.get(k) for k in ['form_id','sample_number','establishment_id','establishment_state','project_code','collection_date','salmonella_sp_analysis','salmonella_sp_analysis_canceled']}|{'source_file':p.name})
        df=pd.DataFrame(rows)
        if df.empty: raise ValueError('No metadata-confirmed FSIS raw poultry primary tables found')
        duplicates=int(df.duplicated(['form_id','sample_number']).sum())
        conflicting=df.groupby(['form_id','sample_number'])['salmonella_sp_analysis'].nunique().gt(1).sum()
        if conflicting: raise ValueError(f'{conflicting} conflicting repeated sample IDs; resolve before modeling')
        df=df.drop_duplicates(['form_id','sample_number']); df['collection_date']=pd.to_datetime(df['collection_date'],errors='coerce')
        out=ROOT/'data/processed'; out.mkdir(parents=True,exist_ok=True); df.to_parquet(out/'fsis_poultry.parquet',index=False)
        write_json(out/'fsis_provenance.json',{'sources':sources,'rows':len(df),'duplicates_removed':duplicates,'invalid_dates':int(df.collection_date.isna().sum()),'availability_warning':'Row-level result/publication dates absent; metadata creation date is snapshot availability. Retrospective features use a conservative assumed 90-day reporting lag; prospective validity unproven.','target':'Primary Salmonella Positive/Negative; no secondary typing tests; national selected sampling, not consumer illness.'})
        return df
