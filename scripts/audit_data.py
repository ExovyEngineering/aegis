"""Read-only, streaming raw-data inventory. Missingness and ranges are sample-based."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse, csv, hashlib, json, zipfile, itertools
from collections import Counter
from datetime import datetime, timezone
from backend.paths import ROOT, data_dir, write_json

EXT = {'.csv','.tsv','.json','.jsonl','.xlsx','.zip','.parquet','.geojson','.pdf'}
SKIP = {'.venv','.tools','.aws','.codex','.agents','.vscode','artifacts','node_modules','.git','reports','manifests','cache','fixtures','external','dist','config','frontend','backend','processed'}
def classify(columns, metadata=''):
    c = {str(x).lower() for x in columns}; m = metadata.lower()
    if 'lab sampling' in m or {'form_id','sample_number'} <= c: return 'FSIS laboratory sampling'
    if {'establishment_id','latitude','longitude'} <= c: return 'FSIS establishment directory'
    if {'etiology','primary mode'} <= c: return 'CDC NORS'
    if any('serotype' in x or 'hhs' in x for x in c): return 'Possible CDC BEAM; requires metadata confirmation'
    if {'station','date'} <= c: return 'Possible NOAA observations; requires metadata confirmation'
    if any('lowaccess' in x or 'lapop' in x for x in c): return 'USDA food access atlas'
    return 'Unrecognized / documentation; do not merge'

def recognize_food_environment_workbook(sheets):
    """Recognize the inspected atlas from bounded content, never its filename.

    This is family identification, not full ingestion or validation of all rows.
    Only the first six sampled rows already retained by the audit are inspected.
    """
    by_name={sheet['name'].strip():sheet for sheet in sheets}
    if len(by_name)!=len(sheets) or not {'Read_Me','Variable List','ACCESS','STORES'}<=set(by_name):
        return None
    read_me=by_name['Read_Me'].get('first_rows',[])[:6]
    if not read_me or not read_me[0] or read_me[0][0]!='Food Environment Atlas data download':
        return None
    provider=next((str(row[0]) for row in read_me if row and row[0] and
                   'source: usda, economic research service' in str(row[0]).lower()),None)
    if not provider:
        return None
    variables=by_name['Variable List'].get('first_rows',[])[:6]
    expected=['Category Name','Category Code','Subcategory Name','Variable Name','Variable Code','Units']
    if len(variables)<3 or variables[1]!=expected:
        return None
    variable=next((row for row in variables[2:] if len(row)==6 and row[1]=='ACCESS' and
                   row[4]=='LACCESS_POP19' and row[5]=='Count' and isinstance(row[3],str) and
                   '2019' in row[3] and '*' not in row[3]),None)
    if variable is None:
        return None
    required={
        'ACCESS':{'FIPS','State','County','LACCESS_POP19','PCT_LACCESS_POP19','LACCESS_LOWI19'},
        'STORES':{'FIPS','State','County','GROC20','GROCPTH20','SNAPS23','SNAPSPTH23'},
    }
    for name,columns in required.items():
        first=by_name[name].get('first_rows',[])[:2]
        if len(first)<2 or not first[0] or first[0][0]!=name or not columns<=set(first[1]):
            return None
    return {'source':'USDA Food Environment Atlas',
            'method':'Bounded workbook content: embedded title/provider, Variable List code/units/vintage, ACCESS and STORES headers.',
            'sheets':[by_name[name]['name'] for name in ('Read_Me','Variable List','ACCESS','STORES')],
            'title':read_me[0][0],'provider_excerpt':provider,
            'variable_evidence':{'code':variable[4],'unit':variable[5],'label':variable[3]},
            'limitation':'Source-family recognition only; full row coverage, units, missing codes and geographic identity require the separate source-specific ingestion adapter.'}

def profile(rows):
    rows = list(itertools.islice(rows, 200)); keys = sorted({str(k) for r in rows for k in r})
    return {'sample_rows':len(rows),'schema':keys,'sample_missing':{k:sum(r.get(k) in (None,'') for r in rows) for k in keys},
      'sample_values':{k:list(dict.fromkeys(str(r[k]) for r in rows if r.get(k) not in (None,'')))[:5] for k in keys if any(t in k.lower() for t in ['date','year','state','county','establishment','pathogen','salmonella','product','time'])}}

def inspect_file(p):
    out={'filename':p.name,'path':str(p.resolve()),'size_bytes':None,'format':p.suffix.lower(),'errors':[]}
    try:
        out['size_bytes']=p.stat().st_size
        h=hashlib.sha256()
        with p.open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
        out['sha256']=h.hexdigest()
        ext=p.suffix.lower()
        if ext in {'.csv','.tsv'}:
            with p.open(encoding='utf-8-sig',newline='') as f:
                reader=csv.DictReader(f,delimiter='\t' if ext=='.tsv' else ','); sample=list(itertools.islice(reader,200)); out.update(profile(sample)); out['row_count']=len(sample)+sum(1 for _ in reader)
        elif ext in {'.json','.geojson'}:
            import ijson
            counts=Counter(); samples={}; metadata=[]; fields=Counter(); nulls=Counter(); ranges={}; declared={}
            with p.open('rb') as f:
                for prefix,event,value in ijson.parse(f):
                    if event=='start_map': counts[prefix]+=1
                    if event in {'string','number','boolean','null'}:
                        if '.metadata.data_records.' in prefix:declared[prefix.rsplit('.',1)[-1]]=value
                        if '.data.' in prefix:
                            fields[prefix]+=1
                            if value in (None,'','NULL'): nulls[prefix]+=1
                            if any(x in prefix.lower() for x in ['date','year']) and value not in (None,'','NULL'):
                                v=str(value); lo,hi=ranges.get(prefix,(v,v)); ranges[prefix]=(min(lo,v),max(hi,v))
                        if 'metadata' in prefix and len(metadata)<50: metadata.append(str(value)[:1000])
                        if 'metadata' not in prefix and len(samples)<200: samples.setdefault(prefix, str(value)[:200])
            out['object_counts_by_path']=dict(counts); out['sample_scalar_values']=samples; out['schema']=list(samples); out['metadata_excerpt']=metadata
            out['field_counts']=dict(fields); out['missing_counts']=dict(nulls); out['timestamp_ranges']=ranges
            out['declared_table_counts']=declared
            for table,expected in declared.items():
                actual_path=f'item.data.{table}_table_data.item'
                if actual_path in counts and int(expected)!=counts[actual_path]:out['errors'].append(f'Declared {table} rows {expected}, parsed {counts[actual_path]}: possible partial download or source metadata mismatch')
            out['row_count']=dict(counts)  # nested tables explicitly retained, never sum unrelated objects
        elif ext=='.jsonl':
            sample=[]; n=0
            with p.open(encoding='utf-8-sig') as f:
                for line in f:
                    if line.strip():
                        row=json.loads(line); n+=1
                        if len(sample)<200: sample.append(row)
            out.update(profile(sample)); out['row_count']=n
        elif ext=='.xlsx':
            import openpyxl
            wb=openpyxl.load_workbook(p,read_only=True,data_only=True); sheets=[]
            try:
                for ws in wb:
                    rows=ws.iter_rows(values_only=True); first=list(itertools.islice(rows,201)); sheets.append({'name':ws.title,'declared_rows':ws.max_row,'declared_columns':ws.max_column,'first_rows':[[str(v)[:200] if v is not None else None for v in r] for r in first[:6]]})
            finally:
                wb.close()
            out['sheets']=sheets; out['schema']=[str(v) for s in sheets for row in s['first_rows'][:2] for v in row if v]
            out['coverage_note']='Workbook dimensions are declared, not verified exact counts. First 201 rows sampled per sheet.'
        elif ext=='.zip':
            with zipfile.ZipFile(p) as z: out['members']=[{'name':i.filename,'compressed':i.compress_size,'uncompressed':i.file_size} for i in z.infolist()]
            out['coverage_note']='Central directory inspected; no extraction or full CRC validation.'
        elif ext=='.parquet':
            import pyarrow.parquet as pq
            q=pq.ParquetFile(p); out['row_count']=q.metadata.num_rows; out['schema']=q.schema.names
        elif ext=='.pdf':
            from pypdf import PdfReader
            q=PdfReader(p); out['pages']=len(q.pages); out['text_sample']='\n'.join(x.extract_text() or '' for x in q.pages[:3])[:12000]
        out['likely_source']=classify(out.get('schema',[]),str(out.get('metadata_excerpt',''))+' '+out.get('text_sample',''))
        recognized=recognize_food_environment_workbook(out.get('sheets',[]))
        if recognized:
            out['likely_source']=recognized['source']; out['source_recognition']=recognized
    except Exception as e: out['errors'].append(f'{type(e).__name__}: {e}')
    return out

def main():
    a=argparse.ArgumentParser(); a.add_argument('--data-dir',type=Path,default=data_dir()); args=a.parse_args()
    if not args.data_dir.is_dir(): a.error(f'Data directory does not exist: {args.data_dir}')
    files=[]; seen={}
    for p in sorted(args.data_dir.rglob('*')):
        if p.is_file() and p.suffix.lower() in EXT and not any(x in SKIP for x in p.relative_to(args.data_dir).parts):
            print('Audit',p.name,flush=True); item=inspect_file(p); item['duplicate_of']=seen.get(item.get('sha256'))
            if item.get('sha256'): seen[item['sha256']]=str(p)
            files.append(item)
    report={'retrieved_at':datetime.now(timezone.utc).isoformat(),'data_dir':str(args.data_dir.resolve()),'sampling_policy':'200 records; workbook 201 rows/sheet; JSON fully streamed for syntax and object counts. Missingness only for sampled CSV/JSONL records.','files':files}
    write_json(ROOT/'data/manifests/inventory.json',report)
    lines=['# Raw data audit',report['retrieved_at'],'',report['sampling_policy'],'','| File | Bytes | Source | Errors |','|---|---:|---|---|']
    for f in files: lines.append(f"| {f['filename']} | {f['size_bytes']} | {f.get('likely_source','unknown')} | {'; '.join(f['errors'])} |")
    lines+=['','Full schemas, samples, nested table counts, duplicate hashes and exact errors: `data/manifests/inventory.json`.','No raw files modified. XLSX formula values use saved workbook caches. Schema recognition is conservative; unknown sources remain separate.']
    lines+=['',f"Files: {len(files)}. Exact duplicate hashes: {sum(bool(f.get('duplicate_of')) for f in files)}. Files with recorded errors: {sum(bool(f['errors']) for f in files)}.",'','## Coverage and schemas']
    for f in files:
        lines+=['',f"### {f['filename']}",f"- Source: {f.get('likely_source','unrecognized')}. Path: `{f['path']}`."]
        if f.get('object_counts_by_path'):
            counts={k:v for k,v in f['object_counts_by_path'].items() if '.data.' in k and k.endswith('.item')}
            lines.append('- Stream-verified nested table rows: `'+json.dumps(counts)+'`.')
        elif isinstance(f.get('row_count'),int):lines.append(f"- Exact parsed row count: {f['row_count']}.")
        if f.get('sheets'):lines.append('- Workbook sheets (declared dimensions): '+', '.join(f"{s['name']} ({s['declared_rows']} rows x {s['declared_columns']} columns)" for s in f['sheets'])+'.')
        if f.get('timestamp_ranges'):lines.append('- Observed date ranges: `'+json.dumps(f['timestamp_ranges'])+'`.')
        critical=[k for k in f.get('schema',[]) if any(t in k.lower() for t in ['date','year','month','state','region','county','establishment','pathogen','salmonella','etiology','product','latitude','longitude'])]
        if critical:lines.append('- Geographic, time, identifier and outcome fields: `'+ '`, `'.join(critical[:35])+'`.')
        if f.get('missing_counts'):lines.append('- Explicit JSON null/empty/NULL counts (top 10): `'+json.dumps(dict(sorted(f['missing_counts'].items(),key=lambda x:x[1],reverse=True)[:10]))+'`. Other sentinel meanings are not reinterpreted.')
        if f.get('coverage_note'):lines.append('- '+f['coverage_note'])
        if f['errors']:lines.append('- Exact errors: '+'; '.join(f['errors']))
    (ROOT/'reports').mkdir(exist_ok=True); (ROOT/'reports/data_audit.md').write_text('\n'.join(lines),encoding='utf-8')
if __name__=='__main__': main()
