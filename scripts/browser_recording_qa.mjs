/** Actual Chrome preparation checks for the final recording. This is automated
 * SIMULATION evidence, never a human presentation, physical sensor or video.
 * UI performs rescue/driver actions; guarded APIs maintain the rehearsal record.
 * Run only against a new launcher-owned isolated offline UUID, never port 8000.
 */
import fs from 'node:fs/promises';
import {createReadStream} from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {chromium} from '../.tools/browser-qa/node_modules/playwright-core/index.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const base=(process.env.AEGIS_QA_BASE_URL||process.env.AEGIS_BASE_URL||'').replace(/\/$/,'');
const expectedUUID=process.env.AEGIS_QA_REHEARSAL_ID||process.env.AEGIS_REHEARSAL_ID||'';
const parsed=new URL(base);
if(parsed.protocol!=='http:'||parsed.hostname!=='127.0.0.1'||['','8000'].includes(parsed.port)||parsed.pathname!=='/'||parsed.search||parsed.hash)throw new Error('Use a verified isolated loopback QA port, never operator port 8000.');
if(!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(expectedUUID))throw new Error('Set AEGIS_QA_REHEARSAL_ID to a fresh reserved rehearsal UUID.');
const folder=path.join(root,'reports/browser_qa/recording');
await fs.mkdir(folder,{recursive:true});
const previous=await fs.readdir(folder);
if(previous.includes('results.json')){
  const history=path.join(folder,'history',new Date().toISOString().replace(/[:.]/g,'-'));
  await fs.mkdir(history,{recursive:true});
  for(const name of previous)if(/\.(json|png)$/.test(name))await fs.copyFile(path.join(folder,name),path.join(history,name));
}
const normal=value=>value.replace(/\s+/g,' ').trim();
const canonical=value=>JSON.stringify(value,(_key,item)=>item&&typeof item==='object'&&!Array.isArray(item)?Object.fromEntries(Object.keys(item).sort().map(key=>[key,item[key]])):item);
const same=(left,right)=>canonical(left)===canonical(right);
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const save=(name,value)=>fs.writeFile(path.join(folder,name+'.json'),JSON.stringify(value,null,2)+'\n');
async function fingerprint(filename){try{const stat=await fs.stat(filename);const digest=createHash('sha256');for await(const bytes of createReadStream(filename))digest.update(bytes);return{exists:true,bytes:stat.size,sha256:digest.digest('hex')};}catch(error){if(error.code==='ENOENT')return{exists:false};throw error;}}
async function database(filename){return Object.fromEntries(await Promise.all(['','-wal','-shm','-journal'].map(async suffix=>[suffix||'sqlite',await fingerprint(filename+suffix)])));}
async function tree(relative){const found={};async function visit(directory){let entries;try{entries=await fs.readdir(directory,{withFileTypes:true});}catch(error){if(error.code==='ENOENT')return;throw error;}for(const entry of entries){const filename=path.join(directory,entry.name);if(entry.isDirectory())await visit(filename);else if(entry.isFile())found[path.relative(root,filename).replaceAll('\\','/')]=await fingerprint(filename);else if(entry.isSymbolicLink())found[path.relative(root,filename).replaceAll('\\','/')]={symlink_not_followed:true};}}await visit(path.join(root,relative));return found;}
async function originals(){const filename=path.join(root,'data/manifests/inventory.json');const manifest=JSON.parse(await fs.readFile(filename,'utf8'));const files=[];for(const row of manifest.files){const resolved=path.resolve(row.path),relative=path.relative(root,resolved);if(relative==='..'||relative.startsWith('..'+path.sep)||path.isAbsolute(relative)){files.push({filename:row.filename,outside_workspace_not_followed:true});continue;}files.push({filename:row.filename,expected_sha256:row.sha256,...await fingerprint(resolved)});}return{manifest:await fingerprint(filename),files};}
const views=[
  ['Command center','Regional command center'],['Save the Load','Save the Load'],
  ['Route laboratory','Test the journey ahead'],['Road intelligence','Inspect the road ahead'],
  ['Dispatcher desk','Turn reports into reviewed action'],['AEGIS Drive','Your assigned journey'],
  ['Evidence assistant','Understand the evidence behind a decision'],['Model evaluation','Measured model performance'],
  ['Project brief','Know what works. Show the evidence.'],['Sources & evidence','Evidence with a clear origin'],
];
const stages=['overview','evidence_science','disruption','approval','driver','closing'];
const presenter='Automated recording preparation QA';
const actor='Automated recording QA dispatcher';
const reason='Automated isolated SIMULATION check: reviewed modeled quality, receiving assumptions and route limitations; no real dispatcher or recipient approval is claimed.';
const incidentNote='Automated isolated recording QA report for exact rescued SH05/T05 while parked; no physical driver, emergency or real incident is claimed.';
const result={checked_at:new Date().toISOString(),base_url:base,expected_rehearsal_id:expectedUUID,
  run_kind:'automated_check',human_rehearsal_verified:false,video_recorded:false,physical_sensor_verified:false,
  final_submission_verified:false,public_provider_refresh_requested:false,actual_osrm_queried:false,
  scope:'Actual Chrome desktop/mobile navigation, guide anchor, Save the Load rescue and exact parked driver handoff. Guarded APIs maintain the automated rehearsal tracker.',
  limitations:['Automated simulated actions do not verify a human five-minute presentation, video quality, authorship, Kiro execution, physical sensing or food-safety clearance.','Offline routes and browser-only base-map tile placeholders are labeled; public providers are not contacted.'],
  checks:[],navigation:[],screenshots:[],page_errors:[],console_errors:[],http_failures:[],request_failures:[],
  blocked_requests:[],external_qa_placeholders:[],post_requests:[],control_requests:[]};
const check=(name,passed,detail='')=>{result.checks.push({name,passed,detail});if(!passed)throw new Error(name+': '+detail);};
let browser,context,page,isolated,sessionId,run,baselineNetwork,phase='runtime_guard';
const sessionPath=suffix=>'/api/freshness/sessions/'+sessionId+(suffix?'/'+suffix:'');
const runPath=suffix=>'/api/rehearsal/'+run.id+(suffix?'/'+suffix:'');
function allowedPost(endpoint,body){
  if(!result.runtime?.isolated||result.runtime.rehearsal_id!==expectedUUID||!result.runtime.offline)return false;
  if(endpoint==='/api/delivery-outlook')return Number.isInteger(body?.expected_network_revision)&&body.expected_network_revision>=0&&body.added_delay_minutes===0&&body.ambient_temperature_c===30&&body.fault_truck_id===null;
  if(endpoint==='/api/rehearsal/start')return !run&&body?.presenter===presenter&&body.run_kind==='automated_check'&&body.purpose==='Automated recording preparation; this is not a human rehearsal or a recorded video.';
  if(run&&endpoint===runPath('checkpoint'))return body?.expected_version===run.version&&body.stage_id===stages[run.milestones.length]&&body.outcome==='covered'&&body.notes.startsWith('Automated Chrome check:');
  if(run&&endpoint===runPath('finish'))return body?.expected_version===run.version&&body.outcome==='completed'&&run.milestones.length===6&&body.notes.startsWith('Automated Chrome check:');
  if(endpoint==='/api/freshness/sessions')return body?.scenario==='poultry_demo'&&body.shipment_id==='SH05'&&body.expected_network_revision===baselineNetwork?.revision;
  if(sessionId&&endpoint===sessionPath('replay'))return body?.event==='heat_excursion'&&Number.isInteger(body.expected_version)&&body.expected_version>=1;
  if(sessionId&&endpoint===sessionPath('routes'))return body?.destination_id==='D06'&&body.routing==='osrm'&&Number.isInteger(body.expected_version);
  if(sessionId&&endpoint===sessionPath('proposal'))return body?.destination_id==='D06'&&Number.isInteger(body.expected_version);
  if(sessionId&&endpoint===sessionPath('approve'))return body?.destination_id==='D06'&&body.actor===actor&&body.reason===reason&&body.quality_review_confirmed===true&&body.recipient_confirmed===true&&body.routing_review_confirmed===true&&body.expected_network_revision===baselineNetwork.revision&&Number.isInteger(body.expected_version)&&/^[a-f0-9]{64}$/.test(body.proposal_hash);
  if(endpoint==='/api/drive/T05/focus')return body?.mode==='parked'&&body.parked_confirmation===true&&Number.isInteger(body.expected_version);
  if(endpoint==='/api/driver/SH05/acknowledge')return body?.expected_network_revision===result.approval?.receipt.network_revision;
  if(endpoint==='/api/driver/incident')return body?.shipment_id==='SH05'&&body.description===incidentNote&&body.expected_network_revision===result.approval?.receipt.network_revision;
  return false;
}
try{
  result.operator_before=await database(path.join(root,'data/aegis.sqlite'));
  result.raw_before=await originals();result.fixtures_before=await tree('data/fixtures');result.cache_before=await tree('data/cache');
  const existing=result.raw_before.files.filter(row=>row.exists);
  check('present inventoried originals match their supplied hashes',existing.every(row=>row.sha256===row.expected_sha256));
  result.original_raw_files_verified=existing.length;result.original_raw_files_unavailable=result.raw_before.files.length-existing.length;
  browser=await chromium.launch({executablePath:process.env.AEGIS_CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});result.browser_version=browser.version();
  context=await browser.newContext({viewport:{width:1440,height:1000},locale:'en-US',timezoneId:'America/Chicago',acceptDownloads:true});
  const get=async endpoint=>{
    const allowed=['/api/runtime-context','/api/network','/api/driver','/api/audit','/api/rehearsal','/api/freshness/context','/api/drive/T05'].includes(endpoint)||run&&[runPath(''),runPath('export')].includes(endpoint);
    if(!allowed)throw new Error('Control GET outside allowlist: '+endpoint);
    const reply=await context.request.get(base+endpoint);result.control_requests.push({phase,endpoint,method:'GET',status:reply.status()});check('GET '+endpoint,reply.ok(),`HTTP ${reply.status()}`);return reply;
  };
  const json=async endpoint=>(await get(endpoint)).json();
  const post=async(endpoint,body)=>{
    if(!allowedPost(endpoint,body))throw new Error('Control POST outside isolated allowlist: '+endpoint);
    const reply=await context.request.post(base+endpoint,{data:body});result.control_requests.push({phase,endpoint,method:'POST',body,status:reply.status()});const value=await reply.json();check('guarded POST '+endpoint,reply.ok(),`HTTP ${reply.status()}: ${JSON.stringify(value).slice(0,1800)}`);return value;
  };
  result.runtime=await json('/api/runtime-context');
  check('verified expected isolated offline UUID before every authorized write',result.runtime.mode==='isolated_rehearsal'&&result.runtime.isolated===true&&result.runtime.offline===true&&result.runtime.rehearsal_id===expectedUUID);
  isolated=path.resolve(root,result.runtime.database_relative_path||'');check('database is exactly reserved UUID path',isolated===path.join(root,'data/rehearsals',expectedUUID+'.sqlite'));
  result.isolated_before=await database(isolated);baselineNetwork=await json('/api/network');
  const initialRehearsals=await json('/api/rehearsal'),initialFreshness=await json('/api/freshness/context');
  check('fresh UUID has no assignments, active run, saved runs or experiments',(await json('/api/driver')).length===0&&!initialRehearsals.active&&(initialRehearsals.runs??[]).length===0&&initialFreshness.sessions.length===0&&initialFreshness.session_errors.length===0);
  check('SH05 is the deterministic T05 candidate',initialFreshness.demo_shipment_id==='SH05'&&baselineNetwork.shipments.some(row=>row.id==='SH05'&&row.truck_id==='T05'));
  await context.route('**/*',async route=>{
    const request=route.request(),url=new URL(request.url());
    if(['data:','blob:','about:'].includes(url.protocol)){await route.continue();return;}
    if(url.origin!==parsed.origin){
      if(request.method()==='GET'&&request.resourceType()==='image'&&/(^|\.)tile\.openstreetmap\.org$/.test(url.hostname)){
        result.external_qa_placeholders.push({phase,url:request.url(),kind:'Browser-only labeled QA tile placeholder; OpenStreetMap was not contacted.'});
        await route.fulfill({status:200,contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#eef0ec"/><text x="12" y="130" font-size="13" fill="#67756c">QA TILE PLACEHOLDER</text></svg>'});return;
      }
      result.blocked_requests.push({phase,url:request.url(),method:request.method(),reason:'External non-tile request is not authorized'});await route.abort('blockedbyclient');return;
    }
    let allowed=['GET','HEAD'].includes(request.method())&&!/\/(?:refresh)(?:\/|$)/.test(url.pathname)&&!url.searchParams.has('refresh');
    if(request.method()==='POST'){let body;try{body=request.postDataJSON();}catch{}allowed=allowedPost(url.pathname,body);result.post_requests.push({phase,path:url.pathname,body,allowed});}
    if(!allowed){result.blocked_requests.push({phase,path:url.pathname,method:request.method()});await route.abort('blockedbyclient');return;}await route.continue();
  });
  page=await context.newPage();page.setDefaultTimeout(30000);
  page.on('pageerror',error=>result.page_errors.push({phase,message:error.message}));
  page.on('console',message=>{if(message.type()==='error')result.console_errors.push({phase,message:message.text(),location:message.location()});});
  page.on('response',reply=>{if(reply.status()>=400&&new URL(reply.url()).origin===parsed.origin)result.http_failures.push({phase,url:reply.url(),status:reply.status()});});
  page.on('requestfailed',request=>result.request_failures.push({phase,url:request.url(),reason:request.failure()?.errorText}));
  const nav=()=>page.getByRole('navigation',{name:'Main navigation',exact:true});
  const lab=()=>page.getByRole('region',{name:'Save the Load workspace',exact:true});
  const driver=()=>page.getByRole('region',{name:'AEGIS Drive workspace',exact:true});
  const panel=()=>page.getByRole('region',{name:'Guided presentation rehearsal',exact:true});
  const navigate=async name=>{await nav().getByRole('button',{name,exact:true}).click();await page.getByRole('heading',{level:1,name:views.find(row=>row[0]===name)[1],exact:true}).waitFor();};
  const capture=async name=>{check('screenshot count stays within six',result.screenshots.length<6);await page.screenshot({path:path.join(folder,name+'.png'),fullPage:false});result.screenshots.push(name+'.png');};
  const noOverflow=async label=>{const sizes=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth}));check(label,sizes.document<=sizes.viewport+1,JSON.stringify(sizes));};
  const uiPost=async(endpoint,action)=>{const pending=page.waitForResponse(reply=>reply.url()===base+endpoint&&reply.request().method()==='POST');await action();const reply=await pending;const value=await reply.json();check('actual UI POST '+endpoint,reply.ok(),`HTTP ${reply.status()}: ${JSON.stringify(value).slice(0,1800)}`);return value;};
  const settled=async snapshot=>{await lab().getByText('Experiment v'+snapshot.version,{exact:true}).waitFor();await lab().getByRole('button',{name:'Read latest capture',exact:true}).waitFor();};
  const covered=async stage=>{run=await post(runPath('checkpoint'),{expected_version:run.version,stage_id:stage,outcome:'covered',notes:'Automated Chrome check: '+stage+'; simulated app workflow only, no human presentation, screen narration or video claim.'});check('ordered '+stage+' checkpoint',run.milestones.at(-1).stage_id===stage&&run.milestones.at(-1).outcome==='covered');return run.milestones.at(-1);};

  phase='desktop_navigation';await page.goto(base+'/',{waitUntil:'domcontentloaded'});await page.getByLabel('Isolated rehearsal runtime',{exact:true}).waitFor();
  for(const [size,width,height] of [['desktop',1440,1000],['mobile',390,844]]){
    phase=size+'_navigation';await page.setViewportSize({width,height});
    check(size+' navigation is operational first and Sources last',same((await nav().getByRole('button').allInnerTexts()).map(normal),views.map(row=>row[0])));
    for(const [name,heading] of views){await navigate(name);check(size+' '+name+' has one correct global heading',await page.getByRole('heading',{level:1}).count()===1);result.navigation.push({viewport:size,name,heading});await noOverflow(size+' '+name+' fits viewport');if(size==='desktop'&&name==='Command center')await capture('desktop-operational-navigation');}
    if(size==='mobile'){await page.getByRole('heading',{level:1}).scrollIntoViewIfNeeded();await capture('mobile-sources-last');}
  }
  await page.setViewportSize({width:1440,height:1000});
  phase='guide_anchor';await navigate('Project brief');
  const guideLink=page.getByRole('link',{name:'Recording checklist & video runbook',exact:true});await guideLink.waitFor();
  check('Project brief links to the recording runbook anchor',await guideLink.getAttribute('href')==='/api/master-guide.html#record-the-final-video');
  const popupPending=page.waitForEvent('popup');await guideLink.click();const guide=await popupPending;await guide.waitForLoadState('domcontentloaded');
  check('actual guide opens locally at final-video section',guide.url()===base+'/api/master-guide.html#record-the-final-video'&&await guide.locator('#record-the-final-video').count()===1);
  result.guide={url:guide.url(),anchor_text:await guide.locator('#record-the-final-video').innerText()};await guide.close();
  phase='start_automated_tracker';run=await post('/api/rehearsal/start',{presenter,purpose:'Automated recording preparation; this is not a human rehearsal or a recorded video.',run_kind:'automated_check'});result.run_id=run.id;
  check('tracker is explicitly automated and preserves five-minute target',run.run_kind==='automated_check'&&run.target_seconds===300);await covered('overview');await covered('evidence_science');
  phase='rehearsal_freshness_navigation';await navigate('Command center');await page.getByLabel('Select shipment',{exact:true}).selectOption('SH02');await page.getByRole('button',{name:'Model this lot’s shelf life',exact:true}).click();await lab().getByRole('combobox',{name:'Candidate to explore',exact:true}).waitFor();
  check('explicit Command handoff selects SH02 without starting an experiment',await lab().getByRole('combobox',{name:'Candidate to explore',exact:true}).inputValue()==='SH02'&&(await json('/api/freshness/context')).sessions.length===0);
  await navigate('Project brief');await panel().getByRole('button',{name:'Open Save the Load',exact:true}).click();await lab().getByRole('combobox',{name:'Candidate to explore',exact:true}).waitFor();
  check('guided rehearsal handoff clears explicit selection and opens default SH05',await lab().getByRole('combobox',{name:'Candidate to explore',exact:true}).inputValue()==='SH05');
  phase='actual_heat_replay';
  check('default Save the Load candidate is SH05',await lab().getByRole('combobox',{name:'Candidate to explore',exact:true}).inputValue()==='SH05');
  let snapshot=await uiPost('/api/freshness/sessions',()=>lab().getByRole('button',{name:'Start rescue experiment',exact:true}).click());sessionId=snapshot.id;result.session_id=sessionId;await settled(snapshot);await lab().getByRole('checkbox',{name:'Follow incoming readings every 5s',exact:true}).uncheck();
  snapshot=await uiPost(sessionPath('replay'),()=>lab().getByRole('button',{name:'Replay heat excursion',exact:true}).click());await settled(snapshot);await save('actual-heated-experiment',snapshot);
  check('stored simulated heat recalculates an actual rescue proposal',snapshot.provenance.telemetry==='simulated_replay'&&snapshot.sensor.source==='simulated_replay'&&snapshot.rescue.triggered&&snapshot.freshness.coverage.complete&&snapshot.rescue.proposal_hash&&snapshot.rescue.plan_summary.constraint_violations===0);
  const disruption=await covered('disruption');check('disruption checkpoint uses stored freshness evidence',disruption.evidence.kind==='recorded_operational_actions'&&disruption.evidence.actions.some(row=>row.action==='freshness_replay')&&disruption.evidence.freshness_context.session_id===sessionId);
  if(await lab().getByRole('button',{name:/^Show all .* candidates and exclusions$/}).count())await lab().getByRole('button',{name:/^Show all .* candidates and exclusions$/}).click();
  const target=snapshot.rescue.options.find(row=>row.destination_id==='D06');check('D06 is an eligible dispatchable modeled recipient',target?.eligible&&target.dispatchable);
  await lab().getByRole('group',{name:'Calculated rescue destinations',exact:true}).getByRole('button',{name:target.destination_name,exact:false}).click();
  snapshot=await uiPost(sessionPath('routes'),()=>lab().getByRole('button',{name:'Check road route',exact:true}).click());await settled(snapshot);
  if(await lab().getByRole('button',{name:'Prepare selected rescue',exact:true}).count()){snapshot=await uiPost(sessionPath('proposal'),()=>lab().getByRole('button',{name:'Prepare selected rescue',exact:true}).click());await settled(snapshot);}
  const routed=snapshot.rescue.options.find(row=>row.destination_id==='D06');check('offline D06 route is a labeled estimate, not public OSRM success',routed.fallback===true&&routed.geometry.type==='LineString'&&snapshot.rescue.proposed_destination_id==='D06');
  await lab().getByRole('heading',{name:'Automatic rescue search',exact:true}).scrollIntoViewIfNeeded();await capture('desktop-heat-and-rescue-plan');
  phase='actual_explicit_rescue_approval';await lab().getByRole('button',{name:'Review '+target.destination_name,exact:true}).click();
  const review=lab().getByRole('region',{name:'Human rescue approval',exact:true});await review.waitFor();const approve=review.getByRole('button',{name:'Approve simulated rescue plan',exact:true});
  check('rescue approval requires identified review and all confirmations',await approve.isDisabled());await review.getByRole('textbox',{name:'Reviewing dispatcher',exact:true}).fill(actor);await review.getByRole('textbox',{name:'Reason for rescue approval',exact:true}).fill(reason);
  const confirmations=review.getByRole('checkbox');check('three independent confirmations are present',await confirmations.count()===3);await confirmations.nth(0).check();await confirmations.nth(1).check();check('two confirmations cannot approve',await approve.isDisabled());await confirmations.nth(2).check();check('complete identified simulated review enables explicit approval',await approve.isEnabled());
  await review.scrollIntoViewIfNeeded();await capture('desktop-three-confirmation-review');
  result.approval=await uiPost(sessionPath('approve'),()=>approve.click());await lab().getByRole('region',{name:'Confirmed rescue receipt',exact:true}).waitFor();await save('actual-approved-rescue',result.approval);
  const approvedNetwork=await json('/api/network'),assignments=await json('/api/driver'),rescued=assignments.find(row=>row.id==='SH05');
  check('whole checked plan commits once with exact rescued T05 SH05 D06',result.approval.receipt.network_revision===baselineNetwork.revision+1&&approvedNetwork.revision===result.approval.receipt.network_revision&&assignments.length===result.approval.receipt.assignments_count&&assignments.length===snapshot.rescue.plan_summary.assignments_count&&rescued?.truck_id==='T05'&&rescued.destination==='D06'&&rescued.freshness_rescue.session_id===sessionId&&!rescued.acknowledged);
  check('holds and recalls remain unchanged and cannot dispatch',baselineNetwork.lots.every(lot=>{const current=approvedNetwork.lots.find(row=>row.id===lot.id);return current.held===lot.held&&current.recalled===lot.recalled;})&&assignments.every(trip=>{const lot=approvedNetwork.lots.find(row=>row.id===trip.lot_id),truck=approvedNetwork.trucks.find(row=>row.id===trip.truck_id);return lot&&!lot.held&&!lot.recalled&&lot.eligible&&truck?.eligible&&truck.refrigerated;}));
  const approvalStage=await covered('approval');check('approval checkpoint is bound to actual stored freshness rescue',approvalStage.evidence.kind==='recorded_operational_actions'&&approvalStage.evidence.actions.some(row=>row.action==='freshness_rescue_approve')&&approvalStage.evidence.freshness_context.session_id===sessionId);
  phase='actual_exact_driver_handoff';await lab().getByRole('button',{name:'Open approved driver assignments',exact:true}).click();await driver().waitFor();
  const destination=approvedNetwork.nodes.find(row=>row.id==='D06');await driver().getByRole('heading',{name:destination.name,exact:true}).waitFor();
  check('rescue receipt opens exact T05 SH05 destination',(await driver().locator('.drive-destination').innerText()).includes('T05')&&(await driver().locator('.drive-destination').innerText()).includes('SH05'));
  check('driver reporting and acknowledgment require parked confirmation',await driver().getByRole('button',{name:/^Dispatch instructions/}).isDisabled()&&await driver().getByRole('button',{name:/^Report an issue/}).isDisabled()&&await driver().locator('textarea').count()===0);
  const parked=await uiPost('/api/drive/T05/focus',()=>driver().getByRole('button',{name:'Confirm safely parked',exact:true}).click());check('actual T05 parked confirmation enables temporary interaction',parked.interaction_allowed===true);
  await driver().getByRole('button',{name:/^Dispatch instructions/}).click();await driver().getByRole('heading',{name:'Dispatcher-approved trip instructions',exact:true}).waitFor();
  check('approved instructions retain exact SH05 rescue context',(await driver().locator('.drive-detail-panel').innerText()).includes('SH05')&&(await driver().locator('.driver-instruction').innerText()).includes('Save the Load: reviewed destination D06'));
  await uiPost('/api/driver/SH05/acknowledge',()=>driver().getByRole('button',{name:'Acknowledge assignment',exact:true}).click());await driver().getByRole('button',{name:'Assignment acknowledged',exact:true}).waitFor();
  await page.setViewportSize({width:390,height:844});await driver().locator('.drive-detail-panel').scrollIntoViewIfNeeded();await noOverflow('mobile exact rescued driver instructions fit viewport');await capture('mobile-exact-rescued-driver');
  await driver().getByRole('button',{name:/^Report an issue/}).click();await driver().getByLabel('Report a driver incident',{exact:true}).fill(incidentNote);await uiPost('/api/driver/incident',()=>driver().getByRole('button',{name:'Send to dispatcher',exact:true}).click());
  const driverStage=await covered('driver');check('driver milestone proves parked ack incident for exact T05 SH05',driverStage.evidence.kind==='recorded_operational_actions'&&same(driverStage.evidence.actions.map(row=>row.action),['driver_focus','acknowledge','incident'])&&driverStage.evidence.assignment_context.id==='SH05'&&driverStage.evidence.assignment_context.truck_id==='T05'&&driverStage.evidence.assignment_context.destination==='D06');
  await covered('closing');phase='freeze_automated_record';run=await post(runPath('finish'),{expected_version:run.version,outcome:'completed',notes:'Automated Chrome check: six stages exercised with simulated app evidence. Team narration, a real timed video, scientific limitations and author signoff still require human review.'});
  check('completed timer retains actual duration and six covered stages',run.status==='completed'&&run.run_kind==='automated_check'&&run.elapsed_seconds>=0&&run.milestones.length===6&&run.milestones.every(row=>row.outcome==='covered'));
  const exportReply=await get(runPath('export')),exportBytes=await exportReply.body(),exported=JSON.parse(exportBytes);
  await fs.writeFile(path.join(folder,'automated-recording-rehearsal.json'),exportBytes);
  check('immutable rehearsal export checksum matches actual bytes',exportReply.headers()['x-aegis-snapshot-sha256']===hash(exportBytes));
  check('export explicitly keeps human presentation Kiro and authorship gates open',exported.five_minute_presentation_verified===false&&exported.genuine_kiro_execution_verified===false&&exported.author_signoff_verified===false&&exported.run.run_kind==='automated_check');
  check('all three operational stages export actual retained audit references',exported.run.milestones.filter(row=>['disruption','approval','driver'].includes(row.stage_id)).every(row=>row.evidence.kind==='recorded_operational_actions'&&row.evidence.audit_ids.length>0));
  result.recorded_elapsed_seconds=run.elapsed_seconds;result.export_sha256=hash(exportBytes);result.milestones=exported.run.milestones;
  await page.setViewportSize({width:1440,height:1000});await navigate('Project brief');await panel().getByLabel('Saved rehearsal',{exact:true}).selectOption(run.id);await panel().getByRole('button',{name:'Open saved rehearsal',exact:true}).click();await panel().getByRole('link',{name:'Download rehearsal evidence JSON',exact:true}).waitFor();await panel().scrollIntoViewIfNeeded();await capture('desktop-completed-automated-record');
  phase='final_guards';check('all UI mutations are narrow authorized isolated workflow actions',result.post_requests.length>0&&result.post_requests.every(row=>row.allowed)&&result.blocked_requests.length===0);
  check('no public refresh was requested',result.post_requests.every(row=>!row.path.includes('/refresh/'))&&result.control_requests.every(row=>!row.endpoint.includes('/refresh/')));
  check('Chrome has no unexpected JavaScript console HTTP or request failures',result.page_errors.length===0&&result.console_errors.length===0&&result.http_failures.length===0&&result.request_failures.length===0,JSON.stringify({page:result.page_errors,console:result.console_errors,http:result.http_failures,request:result.request_failures}));
  result.passed=true;
}catch(error){result.passed=false;result.failure={phase,message:error.stack||String(error)};process.exitCode=1;if(page&&result.screenshots.length<6){try{await page.screenshot({path:path.join(folder,'failure.png'),fullPage:false});result.screenshots.push('failure.png');}catch{}}}
finally{
  await browser?.close();
  try{
    result.operator_after=await database(path.join(root,'data/aegis.sqlite'));result.raw_after=await originals();result.fixtures_after=await tree('data/fixtures');result.cache_after=await tree('data/cache');if(isolated)result.isolated_after=await database(isolated);
    for(const [name,passed] of [['operator database and all sidecars untouched',same(result.operator_before,result.operator_after)],['raw manifest and inventoried originals untouched',same(result.raw_before,result.raw_after)],['dated fixtures and provider caches untouched',same(result.fixtures_before,result.fixtures_after)&&same(result.cache_before,result.cache_after)]]){result.checks.push({name,passed,detail:'Actual SHA-256 file fingerprints before and after. No operator-origin write was authorized or attempted.'});if(!passed){result.passed=false;process.exitCode=1;}}
  }catch(error){result.integrity_error=String(error);result.passed=false;process.exitCode=1;}
  result.finished_at=new Date().toISOString();await save('results',result);
  console.log(JSON.stringify({passed:result.passed,checks:result.checks.length,failed:result.checks.filter(row=>!row.passed),failure:result.failure,screenshots:result.screenshots.length,report:'reports/browser_qa/recording/results.json'},null,2));
}
