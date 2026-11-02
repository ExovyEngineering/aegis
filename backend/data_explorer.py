"""Read-only bounded browsing of explicitly recognized, separately ingested evidence."""
import hashlib
import json
from pathlib import Path
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq
from fastapi import APIRouter, HTTPException, Query
from backend.paths import read_json
from backend.ingestion.beam import beam_identity
from backend.ingestion.nors import NORS_COLUMNS
from backend.ingestion.establishments import DIRECTORY_COLUMNS

SOURCES = {
    'fsis_poultry':('FSIS raw-poultry samples', 'Selected national laboratory sampling; primary test outcomes, not consumer illness or supplier ratings.'),
    'nors_0':('CDC NORS outbreaks', 'Historical outbreak evidence. No linkage to individual FSIS samples, fictional lots or suppliers is established.'),
    'beam_0':('CDC BEAM regional isolates', 'Public surveillance export; HHS regions are not individual farms or distribution routes.'),
    'beam_1':('CDC BEAM source report', 'Surveillance source categories include human, animal and food entries; inspect Source Type and Source Site. Not an FSIS training label.'),
    'beam_2':('CDC BEAM burden / trajectory', 'Aggregated historical serotype summaries with provider-defined year windows; not a forecast.'),
    'beam_3':('CDC BEAM illnesses / outbreaks', 'Aggregated historical illness/outbreak counts; not a shipment risk probability.'),
    'beam_4':('CDC BEAM common serotypes', 'Surveillance serotype summary; isolate counts are not consumer illness probabilities.'),
    'establishments_0':('FSIS Missouri establishments', 'Official directory coordinates; no fictional supply contract, shipment or recall match is implied.'),
}
MAX_DERIVED_BYTES=64*1024*1024


def create_data_router(root:Path):
    router=APIRouter(tags=['Read-only source data explorer'])

    def provenance(source):
        if source=='fsis_poultry':
            path=root/'data/processed/fsis_provenance.json'
            if not path.exists():return {'ingestion_status':'legacy output; source manifest unavailable','recognition':'Legacy derived table; input snapshot identity has not been checked by the current manifest.'}
            saved=read_json(path)
            if not isinstance(saved,dict):raise ValueError('FSIS provenance has an unsupported schema')
            info={'ingestion_status':saved.get('status','legacy provenance'),'source_key':saved.get('source_key','fsis_raw_poultry_primary'),
                  'input_files':[dict(entry,file=Path(entry.get('path','')).name) for entry in saved.get('sources',[])],
                  'output_sha256':saved.get('output_sha256'),'recognition':'Embedded raw-poultry product metadata and primary observation schema.',
                  'ingestion_errors':saved.get('file_errors',[])}
            latest=root/'reports/fsis_ingestion.json'
            if latest.exists():
                attempt=read_json(latest)
                if attempt.get('status')=='failed':info.update(ingestion_status='failed',error=attempt.get('error','Latest FSIS ingestion attempt failed; previous output is retained.'),blocked=True)
            return info
        path=root/'data/processed/evidence_manifest.json'
        if not path.exists():return {'ingestion_status':'legacy output; source manifest unavailable','recognition':'Legacy derived table; content schema is checked, but input snapshot identity has not been checked by the current manifest.'}
        saved=read_json(path)
        if not isinstance(saved,dict) or saved.get('schema_version')!=1 or not isinstance(saved.get('datasets'),dict):raise ValueError('Evidence source manifest has an unsupported schema')
        entry=saved['datasets'].get(source)
        if entry is None:return {'ingestion_status':'not in latest ingestion','recognition':'No input for this semantic source in the latest ingestion manifest.','blocked':True,'error':'Previous output may exist but is not represented by the latest input manifest.'}
        if not isinstance(entry,dict):raise ValueError('Evidence source manifest dataset entry has an unsupported schema')
        info={'ingestion_status':entry.get('status','unknown'),'source_key':entry.get('source_key'),
              'input_files':entry.get('input_files',[]),'output_sha256':entry.get('output_sha256'),
              'recognition':'Supported content signature assigns the semantic source; filenames/discovery order do not assign meaning.',
              'manifest_generated_at':saved.get('generated_at')}
        if entry.get('status')!='available':info.update(blocked=True,error=entry.get('error','Latest ingestion did not publish an available table.'))
        return info

    def validate_identity(source,columns):
        if source.startswith('beam_') and beam_identity(columns)!=source:raise ValueError('Stored BEAM schema does not match this semantic dataset identity')
        if source=='nors_0' and not NORS_COLUMNS<=set(columns):raise ValueError('Stored NORS schema does not match this semantic dataset identity')
        if source=='establishments_0' and not DIRECTORY_COLUMNS<=set(columns):raise ValueError('Stored establishment schema does not match this semantic dataset identity')

    def locate(source):
        if source not in SOURCES: raise HTTPException(404, 'Unknown supported dataset')
        try:
            info=provenance(source)
            if info.get('blocked'):raise HTTPException(503,info['error'])
        except HTTPException:raise
        except Exception as error:raise HTTPException(503,f'{type(error).__name__}: {error}') from error
        path=root/'data/processed'/f'{source}.parquet'
        if not path.exists(): raise HTTPException(404, 'Recognized dataset has not been ingested')
        return path,info

    def snapshot(path,info):
        # One bounded open supplies both checksum and parser input. An atomic
        # replacement between those operations cannot attach old provenance to
        # bytes from a different file. Large sources require a separate adapter.
        with path.open('rb') as stream:body=stream.read(MAX_DERIVED_BYTES+1)
        if len(body)>MAX_DERIVED_BYTES:raise ValueError('Derived table exceeds the 64 MiB explorer snapshot bound')
        digest=hashlib.sha256(body).hexdigest()
        if info.get('output_sha256') and digest!=info['output_sha256']:raise ValueError('Derived table checksum does not match its source manifest; re-ingest before browsing')
        return body,digest

    @router.get('/api/data/catalog')
    def catalog():
        output=[]
        for identity,(name,note) in SOURCES.items():
            path=root/'data/processed'/f'{identity}.parquet'
            item={'id':identity,'name':name,'note':note}
            try:
                info=provenance(identity);item.update({key:value for key,value in info.items() if key!='blocked'})
                if info.get('blocked'):
                    item.update(status=info['ingestion_status']);output.append(item);continue
                if not path.exists():
                    item.update(status='not ingested');output.append(item);continue
                body,digest=snapshot(path,info)
                metadata=pq.ParquetFile(pa.BufferReader(body))
                validate_identity(identity,metadata.schema_arrow.names)
                item.update(status='available',rows=metadata.metadata.num_rows,columns=[{'name':field.name,'type':str(field.type)} for field in metadata.schema_arrow],sha256=digest,
                            provenance='derived local table from source-specific ingestion; no live request',path=f'data/processed/{path.name}')
            except Exception as e:
                item.update(status='unreadable',error=f'{type(e).__name__}: {e}')
            output.append(item)
        return output

    @router.get('/api/data/{source}')
    def rows(source:str, limit:int=Query(default=25,ge=1,le=100),offset:int=Query(default=0,ge=0,le=10000),field:str|None=Query(default=None,max_length=100),contains:str|None=Query(default=None,min_length=1,max_length=100)):
        path,info=locate(source)
        try:
            body,digest=snapshot(path,info)
            dataset=ds.dataset(pq.read_table(pa.BufferReader(body)))
            validate_identity(source,dataset.schema.names)
            if (field is None)!=(contains is None):raise HTTPException(422,'Provide both field and contains to filter')
            if field is not None and field not in dataset.schema.names:raise HTTPException(422,'Filter column is not in this dataset schema')
            expression=None if field is None else pc.match_substring(ds.field(field).cast(pa.string()),contains,ignore_case=True)
            total=dataset.count_rows(filter=expression)
            chunks=[];skip=offset;remaining=limit
            for batch in dataset.scanner(filter=expression,batch_size=256).to_batches():
                if skip>=batch.num_rows:skip-=batch.num_rows;continue
                part=batch.slice(skip,min(remaining,batch.num_rows-skip));skip=0
                chunks.append(part);remaining-=part.num_rows
                if remaining==0:break
            table=pa.Table.from_batches(chunks,schema=dataset.schema)
            records=json.loads(table.to_pandas().to_json(orient='records',date_format='iso'))
            return {'source':source,'name':SOURCES[source][0],'note':SOURCES[source][1],'rows':records,'columns':dataset.schema.names,'offset':offset,'limit':limit,'returned_rows':len(records),'matching_rows':total,'has_more':offset+len(records)<total,'next_offset':offset+limit if offset+limit<=10000 and offset+limit<total else None,'filter':{'field':field,'contains':contains} if field else None,'page_null_counts':{name:table[name].null_count for name in table.column_names},
                    'snapshot_sha256':digest,'source_key':info.get('source_key'),'input_files':info.get('input_files',[]),'ingestion_status':info.get('ingestion_status'),'recognition':info.get('recognition'),
                    'provenance':'Read-only derived source table. Checksum and values use the same bounded immutable request snapshot. Null counts describe this page only. Values retain source formatting; dates have no invented publication timezone. Sources are never merged by this explorer.'}
        except HTTPException:raise
        except Exception as e:raise HTTPException(503,f'{type(e).__name__}: {e}') from e
    return router
