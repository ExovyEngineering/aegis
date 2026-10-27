from pathlib import Path
from datetime import datetime,timezone
import ijson
import pandas as pd
from backend.paths import data_dir, ROOT, write_json
from backend.ingestion.common import source_files,sha256_file,exact_error,publish_parquet

FIELDS=['form_id','sample_number','establishment_id','establishment_state','project_code','collection_date','salmonella_sp_analysis','salmonella_sp_analysis_canceled']
REQUIRED={'form_id','sample_number','establishment_id','collection_date','salmonella_sp_analysis','salmonella_sp_analysis_canceled'}


def valid_identity(value):return value is not None and str(value).strip() not in {'','NULL'}


def read_poultry_source(path):
    """Read metadata and primary observations separately, with bounded streaming."""
    with path.open('rb') as stream:metadata_rows=list(ijson.items(stream,'item.metadata'))
    poultry=[m for m in metadata_rows if isinstance(m,dict) and 'raw poultry product sampling' in str(m.get('data_product_name','')).lower()]
    if not poultry:return None
    if len(metadata_rows)!=1:raise ValueError('Expected one FSIS product metadata object; mixed-product files require a separate adapter')
    metadata=poultry[0];rows=[]
    with path.open('rb') as stream:
        for row in ijson.items(stream,'item.data.primary_table_data.item'):
            if not isinstance(row,dict):raise ValueError('FSIS primary observation is not an object')
            if not REQUIRED<=row.keys():raise ValueError(f'Missing primary fields: {sorted(REQUIRED-row.keys())}')
            if not all(valid_identity(row.get(k)) for k in ('form_id','sample_number','establishment_id')):
                raise ValueError('Missing primary sample/establishment identity; cannot deduplicate safely')
            rows.append({key:row.get(key) for key in FIELDS})
    declared=metadata.get('data_records',{}).get('primary') if isinstance(metadata.get('data_records'),dict) else None
    if declared is not None:
        try:expected=int(declared)
        except (ValueError,TypeError) as error:raise ValueError(f'Invalid declared primary record count: {declared!r}') from error
        if expected!=len(rows):raise ValueError(f'FSIS primary row count mismatch: declared {expected}, parsed {len(rows)}')
    return metadata,rows

class FSISPoultryAdapter:
    def ingest(self,folder=None,output_dir=None,report_path=None):
        folder=Path(folder or data_dir()).resolve();out=Path(output_dir or ROOT/'data/processed').resolve()
        report_path=Path(report_path or ROOT/'reports/fsis_ingestion.json')
        rows=[];sources=[];files=[];seen={}
        for path in source_files(folder,{'.json'},excluded=(out,report_path)):
            relative=path.relative_to(folder).as_posix()
            entry={'path':str(path),'source_file':relative,'file':path.name};files.append(entry)
            try:
                digest=sha256_file(path);entry.update(sha256=digest,bytes=path.stat().st_size)
                if digest in seen:
                    entry.update(status='duplicate',duplicate_of=seen[digest]);continue
                parsed=read_poultry_source(path)
                if parsed is None:
                    entry.update(status='unrecognized',note='Not one metadata-confirmed raw-poultry primary product; not merged.');continue
                metadata,file_rows=parsed
                if sha256_file(path)!=digest:raise ValueError('Source bytes changed during ingestion; observations not accepted')
                entry.update(status='ingested',rows=len(file_rows));seen[digest]=relative
                sources.append({'path':str(path),'source_file':relative,'sha256':digest,'metadata_creation_date':metadata.get('creation_date'),'declared_records':metadata.get('data_records'),'parsed_primary_rows':len(file_rows)})
                rows.extend(dict(row,source_file=relative) for row in file_rows)
            except Exception as error:entry.update(status='failed',error=exact_error(error))
        report={'schema_version':1,'generated_at':datetime.now(timezone.utc).isoformat(),'data_dir':str(folder),
                'files':files,'errors':[entry for entry in files if entry['status']=='failed'],
                'accepted_sources':len(sources),'status':'partial' if any(entry['status']=='failed' for entry in files) else 'complete'}
        df=pd.DataFrame(rows)
        if df.empty:
            report.update(status='failed',error='No metadata-confirmed FSIS raw poultry primary tables found',previous_output_retained=(out/'fsis_poultry.parquet').exists())
            write_json(report_path,report);raise ValueError(report['error'])
        duplicates=int(df.duplicated(['form_id','sample_number']).sum())
        # An unchanged result alone cannot justify silently discarding revised identity,
        # dates, cancellation or geography. Compare all retained observation fields.
        conflicting=df.groupby(['form_id','sample_number'],dropna=False)[FIELDS].nunique(dropna=False).gt(1).any(axis=1).sum()
        if conflicting:
            report.update(status='failed',error=f'{conflicting} conflicting repeated sample IDs; resolve before modeling',previous_output_retained=(out/'fsis_poultry.parquet').exists())
            write_json(report_path,report);raise ValueError(report['error'])
        df=df.drop_duplicates(['form_id','sample_number']); df['collection_date']=pd.to_datetime(df['collection_date'],errors='coerce')
        publish_parquet(df,out/'fsis_poultry.parquet')
        provenance={'source_key':'fsis_raw_poultry_primary','status':report['status'],'sources':sources,'rows':len(df),'duplicates_removed':duplicates,'invalid_dates':int(df.collection_date.isna().sum()),'output_sha256':sha256_file(out/'fsis_poultry.parquet'),
                    'file_errors':report['errors'],'availability_warning':'Row-level result/publication dates absent; metadata creation dates describe the source snapshot, not verified public release. Retrospective features use an assumed 90-day reporting lag; prospective validity unproven.',
                    'target':'Primary Salmonella Positive/Negative; no secondary typing tests; national selected sampling, not consumer illness.'}
        write_json(out/'fsis_provenance.json',provenance)
        report.update(rows=len(df),duplicates_removed=duplicates,output=str(out/'fsis_poultry.parquet'),output_sha256=provenance['output_sha256'])
        write_json(report_path,report)
        return df
