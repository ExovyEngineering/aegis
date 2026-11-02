"""Verify our own reviewer ZIP and run its extracted app offline in isolation.

Use archives built by scripts/package_submission.py from trusted project code.
Hashes establish internal integrity, not publisher authenticity. The worker reuses
installed dependencies; this is not a fresh Python environment or a security
sandbox for executing an untrusted application's code.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import re
import socket
import stat
import subprocess
import sys
import tempfile
from threading import local
import time
import traceback
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[1]
MAX_ARCHIVE_BYTES=100*1024*1024
MAX_MANIFEST_BYTES=2*1024*1024
FORBIDDEN_PARTS={'.git','.aws','.codex','.agents','.tools','.venv','node_modules','__pycache__'}
WINDOWS_RESERVED={'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}


def digest_file(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda:stream.read(1024*1024),b''):digest.update(part)
    return digest.hexdigest()


def safe_member(name):
    if not isinstance(name,str) or not name or '\\' in name or '\x00' in name or ':' in name:
        raise ValueError(f'Unsafe archive path: {name!r}')
    parts=name.split('/')
    if PurePosixPath(name).is_absolute() or any(part in {'','.', '..'} for part in parts):
        raise ValueError(f'Unsafe archive path: {name!r}')
    if any(part.endswith((' ','.')) or part.split('.')[0].upper() in WINDOWS_RESERVED for part in parts):
        raise ValueError(f'Nonportable archive path: {name!r}')
    if any(part.casefold() in FORBIDDEN_PARTS or part.casefold().startswith('.env') and part!='.env.example' for part in parts):
        raise ValueError(f'Forbidden credential/runtime archive path: {name}')
    lower=name.casefold()
    if lower.startswith(('data/backups/','data/recovered/')):
        raise ValueError(f'Forbidden private backup/recovery archive path: {name}')
    if lower.endswith(('.pem','.key','.sqlite','.sqlite3','.db','.exe','.dll')) or re.search(r'\.(?:sqlite3?|db)-[^/]+$',lower):
        raise ValueError(f'Forbidden credential/database/runtime archive path: {name}')
    return name


def validate_and_extract(archive,target):
    """Verify every member before writing; manually extract regular files only."""
    archive,target=Path(archive),Path(target).resolve()
    if not target.is_dir() or any(target.iterdir()):raise ValueError('Extraction target must be an existing empty isolated directory')
    with zipfile.ZipFile(archive) as zipped:
        infos=zipped.infolist()
        if not infos or len(infos)>10000:raise ValueError('Archive member count is empty or exceeds 10,000')
        if sum(info.file_size for info in infos)>MAX_ARCHIVE_BYTES:raise ValueError('Archive exceeds the 100 MiB uncompressed bound')
        names={};folded=set()
        for info in infos:
            name=safe_member(info.filename)
            if name.casefold() in folded:raise ValueError(f'Duplicate/case-colliding archive path: {name}')
            folded.add(name.casefold());names[name]=info
            mode=info.external_attr>>16
            if stat.S_IFMT(mode) not in (0,stat.S_IFREG):raise ValueError(f'Symlink or special archive member rejected: {name}')
            if info.is_dir():raise ValueError(f'Directory entries are unsupported; reviewer packages contain files only: {name}')
            if info.flag_bits&1:raise ValueError(f'Encrypted archive member rejected: {name}')
        if 'PACKAGE_MANIFEST.json' not in names:raise ValueError('Archive is missing PACKAGE_MANIFEST.json')
        if names['PACKAGE_MANIFEST.json'].file_size>MAX_MANIFEST_BYTES:raise ValueError('Package manifest exceeds the 2 MiB bound')
        manifest=json.loads(zipped.read('PACKAGE_MANIFEST.json'))
        if not isinstance(manifest,dict) or manifest.get('draft') is not True or not isinstance(manifest.get('files'),list):
            raise ValueError('Unsupported package manifest schema; expected a draft with files array')
        entries={}
        for entry in manifest['files']:
            if not isinstance(entry,dict):raise ValueError('Package manifest file entry is not an object')
            name=safe_member(entry.get('path'))
            if name=='PACKAGE_MANIFEST.json' or name in entries:raise ValueError(f'Duplicate/self-referencing manifest path: {name}')
            if type(entry.get('bytes')) is not int or entry['bytes']<0:raise ValueError(f'Invalid manifest byte count: {name}')
            if not isinstance(entry.get('sha256'),str) or not re.fullmatch(r'[0-9a-f]{64}',entry['sha256']):raise ValueError(f'Invalid manifest checksum: {name}')
            entries[name]=entry
        if not entries or set(names)!=(set(entries)|{'PACKAGE_MANIFEST.json'}):raise ValueError('Manifest membership does not exactly match archive files')
        for name,entry in entries.items():
            if names[name].file_size!=entry['bytes']:raise ValueError(f'Package byte-count mismatch: {name}')
            body=zipped.read(name)
            if len(body)!=entry['bytes'] or hashlib.sha256(body).hexdigest()!=entry['sha256']:raise ValueError(f'Package checksum/size mismatch: {name}')
        # The archive is our trusted code; integrity and path checks are complete.
        # Recheck the exact bytes copied to defend against an interrupted archive.
        for name in sorted(names):
            body=zipped.read(name)
            if name in entries and hashlib.sha256(body).hexdigest()!=entries[name]['sha256']:raise ValueError(f'Archive changed before extraction: {name}')
            destination=(target/name).resolve()
            if not destination.is_relative_to(target):raise ValueError(f'Extraction path escapes target: {name}')
            destination.parent.mkdir(parents=True,exist_ok=True)
            with destination.open('xb') as stream:stream.write(body)
    return {'manifest_files_verified':len(entries),'archive_files':len(names),'uncompressed_bytes':sum(info.file_size for info in infos)}


@contextmanager
def no_network():
    """Reject Internet socket connects, UDP sends and DNS in the offline worker."""
    attempts=[]
    connect=socket.socket.connect;connect_ex=socket.socket.connect_ex;sendto=socket.socket.sendto;socketpair=socket.socketpair
    context=local()
    def deny(operation,address):
        attempts.append({'operation':operation,'address':str(address)})
        raise RuntimeError(f'Package verification has networking disabled: {operation}')
    def guarded_connect(connection,address):
        # Python's Windows asyncio self-pipe uses socketpair's own loopback
        # connection. Permit only that construction, in its calling thread.
        internal_pair=getattr(context,'socketpair',False) and isinstance(address,tuple) and address[0] in ('127.0.0.1','::1')
        if connection.family in (socket.AF_INET,socket.AF_INET6) and not internal_pair:return deny('socket.connect',address)
        return connect(connection,address)
    def guarded_socketpair(*args,**kwargs):
        previous=getattr(context,'socketpair',False);context.socketpair=True
        try:return socketpair(*args,**kwargs)
        finally:context.socketpair=previous
    def guarded_connect_ex(connection,address):
        if connection.family in (socket.AF_INET,socket.AF_INET6):return deny('socket.connect_ex',address)
        return connect_ex(connection,address)
    def guarded_sendto(connection,*args):
        if connection.family in (socket.AF_INET,socket.AF_INET6):return deny('socket.sendto',args[-1] if args else '')
        return sendto(connection,*args)
    with patch.object(socket.socket,'connect',guarded_connect),patch.object(socket.socket,'connect_ex',guarded_connect_ex),patch.object(socket.socket,'sendto',guarded_sendto),patch.object(socket,'socketpair',guarded_socketpair),patch.object(socket,'getaddrinfo',lambda *args,**kwargs:deny('DNS',args[0] if args else '')),patch.object(socket,'create_connection',lambda address,*args,**kwargs:deny('socket.create_connection',address)):
        yield attempts


def _assert(condition,message):
    if not condition:raise AssertionError(message)


def run_extracted_workflows(target):
    """Called only in the fresh subprocess, after its cwd/import path isolation."""
    target=Path(target).resolve()
    _assert(Path.cwd().resolve()==target,'Worker cwd is not the extracted archive')
    sys.path[:]=[str(target),*[entry for entry in sys.path if entry and Path(entry).resolve()!=ROOT.resolve() and Path(entry).resolve()!=target]]
    os.environ['AEGIS_DB_PATH']=str(target/'data/reviewer-verification.sqlite')
    checks=[];attempts=[]
    result={'status':'failed','passed':False,'checks':checks,'network_requested':False,'network_guard_enabled':True,'isolated_extracted_directory':True,'fresh_python_environment':False}
    try:
        with no_network() as attempts:
            from fastapi.testclient import TestClient
            import backend
            import backend.main as api
            from backend.paths import ROOT as imported_root
            _assert(Path(backend.__file__).resolve().is_relative_to(target),'Backend import escaped extracted archive')
            _assert(imported_root.resolve()==target and api.DB.resolve().is_relative_to(target),'Extracted source or database isolation failed')
            _assert(not api.DB.exists(),'Reviewer database was not fresh before application startup')
            checks.append('extracted backend imports and fresh database are isolated from checkout')
            with TestClient(api.app) as client:
                page=client.get('/')
                _assert(page.status_code==200 and 'AEGIS' in page.text,'Prebuilt frontend does not load')
                assets=re.findall(r'(?:src|href)="(/assets/[^\"]+)"',page.text)
                _assert(bool(assets),'Prebuilt frontend has no bundled assets')
                for asset in assets:_assert(client.get(asset).status_code==200,f'Bundled frontend asset unavailable: {asset}')
                checks.append('prebuilt frontend and bundled assets load')
                if (target/'scripts/start_local.py').exists():
                    from scripts.start_local import frontend_assets
                    _assert((target/'Start-AEGIS.cmd').is_file(),'Windows local launcher missing from reviewer package')
                    _assert(frontend_assets(target)['local_asset_count']>0,'Packaged launcher could not validate prebuilt assets without Node')
                    checks.append('packaged foreground launcher and prebuilt assets validate without building or downloading dependencies')
                for source in ('fsis_recalls','modot','openmeteo'):
                    response=client.get('/api/evidence/'+source,params={'limit':2} if source=='fsis_recalls' else {})
                    _assert(response.status_code==200,f'Packaged source evidence unavailable: {source}')
                    evidence=response.json()
                    _assert(evidence.get('fixture') is True and evidence.get('live') is False and bool(evidence.get('retrieved_at')),f'{source} is not a clearly dated fixture')
                    checks.append(source+' dated fixture works without network/cache')
                for source in ('network','model','model-timing','noaa-coverage','facilities','inventory'):
                    _assert(client.get('/api/'+source).status_code==200,f'Required read endpoint failed: {source}')
                checks.append('network, measured model and source coverage reports are available')
                assistant=client.get('/api/assistant/context')
                _assert(assistant.status_code==200,'Read-only assistant context unavailable')
                captured_assistant=assistant.json()
                explained=client.post('/api/assistant/ask',json={'question_id':'model_limits','expected_snapshot_id':captured_assistant['snapshot_id']})
                _assert(explained.status_code==200 and explained.json()['engine']['llm_used'] is False and all(fact in captured_assistant['facts'] for fact in explained.json()['answer']['items']),'Assistant invented a fact or failed its deterministic grounding contract')
                checks.append('read-only assistant explains exact captured facts without a provider or model call')
                before_outlook=digest_file(api.DB)
                friendly=client.post('/api/assistant/interpret',json={'prompt':'chicken','expected_snapshot_id':captured_assistant['snapshot_id']})
                _assert(friendly.status_code==200,'Broad poultry question did not produce guidance')
                choices=friendly.json()
                _assert(choices.get('kind')=='clarification' and choices.get('operational_state_modified') is False and choices['interpretation']['llm_routing_used'] is False and set(choices['clarification']['question_ids']).issubset({question['id'] for question in captured_assistant['questions']}) and choices['clarification']['question_ids'],'Broad poultry question invented an answer or failed canonical guidance')
                checks.append('broad chicken question returns canonical read-only assistant choices without a model call')
                impact_network=client.get('/api/network').json()
                for delay in (0,60):
                    outlook=client.post('/api/delivery-outlook',json={'expected_network_revision':impact_network['revision'],'added_delay_minutes':delay,'ambient_temperature_c':30,'fault_truck_id':None})
                    _assert(outlook.status_code==200,'Packaged delivery outlook failed')
                    projection=outlook.json()
                    _assert(projection.get('read_only') is True and projection.get('simulation') is True and projection.get('operational_state_modified') is False and projection.get('planning_horizon_hours')==6 and projection['parameters']=={'added_delay_minutes':delay,'ambient_temperature_c':30,'fault_truck_id':None},'Delivery outlook lost captured planning assumptions')
                    _assert(projection['provenance']['model_kind']=='deterministic planning projection' and projection['provenance'].get('weather_input') and projection['provenance'].get('cargo_input'),'Delivery outlook lost simulation provenance')
                    _assert([row['scenario'] for row in projection['scenarios']]==list('ABCD') and all(row['summary']['feasible'] and row['summary']['constraint_violations']==0 and row['summary']['constraint_review_passed'] for row in projection['scenarios']),'Delivery outlook did not independently check four actual allocations')
                _assert(client.post('/api/delivery-outlook',json={'expected_network_revision':impact_network['revision']+1}).status_code==409,'Stale outlook revision was accepted')
                _assert(client.get('/api/network').json()==impact_network and digest_file(api.DB)==before_outlook,'Read-only guidance or delivery outlook changed packaged operational state')
                checks.append('read-only delivery outlook compares current and delayed allocations with simulation provenance and independent constraints')
                impact=client.post('/api/events/preview',json={'event':'road_closure','shipment_id':impact_network['shipments'][0]['id'],'expected_network_revision':impact_network['revision']})
                _assert(impact.status_code==200 and impact.json()['read_only'] is True and impact.json()['operational_state_modified'] is False and len(impact.json()['scenarios'])==4 and impact.json()['route_effects']['geometry_changed'] is False,'Read-only event comparison failed its simulation or route scope')
                _assert(client.get('/api/network').json()==impact_network,'Event preview changed the packaged network')
                checks.append('read-only disruption preview computes four real before/after allocations without changing network or route geometry')
                roads=client.get('/api/road-intelligence')
                _assert(roads.status_code==200,'Packaged road workspace unavailable')
                captured=roads.json();road_sources={source['id']:source for source in captured.get('sources',[])}
                _assert(set(road_sources)=={'modot','iowa_dot'} and all(source.get('available') and source.get('fixture') and source.get('stale') for source in road_sources.values()),'Separate dated road fixtures or stale labels missing')
                road_comparison=client.post('/api/road-intelligence/compare',json={'origin':[-92.3341,38.9517],'destination':[-93.625,41.5868],'routing':'estimated','buffer_m':250})
                _assert(road_comparison.status_code==200,'Packaged offline road comparison failed')
                comparison=road_comparison.json()
                _assert(comparison.get('operational_state_modified') is False and comparison.get('alternatives') and all(row.get('fallback') and row.get('review_required') and len(row.get('reviews',[]))==2 for row in comparison['alternatives']),'Road comparison changed state or lost estimate/review/source boundaries')
                checks.append('separate dated Iowa/Missouri road fixtures and estimated comparison work without network')
                catalog_response=client.get('/api/data/catalog')
                _assert(catalog_response.status_code==200,'Source catalog unavailable')
                catalog={entry['id']:entry for entry in catalog_response.json()}
                semantic={'fsis_poultry':'fsis_raw_poultry_primary','nors_0':'cdc_nors_outbreaks','beam_0':'cdc_beam_regional_isolates','beam_1':'cdc_beam_source_report','beam_2':'cdc_beam_burden_trajectory','beam_3':'cdc_beam_illnesses_outbreaks','beam_4':'cdc_beam_common_serotypes','establishments_0':'fsis_missouri_establishments'}
                for identity,key in semantic.items():
                    entry=catalog.get(identity,{})
                    _assert(entry.get('status')=='available' and entry.get('source_key')==key and bool(entry.get('input_files')),f'Semantic source provenance unavailable: {identity}')
                    response=client.get('/api/data/'+identity,params={'limit':2})
                    _assert(response.status_code==200,f'Bounded source browsing failed: {identity}')
                    rows=response.json()
                    _assert(rows.get('snapshot_sha256')==entry.get('sha256') and rows.get('source_key')==key and 0<len(rows.get('rows',[]))<=2,f'Source-row identity/hash mismatch: {identity}')
                checks.append('all eight semantic source tables browse with matching snapshot checksums')
                context=client.get('/api/food-access')
                _assert(context.status_code==200,'USDA historical county context unavailable')
                county=context.json();records=county.get('records',[])
                _assert(county.get('integrity_verified') is True and len(records)==county.get('geography',{}).get('county_count')==115,'USDA county coverage/integrity mismatch')
                codes=[row.get('FIPS') for row in records]
                _assert(len(set(codes))==115 and all(isinstance(code,str) and re.fullmatch(r'29\d{3}',code) for code in codes) and '29510' in codes,'USDA Missouri FIPS or St. Louis city missing')
                exported=client.get('/api/food-access.csv')
                _assert(exported.status_code==200 and 'source_sha256' in exported.text,'USDA context export unavailable')
                checks.append('historical USDA context retains 115 Missouri county units, FIPS and export provenance')
                _assert(client.get('/api/driver').json()==[],'Fresh reviewer database already contains assignments')
                _assert(client.get('/api/readiness').json().get('summary',{}).get('total_assignments')==0,'Empty readiness view invents assignments')
                plan_response=client.post('/api/route-lab',json={'preset':'farm','routing':'estimated'})
                _assert(plan_response.status_code==200,'Offline route laboratory failed')
                plan=plan_response.json()
                _assert(plan.get('routes') and plan.get('matrix_fallback') is True and plan['summary']['constraint_violations']==0,'Offline estimated farm routing failed constraints/provenance')
                checks.append('offline farm route plan is feasible with explicitly estimated routing')
                saved=client.post('/api/planning/projects',json={'name':'Reviewer package experiment','run_id':plan['run_id']})
                _assert(saved.status_code==200,'Planning project save failed')
                reopened=client.get('/api/planning/projects/'+saved.json()['id'])
                _assert(reopened.status_code==200 and reopened.json()['run']['result']['run_id']==plan['run_id'],'Saved project did not reopen its exact run')
                checks.append('saved route project reopens its immutable planning run')
                pdf=client.get('/api/project-brief.pdf')
                _assert(pdf.status_code==200 and pdf.content.startswith(b'%PDF'),'Presentation PDF absent or invalid')
                checks.append('presentation PDF is included and downloadable')
                if (target/'reports/master_guide_manifest.json').exists():
                    handbook=json.loads((target/'reports/master_guide_manifest.json').read_text(encoding='utf-8'))
                    downloaded=client.get('/api/master-guide.pdf')
                    _assert(downloaded.status_code==200 and downloaded.content.startswith(b'%PDF') and hashlib.sha256(downloaded.content).hexdigest()==handbook['sha256'],'Master user guide PDF/hash missing')
                    _assert(client.get('/api/master-guide.html').status_code==200 and client.get('/api/master-guide.md').status_code==200,'Master guide reading/Markdown formats missing')
                    checks.append('complete master user handbook downloads in PDF, print HTML and Markdown with recorded checksum')
                if (target/'backend/challenge.py').exists():
                    tasks=client.get('/api/challenge')
                    _assert(tasks.status_code==200 and len(tasks.json().get('tasks',[]))==5,'Five-task handoff missing')
                    _assert('not used' in tasks.json()['tasks'][3]['status'].lower() and 'not met' in tasks.json()['tasks'][3]['status'].lower(),'Kiro non-use was not disclosed')
                    final_guide=json.loads((target/'reports/final_handoff_manifest.json').read_text(encoding='utf-8'))
                    final_pdf=client.get('/api/challenge/artifacts/guide.pdf')
                    _assert(final_pdf.status_code==200 and hashlib.sha256(final_pdf.content).hexdigest()==final_guide['sha256'],'Final five-task PDF/hash mismatch')
                    _assert(client.get('/api/challenge/artifacts/guide.html').status_code==200,'Final guide HTML unavailable')
                    checks.append('five challenge tasks and final guide export disclose Kiro non-use and remaining team review')
                    integrated=client.get('/api/challenge/integrated-model')
                    _assert(integrated.status_code==200,'Integrated research results unavailable')
                    study=integrated.json();cohort=study['primary_split']['validation_rows']
                    _assert(study['operational_activation_allowed'] is False and cohort>0 and all(row['metrics']['n']==cohort for row in study['models'].values()),'Integrated study lost common cohort or research-only gate')
                    _assert(client.get('/api/challenge/artifacts/analytic-data.csv').status_code==200 and client.get('/api/challenge/artifacts/dictionary.csv').status_code==200,'Analytic data/dictionary missing')
                    checks.append('integrated FSIS BEAM NOAA research and ablation metrics retain common cohort and no operational activation')
                    policies=client.get('/api/challenge/decision-study')
                    _assert(policies.status_code==200,'Food-security policy study unavailable')
                    policy_data=policies.json()
                    _assert(policy_data['simulation'] is True and policy_data['requires_human_approval'] is True and len(policy_data['scenarios'])>=3,'Policy provenance/scenarios missing')
                    _assert(all(len(scene['policies'])>=3 and all(row['constraint_review']['passed'] and type(row['metrics']['held_or_recalled_dispatched_kg']) in (int,float) and row['metrics']['held_or_recalled_dispatched_kg']==0 for row in scene['policies']) for scene in policy_data['scenarios']),'Policy safety exclusions/independent checks failed')
                    _assert(client.get('/api/driver').json()==[],'Reading challenge evidence dispatched assignments')
                    checks.append('three food-volume and balanced-service scenarios compare safe eligible policies without dispatch')
                proposal=client.post('/api/proposals/A')
                _assert(proposal.status_code==200,'Scenario proposal unavailable')
                approval='/api/proposals/'+proposal.json()['id']+'/approve'
                _assert(client.post(approval,json={'actor':'  ','reason':'     '}).status_code==422,'Blank approval identity was accepted')
                _assert(client.post(approval,json={'actor':'Package verifier','reason':'Isolated trusted reviewer archive workflow'}).status_code==200,'Explicit human approval failed')
                assignments=client.get('/api/driver').json()
                _assert(bool(assignments),'Approval did not create simulated driver assignments')
                checks.append('human approval publishes simulated assignments in the fresh extracted database')
                history_network=client.get('/api/network').json()
                history=client.get('/api/activity',params={'action':'approve','limit':25})
                _assert(history.status_code==200 and history.json()['read_only'] is True and history.json()['operational_state_modified'] is False and history.json()['total_matching']>=1 and all(row['action']=='approve' for row in history.json()['records']),'Recorded approval activity unavailable or falsely classified')
                _assert(client.get('/api/network').json()==history_network,'Activity inspection changed the packaged network')
                checks.append('read-only activity history exposes the actual recorded approval without changing state')
                assignment=assignments[0];sid=assignment['id'];truck=assignment['truck_id']
                _assert(client.post('/api/driver/'+sid+'/acknowledge').status_code==423,'Drive acknowledgment was not initially locked')
                drive=client.get('/api/drive/'+truck).json()
                _assert(drive.get('focus',{}).get('interaction_allowed') is False,'Fresh Drive focus was not locked')
                parked=client.post('/api/drive/'+truck+'/focus',json={'mode':'parked','parked_confirmation':True,'expected_version':drive['focus']['version']})
                _assert(parked.status_code==200,'Explicit parked confirmation failed')
                _assert(client.post('/api/driver/'+sid+'/acknowledge',json={'expected_network_revision':drive['network_revision']}).status_code==200,'Parked contextual acknowledgment failed')
                checks.append('Drive default lock and parked confirmation gate contextual trip acknowledgment')
                before=digest_file(api.DB)
                readiness=client.get('/api/readiness')
                _assert(readiness.status_code==200,'Approved readiness view failed')
                evaluated=next((row for row in readiness.json().get('assignments',[]) if row['shipment_id']==sid),{})
                _assert(evaluated.get('status')=='ready_for_review' and not evaluated.get('blockers'),'Acknowledged valid assignment did not become ready for human review')
                _assert(digest_file(api.DB)==before,'Readiness changed the extracted operational database')
                checks.append('read-only readiness distinguishes approved acknowledged work without dispatching')
                frozen=json.loads((target/'data/fixtures/osrm_route.json').read_text(encoding='utf-8'))
                with patch.object(api.OSRMRoutingAdapter,'route',lambda *args,**kwargs:frozen):
                    routed=client.post('/api/route',json={'coordinates':[[-92.3341,38.9517],[-90.1994,38.6270]]})
                _assert(routed.status_code==200 and routed.json().get('road_review',{}).get('modot_retrieved_at'),'Route review did not use the dated packaged MoDOT fixture')
                checks.append('route review uses a supplied OSRM fixture and dated MoDOT evidence offline')
                from scripts.backup_state import create_backup, verify_backup, restore_backup
                backed=create_backup(api.DB,'data/backups/reviewer-check',root=target)
                verified=verify_backup(backed['backup_directory'],root=target)
                restored=restore_backup(backed['backup_directory'],'data/recovered/reviewer-check.sqlite',root=target)
                _assert(verified['status']=='verified' and restored['status']=='restored_to_new_copy' and not restored['operator_database_overwritten'] and not restored['server_started'],'Packaged local recovery verification failed')
                checks.append('local SQLite backup verifies and restores to a new private copy without rebinding the app')
                quality_network=client.get('/api/network').json()
                quality_context=client.get('/api/freshness/context')
                _assert(quality_context.status_code==200,'Packaged freshness workspace unavailable')
                candidate=quality_context.json()['demo_shipment_id']
                session=client.post('/api/freshness/sessions',json={'expected_network_revision':quality_network['revision'],'shipment_id':candidate,'scenario':'poultry_demo'})
                _assert(session.status_code==200,'Packaged sensor replay creation failed')
                baseline_quality=session.json()
                heated=client.post('/api/freshness/sessions/'+baseline_quality['id']+'/replay',json={'expected_version':baseline_quality['version'],'event':'heat_excursion'})
                _assert(heated.status_code==200,'Packaged temperature replay failed')
                capture=heated.json();rescue=capture['rescue']
                _assert(capture['freshness']['remaining_reference_hours']<baseline_quality['freshness']['remaining_reference_hours'] and 0<capture['freshness']['remaining_quality_hours']<capture['freshness']['remaining_hours_at_forecast_temperature'],'Quality point/sensitivity clocks or irreversible exposure calculation failed')
                _assert(rescue['triggered'] and rescue['proposal_hash'] and rescue['plan_summary']['constraint_violations']==0 and all(capture['fefo'][policy]['constraint_review']['passed'] for policy in ('fifo','fefo')),'Automatic rescue or independently checked FEFO/FIFO computation failed')
                _assert(client.get('/api/network').json()==quality_network,'A sensor experiment changed operational state before approval')
                checks.append('stored sensor replay drives conditional quality clocks, automatic rescue and independently reviewed FEFO/FIFO')
                approval_body={'expected_version':capture['version'],'expected_network_revision':capture['network_revision'],'proposal_hash':rescue['proposal_hash'],'destination_id':rescue['proposed_destination_id'],
                    'actor':'Offline reviewer dispatcher','reason':'Explicit isolated quality, receiving and route review for the packaged rescue demonstration',
                    'quality_review_confirmed':True,'recipient_confirmed':True,'routing_review_confirmed':True}
                _assert(client.post('/api/freshness/sessions/'+capture['id']+'/approve',json={**approval_body,'quality_review_confirmed':False}).status_code==422,'Missing food-safety/quality review confirmation was accepted')
                approved=client.post('/api/freshness/sessions/'+capture['id']+'/approve',json=approval_body)
                _assert(approved.status_code==200,'Packaged identified rescue approval failed')
                result_snapshot=approved.json()['snapshot'];published=client.get('/api/driver').json()
                saved_trip=next(row for row in published if row['id']==candidate)
                _assert(saved_trip['destination']==rescue['proposed_destination_id'] and saved_trip.get('freshness_rescue',{}).get('session_id')==capture['id'],'Approved rescue did not update the actual simulated driver assignment')
                checks.append('identified rescue approval requires all review confirmations and updates the exact simulated driver trip')
                further=client.post('/api/freshness/sessions/'+capture['id']+'/replay',json={'expected_version':result_snapshot['version'],'event':'normal'})
                _assert(further.status_code==200 and further.json()['status']=='review_required','New readings did not require renewed review')
                driver_review=client.get('/api/drive/'+saved_trip['truck_id']).json()
                _assert(driver_review.get('freshness_reviews') and client.get('/api/driver').json()==published,'New telemetry silently changed assignments or omitted the driver review advisory')
                checks.append('later sensor frames raise a persistent freshness review without automatic holds or redispatch')
            _assert(not attempts,'Application attempted network access during offline verification')
            checks.append('socket and DNS guard observed zero application network attempts')
        result.update(status='passed',passed=True)
    except Exception as error:
        result.update(error=f'{type(error).__name__}: {error}',traceback=traceback.format_exc())
    result.update(network_requested=bool(attempts),network_attempts=attempts,
                  check_results=[{'name':name,'status':'passed'} for name in checks])
    if not result['passed']:result['check_results'].append({'name':'offline extracted application workflow','status':'failed','detail':result.get('error')})
    return result


def _run_worker(target,result_path):
    environment={key:value for key,value in os.environ.items() if not key.startswith('AEGIS_') and key not in {'PYTHONPATH','PYTHONHOME'}}
    environment.update(AEGIS_DB_PATH=str(target/'data/reviewer-verification.sqlite'),PYTHONDONTWRITEBYTECODE='1')
    command=[sys.executable,'-I',str(Path(__file__).resolve()),'--worker',str(target),'--worker-result',str(result_path)]
    completed=subprocess.run(command,cwd=target,env=environment,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',timeout=180)
    if not result_path.exists():raise RuntimeError(f'Extracted verification worker returned {completed.returncode} without a report: {completed.stdout[-3000:]}')
    result=json.loads(result_path.read_text(encoding='utf-8'))
    result.update(worker_exit_code=completed.returncode,worker_stdout=completed.stdout[-4000:])
    if completed.returncode!=0:result.update(status='failed',passed=False)
    return result


def operator_fingerprints(workspace):
    paths=[workspace/'data'/f'aegis.sqlite{suffix}' for suffix in ('','-wal','-shm','-journal')]
    return {path.relative_to(workspace).as_posix():digest_file(path) if path.exists() else None for path in paths}


def verify_package(archive,workspace=ROOT):
    workspace=Path(workspace).resolve();archive=Path(archive).resolve()
    started=time.monotonic();before=operator_fingerprints(workspace)
    result={'status':'failed','passed':False,'checked_at':datetime.now(timezone.utc).isoformat(),'archive':str(archive),
            'fresh_python_environment':False,'isolated_extracted_directory':True,'network_requested':False,
            'operator_database_modified':None,'checks':[],'check_results':[],
            'limitations':['The existing installed dependency environment is reused; no fresh dependency installation is claimed.',
                           'Only trusted project archives may be executed. Internal hashes are not a signature or an untrusted-code security sandbox.',
                           'Offline ASGI workflows do not prove a real browser rendering, live provider connectivity or a completed timed presentation.']}
    try:
        result['archive_sha256']=digest_file(archive)
        temp_root=workspace/'.tools/package-verification';temp_root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='reviewer-',dir=temp_root) as temporary:
            folder=Path(temporary).resolve();target=folder/'extracted';target.mkdir()
            _assert(folder.is_relative_to(temp_root.resolve()),'Temporary directory escaped workspace isolation')
            result.update(validate_and_extract(archive,target))
            result['checks'].append('archive paths, exact manifest membership, hashes, sizes and exclusions verified')
            result['check_results'].append({'name':result['checks'][-1],'status':'passed'})
            worker=_run_worker(target,folder/'worker-result.json')
            result['checks'].extend(worker.pop('checks',[]));result['check_results'].extend(worker.pop('check_results',[]))
            result.update(worker)
    except Exception as error:
        result.update(status='failed',passed=False,error=f'{type(error).__name__}: {error}')
        result['check_results'].append({'name':'reviewer archive verification','status':'failed','detail':result['error']})
    finally:
        result['operator_database_modified']=operator_fingerprints(workspace)!=before
        if result['operator_database_modified']:
            result.update(status='failed',passed=False,error='Original operator database fingerprints changed during package verification')
            result['check_results'].append({'name':'original operator database preserved','status':'failed','detail':result['error']})
        else:
            result['checks'].append('original operator database and SQLite sidecar fingerprints unchanged')
            result['check_results'].append({'name':result['checks'][-1],'status':'passed'})
        result['finished_at']=datetime.now(timezone.utc).isoformat();result['duration_seconds']=round(time.monotonic()-started,3)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,default=ROOT/'artifacts/aegis-review-draft.zip')
    parser.add_argument('--report',type=Path,default=ROOT/'reports/package_verification.json')
    parser.add_argument('--worker',type=Path,help=argparse.SUPPRESS)
    parser.add_argument('--worker-result',type=Path,help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.worker is not None:
        result=run_extracted_workflows(args.worker)
        if args.worker_result is None:parser.error('--worker-result is required for an isolated worker')
        args.worker_result.write_text(json.dumps(result,indent=2),encoding='utf-8')
        return 0 if result['passed'] else 1
    result=verify_package(args.archive)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    return 0 if result['passed'] else 1


if __name__=='__main__':sys.exit(main())
