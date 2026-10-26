"""Read-only bounded browsing of explicitly recognized, separately ingested evidence."""
import hashlib
import json
from pathlib import Path
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq
from fastapi import APIRouter, HTTPException, Query

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


def create_data_router(root:Path):
    router=APIRouter(tags=['Read-only source data explorer'])

    def locate(source):
        if source not in SOURCES: raise HTTPException(404, 'Unknown supported dataset')
        path=root/'data/processed'/f'{source}.parquet'
        if not path.exists(): raise HTTPException(404, 'Recognized dataset has not been ingested')
        return path

    @router.get('/api/data/catalog')
    def catalog():
        output=[]
        for identity,(name,note) in SOURCES.items():
            path=root/'data/processed'/f'{identity}.parquet'
            if not path.exists():
                output.append({'id':identity,'name':name,'status':'not ingested','note':note});continue
            try:
                metadata=pq.ParquetFile(path)
                output.append({'id':identity,'name':name,'status':'available','note':note,'rows':metadata.metadata.num_rows,'columns':[{'name':field.name,'type':str(field.type)} for field in metadata.schema_arrow], 'sha256':hashlib.sha256(path.read_bytes()).hexdigest(), 'provenance':'derived local table from source-specific ingestion; no live request', 'path':f'data/processed/{path.name}'})
            except Exception as e:
                output.append({'id':identity,'name':name,'status':'unreadable','error':f'{type(e).__name__}: {e}','note':note})
        return output

    @router.get('/api/data/{source}')
    def rows(source:str, limit:int=Query(default=25,ge=1,le=100),offset:int=Query(default=0,ge=0,le=10000),field:str|None=Query(default=None,max_length=100),contains:str|None=Query(default=None,min_length=1,max_length=100)):
        path=locate(source)
        try:
            dataset=ds.dataset(path,format='parquet')
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
            return {'source':source,'name':SOURCES[source][0],'note':SOURCES[source][1],'rows':records,'columns':dataset.schema.names,'offset':offset,'limit':limit,'returned_rows':len(records),'matching_rows':total,'has_more':offset+len(records)<total,'next_offset':offset+limit if offset+limit<=10000 and offset+limit<total else None,'filter':{'field':field,'contains':contains} if field else None,'page_null_counts':{name:table[name].null_count for name in table.column_names},'provenance':'Read-only derived source table. Null counts describe this page only. Values retain source formatting; dates have no invented publication timezone. Sources are never merged by this explorer.'}
        except HTTPException:raise
        except Exception as e:raise HTTPException(503,f'{type(e).__name__}: {e}') from e
    return router
