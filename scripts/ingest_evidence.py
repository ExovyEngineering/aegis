"""Ingest separately recognized evidence exports; never assign identity by filename/order."""
import argparse
import sys
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.paths import ROOT,data_dir,write_json
from backend.ingestion.common import source_files,sha256_file,read_columns,exact_error,publish_parquet
from backend.ingestion.nors import NORSAdapter,NORS_COLUMNS
from backend.ingestion.beam import BEAMAdapter,beam_identity
from backend.ingestion.establishments import EstablishmentAdapter,DIRECTORY_COLUMNS

SEMANTIC_KEYS={
    'nors_0':'cdc_nors_outbreaks',
    'beam_0':'cdc_beam_regional_isolates',
    'beam_1':'cdc_beam_source_report',
    'beam_2':'cdc_beam_burden_trajectory',
    'beam_3':'cdc_beam_illnesses_outbreaks',
    'beam_4':'cdc_beam_common_serotypes',
    'establishments_0':'fsis_missouri_establishments',
}


def identify(columns):
    matches=[]
    if NORS_COLUMNS<=set(columns):matches.append(('nors_0','nors',NORSAdapter))
    beam=beam_identity(columns)
    if beam:matches.append((beam,'beam',BEAMAdapter))
    if DIRECTORY_COLUMNS<=set(columns):matches.append(('establishments_0','establishments',EstablishmentAdapter))
    if len(matches)>1:raise ValueError(f'Ambiguous source schema matches {[m[0] for m in matches]}')
    return matches[0] if matches else None


def ingest(folder=None,output_dir=None,report_path=None):
    folder=Path(folder or data_dir()).resolve()
    output_dir=Path(output_dir or ROOT/'data/processed').resolve()
    report_path=Path(report_path or ROOT/'reports/evidence_ingestion.json')
    reports=[];groups=defaultdict(list)
    for path in source_files(folder,{'.csv','.tsv'},excluded=(output_dir,report_path)):
        entry={'file':path.name,'path':str(path),'relative_path':path.relative_to(folder).as_posix()}
        reports.append(entry)
        try:
            entry['sha256']=sha256_file(path);entry['bytes']=path.stat().st_size
            columns=read_columns(path);entry['columns']=columns
            match=identify(columns)
            if match is None:
                entry.update(status='unrecognized',note='No supported content signature; not merged or ingested.');continue
            identity,source,adapter=match
            entry.update(dataset_id=identity,source=source,source_key=SEMANTIC_KEYS[identity],status='recognized')
            groups[identity].append((path,entry,adapter))
        except Exception as error:entry.update(status='failed',error=exact_error(error))
    datasets={}
    for identity,group in sorted(groups.items()):
        unique={entry['sha256'] for _,entry,_ in group}
        destination=output_dir/f'{identity}.parquet'
        dataset={'dataset_id':identity,'source_key':SEMANTIC_KEYS[identity],
                 'input_files':[{key:entry[key] for key in ('file','path','relative_path','sha256','bytes')} for _,entry,_ in group],
                 'output':str(destination)}
        datasets[identity]=dataset
        if len(unique)>1:
            message=f'{len(unique)} different exports match {SEMANTIC_KEYS[identity]}; select one explicit snapshot before ingestion. No files were pooled or chosen by filename.'
            dataset.update(status='conflict',error=message,previous_output_retained=destination.exists())
            for _,entry,_ in group:entry.update(status='conflict',error=message,output=str(destination),previous_output_retained=destination.exists())
            continue
        path,entry,adapter=group[0]
        try:
            frame=adapter().read(path)
            if list(frame.columns)!=entry['columns']:raise ValueError('Source header changed during ingestion')
            if sha256_file(path)!=entry['sha256']:raise ValueError('Source bytes changed during ingestion; no output published')
            output_dir.mkdir(parents=True,exist_ok=True)
            publish_parquet(frame,destination)
            dataset.update(status='available',rows=len(frame),columns=list(frame),output_sha256=sha256_file(destination))
            entry.update(status='ingested',rows=len(frame),output=str(destination),output_sha256=dataset['output_sha256'])
            if frame.attrs:entry['adapter_counts']=dict(frame.attrs);dataset['adapter_counts']=dict(frame.attrs)
            for _,duplicate,_ in group[1:]:
                duplicate.update(status='duplicate',duplicate_of=entry['relative_path'],rows=len(frame),output=str(destination),output_sha256=dataset['output_sha256'])
        except Exception as error:
            message=exact_error(error)
            dataset.update(status='failed',error=message,previous_output_retained=destination.exists())
            for _,entry,_ in group:entry.update(status='failed',error=message,output=str(destination),previous_output_retained=destination.exists())
    manifest={'schema_version':1,'generated_at':datetime.now(timezone.utc).isoformat(),'data_dir':str(folder),
              'identity_policy':'Content signatures assign stable semantic IDs. Different exports for one ID conflict; exact-byte duplicate downloads are not pooled.',
              'datasets':datasets,'files':reports,
              'limitations':['Recognition uses inspected schema signatures; it does not prove provider authenticity or completeness.',
                             'Unsupported workbooks/archives/JSON remain in the data audit and are not silently treated as CSV exports.',
                             'Different snapshots require explicit selection in a dedicated input folder; no vintage or recency is inferred from filenames.']}
    write_json(output_dir/'evidence_manifest.json',manifest);write_json(report_path,reports)
    return reports


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,default=data_dir())
    args=parser.parse_args();reports=ingest(args.data_dir)
    counts={status:sum(row['status']==status for row in reports) for status in sorted({row['status'] for row in reports})}
    print('Evidence ingestion:',counts)


if __name__=='__main__':main()
