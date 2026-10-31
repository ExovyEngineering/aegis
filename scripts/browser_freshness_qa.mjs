/** Real Chrome Save-the-Load workflow against one verified offline rehearsal.
 * All deliberate writes are confined to that UUID database. Sensor packets and
 * confirmations are automated SIMULATION fixtures, not physical/human evidence.
 * External base-map tiles receive recorded browser-only placeholders.
 */
import fs from 'node:fs/promises';
import {createReadStream} from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {chromium} from '../.tools/browser-qa/node_modules/playwright-core/index.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const base=(process.env.AEGIS_BASE_URL||process.env.AEGIS_QA_BASE_URL||'').replace(/\/$/,'');
const expectedUUID=process.env.AEGIS_QA_REHEARSAL_ID||process.env.AEGIS_REHEARSAL_ID||'';
const parsed=new URL(base);
if(parsed.protocol!=='http:'||parsed.hostname!=='127.0.0.1'||['','8000'].includes(parsed.port)||parsed.pathname!=='/'||parsed.search||parsed.hash)throw new Error('Use a verified isolated loopback QA port, never operator port 8000');
if(!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(expectedUUID))throw new Error('Set AEGIS_QA_REHEARSAL_ID to the reserved rehearsal UUID');
const folder=path.join(root,'reports/browser_qa/freshness');
await fs.mkdir(folder,{recursive:true});
const previous=await fs.readdir(folder);
if(previous.includes('results.json')){
  const history=path.join(folder,'history',new Date().toISOString().replace(/[:.]/g,'-'));await fs.mkdir(history,{recursive:true});
  for(const name of previous)if(/\.(json|png)$/.test(name))await fs.copyFile(path.join(folder,name),path.join(history,name));
}
const canonical=value=>JSON.stringify(value,(_key,item)=>item&&typeof item==='object'&&!Array.isArray(item)?Object.fromEntries(Object.keys(item).sort().map(key=>[key,item[key]])):item);
const same=(left,right)=>canonical(left)===canonical(right);
const normal=value=>value.replace(/\s+/g,' ').trim();
const escape=value=>value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
const save=(name,value)=>fs.writeFile(path.join(folder,name+'.json'),JSON.stringify(value,null,2)+'\n');
async function fingerprint(filename){try{const stat=await fs.stat(filename);const hash=createHash('sha256');for await(const bytes of createReadStream(filename))hash.update(bytes);return{exists:true,bytes:stat.size,sha256:hash.digest('hex')};}catch(error){if(error.code==='ENOENT')return{exists:false};throw error;}}
async function database(filename){return Object.fromEntries(await Promise.all(['','-wal','-shm','-journal'].map(async suffix=>[suffix||'sqlite',await fingerprint(filename+suffix)])));}
async function tree(relative){const found={};async function visit(directory){let entries;try{entries=await fs.readdir(directory,{withFileTypes:true});}catch(error){if(error.code==='ENOENT')return;throw error;}for(const entry of entries){const filename=path.join(directory,entry.name);if(entry.isDirectory())await visit(filename);else if(entry.isFile())found[path.relative(root,filename).replaceAll('\\','/')]=await fingerprint(filename);else if(entry.isSymbolicLink())found[path.relative(root,filename).replaceAll('\\','/')]={symlink_not_followed:true};}}await visit(path.join(root,relative));return found;}
async function originals(){const manifestFile=path.join(root,'data/manifests/inventory.json');const manifest=JSON.parse(await fs.readFile(manifestFile,'utf8'));const found=[];for(const row of manifest.files){const filename=path.resolve(row.path);const relative=path.relative(root,filename);if(relative==='..'||relative.startsWith('..'+path.sep)||path.isAbsolute(relative)){found.push({filename:row.filename,outside_workspace_not_followed:true});continue;}found.push({filename:row.filename,expected_sha256:row.sha256,...await fingerprint(filename)});}return{manifest:await fingerprint(manifestFile),files:found};}
const result={checked_at:new Date().toISOString(),base_url:base,expected_rehearsal_id:expectedUUID,run_kind:'automated_check',human_rehearsal_verified:false,deliberate_writes_scope:'only the verified isolated offline UUID',physical_hardware_queried:false,actual_osrm_queried:false,public_provider_refresh_requested:false,external_map_tiles_replaced_with_qa_placeholders:true,checks:[],screenshots:[],page_errors:[],console_errors:[],http_failures:[],request_failures:[],expected_api_rejections:[],blocked_requests:[],external_qa_placeholders:[],post_requests:[],control_requests:[]};
const check=(name,passed,detail='')=>{result.checks.push({name,passed,detail});if(!passed)throw new Error(name+': '+detail);};
let browser,context,page,phase='runtime_guard',isolated,sessionId,truckId,baselineNetwork,baselineAssignments;
const sessionPath=suffix=>'/api/freshness/sessions/'+sessionId+(suffix?'/'+suffix:'');
try{
  result.operator_before=await database(path.join(root,'data/aegis.sqlite'));
  result.raw_before=await originals();result.fixtures_before=await tree('data/fixtures');result.cache_before=await tree('data/cache');
  const existingRaw=result.raw_before.files.filter(row=>row.exists);
  check('all present inventoried original hashes match their supplied manifest',existingRaw.every(row=>row.sha256===row.expected_sha256));
  result.original_raw_files_verified=existingRaw.length;result.original_raw_files_unavailable=result.raw_before.files.length-existingRaw.length;
  browser=await chromium.launch({executablePath:process.env.AEGIS_CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});result.browser_version=browser.version();
  context=await browser.newContext({viewport:{width:1440,height:1050},locale:'en-US',timezoneId:'America/Chicago',acceptDownloads:true});
  const get=async endpoint=>{
    const allowed=['/api/runtime-context','/api/network','/api/driver','/api/dispatch','/api/readiness','/api/audit','/api/freshness/context'].includes(endpoint)||sessionId&&endpoint===sessionPath('')||truckId&&endpoint==='/api/drive/'+truckId;
    if(!allowed)throw new Error('Control GET outside the explicit allowlist: '+endpoint);
    const reply=await context.request.get(base+endpoint);result.control_requests.push({phase,endpoint,method:'GET',status:reply.status()});check('GET '+endpoint,reply.ok(),`HTTP ${reply.status()}`);return reply.json();
  };
  const runtime=await get('/api/runtime-context');result.runtime=runtime;
  check('expected isolated offline UUID is verified before any deliberate mutation',runtime.mode==='isolated_rehearsal'&&runtime.isolated===true&&runtime.offline===true&&runtime.rehearsal_id===expectedUUID);
  isolated=path.resolve(root,runtime.database_relative_path||'');check('QA database is exactly the reserved UUID path',isolated===path.join(root,'data/rehearsals',expectedUUID+'.sqlite'));
  baselineNetwork=await get('/api/network');baselineAssignments=await get('/api/driver');
  check('fresh UUID starts with no approved assignments',baselineAssignments.length===0);
  result.isolated_before=await database(isolated);
  const info=await get('/api/freshness/context');await save('actual-initial-context',info);
  check('documented deterministic rescue candidate is SH05',info.demo_shipment_id==='SH05'&&info.shipments.some(row=>row.id==='SH05'));
  const original=baselineNetwork.shipments.find(row=>row.id==='SH05');check('SH05 is a known simulated candidate',!!original);truckId=original.truck_id;
  const originalNode=baselineNetwork.nodes.find(node=>node.id===original.destination);const rescuedNode=baselineNetwork.nodes.find(node=>node.id==='D06');
  check('review target D06 differs from the original destination',!!rescuedNode&&original.destination!=='D06');
  await save('actual-original-shipment',original);
  function allowedPost(endpoint,body){
    if(endpoint==='/api/delivery-outlook')return body&&body.expected_network_revision>=0&&body.added_delay_minutes===0&&body.ambient_temperature_c===30&&body.fault_truck_id===null;
    if(endpoint==='/api/freshness/sessions')return body?.scenario==='poultry_demo'&&body.shipment_id==='SH05'&&body.expected_network_revision===baselineNetwork.revision;
    if(sessionId&&endpoint===sessionPath('replay'))return ['normal','heat_excursion','road_delay','recovery'].includes(body?.event)&&Number.isInteger(body.expected_version)&&body.expected_version>=1;
    if(sessionId&&endpoint===sessionPath('routes'))return body?.destination_id&&body.routing==='osrm'&&runtime.offline&&Number.isInteger(body.expected_version);
    if(sessionId&&endpoint===sessionPath('proposal'))return body?.destination_id&&Number.isInteger(body.expected_version);
    if(sessionId&&endpoint===sessionPath('approve'))return body?.destination_id==='D06'&&body.actor==='Freshness QA dispatcher'&&body.quality_review_confirmed===true&&body.recipient_confirmed===true&&body.routing_review_confirmed===true&&body.expected_network_revision===baselineNetwork.revision&&Number.isInteger(body.expected_version)&&/^[a-f0-9]{64}$/.test(body.proposal_hash);
    if(truckId&&endpoint==='/api/drive/'+truckId+'/focus')return ['parked','driving'].includes(body?.mode)&&body.parked_confirmation===(body.mode==='parked')&&Number.isInteger(body.expected_version);
    return false;
  }
  async function post(endpoint,body,expected=200){
    if(!allowedPost(endpoint,body))throw new Error('Control POST outside the explicit isolated allowlist: '+endpoint);
    const reply=await context.request.post(base+endpoint,{data:body});result.control_requests.push({phase,endpoint,method:'POST',body,status:reply.status(),expected});check('control POST '+endpoint+' returns '+expected,reply.status()===expected,`HTTP ${reply.status()}`);
    const value=await reply.json();if(expected>=400)result.expected_api_rejections.push({phase,endpoint,status:reply.status(),body:value,kind:'actual stale-version rejection, not an upstream outage'});return value;
  }
  await context.route('**/*',async route=>{
    const request=route.request();const url=new URL(request.url());
    if(['data:','blob:','about:'].includes(url.protocol)){await route.continue();return;}
    if(url.origin!==parsed.origin){result.external_qa_placeholders.push({phase,url:request.url(),method:request.method(),kind:'Browser-only image placeholder; provider was not contacted'});await route.fulfill({status:200,contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#eef0ec"/></svg>'});return;}
    let allowed=['GET','HEAD'].includes(request.method())&&!/\/(?:refresh)(?:\/|$)/.test(url.pathname)&&!url.searchParams.has('refresh');
    if(request.method()==='POST'){let body;try{body=request.postDataJSON();}catch{}allowed=allowedPost(url.pathname,body);result.post_requests.push({phase,path:url.pathname,body,allowed});}
    if(!allowed){result.blocked_requests.push({phase,path:url.pathname,method:request.method()});await route.abort('blockedbyclient');return;}
    await route.continue();
  });
  page=await context.newPage();page.setDefaultTimeout(30000);
  page.on('pageerror',error=>result.page_errors.push({phase,message:error.message}));
  page.on('console',message=>{if(message.type()!=='error')return;const item={phase,message:message.text(),location:message.location()};if(phase==='actual_stale_ui_rejection'&&item.message.includes('409'))result.expected_api_rejections.push({...item,kind:'Chrome console from deliberate actual HTTP409'});else result.console_errors.push(item);});
  page.on('response',reply=>{if(reply.status()<400||new URL(reply.url()).origin!==parsed.origin)return;const item={phase,url:reply.url(),status:reply.status()};if(phase==='actual_stale_ui_rejection'&&reply.url()===base+sessionPath('replay')&&reply.status()===409)result.expected_api_rejections.push({...item,kind:'Actual stale UI replay, not mocked'});else result.http_failures.push(item);});
  page.on('requestfailed',request=>result.request_failures.push({phase,url:request.url(),reason:request.failure()?.errorText}));
  const nav=()=>page.getByRole('navigation',{name:'Main navigation',exact:true});
  const lab=()=>page.getByRole('region',{name:'Save the Load workspace',exact:true});
  const driver=()=>page.getByRole('region',{name:'AEGIS Drive workspace',exact:true});
  const nextPost=endpoint=>page.waitForResponse(reply=>reply.url()===base+endpoint&&reply.request().method()==='POST');
  const nextSession=()=>page.waitForResponse(reply=>reply.url()===base+sessionPath('')&&reply.request().method()==='GET');
  const capture=async name=>{check('screenshot budget stays within ten images',result.screenshots.length<10);await page.screenshot({path:path.join(folder,name+'.png'),fullPage:false});result.screenshots.push(name+'.png');};
  const noOverflow=async name=>check(name,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  const exportCapture=async name=>{const pending=page.waitForEvent('download');await lab().getByRole('button',{name:'Export captured freshness experiment',exact:true}).click();const download=await pending;const filename=path.join(folder,name+'.json');await download.saveAs(filename);return JSON.parse(await fs.readFile(filename,'utf8'));};
  const bodyOf=async(reply,label)=>{const value=await reply.json();check(label,reply.ok(),`HTTP ${reply.status()}: ${JSON.stringify(value).slice(0,1600)}`);return value;};
  const settled=async value=>{await lab().getByText(`Experiment v${value.version}`,{exact:true}).waitFor();await lab().getByRole('button',{name:'Read latest capture',exact:true}).waitFor();};
  async function selectOption(option){await lab().getByRole('group',{name:'Calculated rescue destinations',exact:true}).getByRole('button',{name:new RegExp(escape(option.destination_name))}).click();}
  phase='baseline_creation';await page.goto(base+'/',{waitUntil:'domcontentloaded'});await nav().getByRole('button',{name:'Save the Load',exact:true}).click();await lab().getByRole('button',{name:'Start rescue experiment',exact:true}).waitFor();
  result.initial_ui_candidate=await lab().getByRole('combobox',{name:'Candidate to explore',exact:true}).inputValue();check('generic Save the Load navigation defaults to SH05',result.initial_ui_candidate==='SH05');
  let pending=nextPost('/api/freshness/sessions');await lab().getByRole('button',{name:'Start rescue experiment',exact:true}).click();let baseline=await bodyOf(await pending,'actual replay experiment is created');sessionId=baseline.id;await settled(baseline);await save('actual-baseline-experiment',baseline);
  await lab().getByRole('checkbox',{name:'Follow incoming readings every 5s',exact:true}).uncheck();
  check('baseline uses stored simulated readings and no rescue trigger',baseline.shipment.id==='SH05'&&baseline.provenance.telemetry==='simulated_replay'&&baseline.sensor.source==='simulated_replay'&&!baseline.rescue.triggered&&baseline.freshness.coverage.complete&&baseline.freshness.remaining_quality_hours===9);
  check('experiment baseline leaves actual network and assignments unchanged',same(await get('/api/network'),baselineNetwork)&&same(await get('/api/driver'),baselineAssignments));
  await lab().locator('.freshness-kpis').scrollIntoViewIfNeeded();await capture('desktop-baseline-quality-window');
  phase='heat_excursion';pending=nextPost(sessionPath('replay'));await lab().getByRole('button',{name:'Replay heat excursion',exact:true}).click();let heated=await bodyOf(await pending,'actual heat frames append and recalculate');await settled(heated);await save('actual-heated-experiment',heated);
  check('temperature excursion changes point and conservative clocks to the documented calculated range',Math.abs(heated.freshness.remaining_hours_at_forecast_temperature-4.388539913)<.002&&Math.abs(heated.freshness.remaining_quality_hours-1.508947695)<.002&&heated.freshness.remaining_quality_hours<heated.freshness.remaining_hours_at_forecast_temperature);
  check('conservative window drives an automatic rescue calculation',heated.rescue.triggered&&heated.rescue.proposal_hash&&heated.rescue.plan_summary?.constraint_violations===0&&heated.rescue.options.some(option=>option.destination_id==='D06'&&option.eligible&&option.dispatchable));
  const cards=lab().locator('.freshness-kpis article');check('displayed clocks distinguish point estimate and sensitivity window',(await cards.nth(0).innerText()).includes('4.4')&&(await cards.nth(2).innerText()).includes('1.5'));
  check('all five sensor channels are visibly attributed as input/context',await lab().locator('.freshness-sensor').count()===5&&(await lab().locator('.freshness-sensors').innerText()).includes('not a poultry freshness proxy')&&(await lab().locator('.freshness-sensors').innerText()).includes('not substituted for product temperature'));
  await lab().locator('.freshness-kpis').scrollIntoViewIfNeeded();await capture('desktop-heat-clocks-and-context-channels');
  const lotTotals=plan=>Object.fromEntries(plan.picks.map(row=>row.lot_id).filter((id,index,ids)=>ids.indexOf(id)===index).sort().map(id=>[id,plan.picks.filter(row=>row.lot_id===id).reduce((sum,row)=>sum+row.quantity_kg,0)]));
  check('actual FEFO and FIFO allocations differ under the same captured demand',heated.fefo.feasible&&!same(lotTotals(heated.fefo.fefo),lotTotals(heated.fefo.fifo))&&heated.fefo.fefo.supplied_kg===heated.fefo.fifo.supplied_kg);
  check('FEFO reduces modeled expiry exposure without calling it measured waste',heated.fefo.fefo.estimated_expiry_waste_kg<heated.fefo.fifo.estimated_expiry_waste_kg&&(await lab().innerText()).includes('stock exposed to modeled expiry'));
  const warehouse=lab().locator('section.panel').filter({has:page.getByRole('heading',{name:'Warehouse picking: arrival order or predicted expiry?',exact:true})});
  for(const [mode,label] of [['fifo','Show FIFO pick order'],['fefo','Show FEFO pick order']]){await warehouse.getByRole('button',{name:label,exact:true}).click();await page.waitForFunction(id=>document.querySelector('.freshness-fefo-table tbody tr strong')?.textContent===id,heated.fefo[mode].picks[0]?.lot_id);check(label+' shows the actual first selected lot',(await warehouse.locator('tbody tr').first().innerText()).includes(heated.fefo[mode].picks[0].lot_id));}
  await warehouse.scrollIntoViewIfNeeded();await capture('desktop-fefo-versus-fifo-picks');
  phase='route_and_proposal';const alternative=heated.rescue.options.find(option=>option.eligible&&option.dispatchable&&option.destination_id!=='D06');check('a second actual eligible recipient is available for explicit proposal selection',!!alternative);
  if(await lab().getByRole('button',{name:new RegExp('^Show all .* candidates and exclusions$')}).count())await lab().getByRole('button',{name:new RegExp('^Show all .* candidates and exclusions$')}).click();
  await selectOption(alternative);pending=nextPost(sessionPath('proposal'));await lab().getByRole('button',{name:'Prepare selected rescue',exact:true}).click();let selected=await bodyOf(await pending,'selected recipient proposal uses actual backend');await settled(selected);check('proposal is bound to selected recipient and sensor version',selected.rescue.proposed_destination_id===alternative.destination_id&&selected.version>heated.version&&selected.rescue.proposal_hash!==heated.rescue.proposal_hash);
  const target=selected.rescue.options.find(option=>option.destination_id==='D06');await selectOption(target);pending=nextPost(sessionPath('routes'));await lab().getByRole('button',{name:'Check road route',exact:true}).click();let routed=await bodyOf(await pending,'offline route check completes with a labeled estimate');await settled(routed);await save('actual-routed-proposal',routed);
  const routeOption=routed.rescue.options.find(option=>option.destination_id==='D06');check('route geometry and fallback provenance correspond to D06',routeOption.eligible&&routeOption.dispatchable&&routeOption.fallback&&routeOption.geometry.type==='LineString'&&same(routeOption.geometry.coordinates[0],routed.shipment.origin)&&same(routeOption.geometry.coordinates.at(-1),rescuedNode.coordinates));
  check('route and proposal still leave the operational network unchanged',same(await get('/api/network'),baselineNetwork)&&same(await get('/api/driver'),baselineAssignments));
  await lab().getByRole('heading',{name:'Automatic rescue search',exact:true}).scrollIntoViewIfNeeded();await capture('desktop-calculated-rescue-destination-and-map');
  const beforeSelectionPosts=result.post_requests.length;await selectOption(alternative);const exported=await exportCapture('captured-routed-experiment-export');const {captured_export,export_note,...captured}=exported;
  check('local destination selection cannot rewrite captured experiment export',captured_export===true&&same(captured,routed)&&result.post_requests.length===beforeSelectionPosts&&routed.rescue.proposed_destination_id==='D06');await selectOption(routeOption);
  phase='review_and_approval';await lab().getByRole('button',{name:'Review '+routeOption.destination_name,exact:true}).click();const review=lab().getByRole('region',{name:'Human rescue approval',exact:true});await review.waitFor();
  const approve=review.getByRole('button',{name:'Approve simulated rescue plan',exact:true});check('approval begins disabled',await approve.isDisabled());await review.getByRole('textbox',{name:'Reviewing dispatcher',exact:true}).fill('Freshness QA dispatcher');await review.getByRole('textbox',{name:'Reason for rescue approval',exact:true}).fill('Automated isolated QA: inspect the modeled quality, simulated receiving capacity and route limitations.');
  const checks=review.getByRole('checkbox');check('three independent review confirmations are required',await checks.count()===3);await checks.nth(0).check();await checks.nth(1).check();check('two confirmations cannot approve',await approve.isDisabled());await checks.nth(2).check();check('identified review plus all confirmations enables approval',await approve.isEnabled());
  await review.scrollIntoViewIfNeeded();await capture('desktop-three-part-human-rescue-review');pending=nextPost(sessionPath('approve'));await approve.click();const approval=await bodyOf(await pending,'actual human-reviewed simulated rescue commits');await lab().getByRole('region',{name:'Confirmed rescue receipt',exact:true}).waitFor();await save('actual-approved-rescue',approval);
  const approvedNetwork=await get('/api/network');const approvedAssignments=await get('/api/driver');const rescued=approvedAssignments.find(row=>row.id==='SH05');
  check('checked full plan changes SH05 to D06 after exactly one network revision',approval.receipt.network_revision===baselineNetwork.revision+1&&approvedNetwork.revision===approval.receipt.network_revision&&rescued?.destination==='D06'&&rescued.instruction.includes('Save the Load')&&rescued.freshness_rescue.session_id===sessionId);
  check('approval publishes exactly the independently checked assignment count',approvedAssignments.length===approval.receipt.assignments_count&&approvedAssignments.length===routed.rescue.plan_summary.assignments_count);
  check('holds recalls and eligibility are preserved across rescue approval',baselineNetwork.lots.every(lot=>{const current=approvedNetwork.lots.find(row=>row.id===lot.id);return current.held===lot.held&&current.recalled===lot.recalled&&current.eligible===lot.eligible&&current.shelf_life_hours<=lot.shelf_life_hours;}));
  const audit=await get('/api/audit');check('identified rescue approval is in the actual audit trail',audit.some(row=>row.action==='freshness_rescue_approve'&&row.actor==='Freshness QA dispatcher'));
  phase='driver_handoff';await lab().getByRole('button',{name:'Open approved driver assignments',exact:true}).click();await driver().waitFor();await driver().getByRole('heading',{name:rescuedNode.name,exact:true}).waitFor();
  check('driver handoff opens the exact rescued truck and shipment',(await driver().innerText()).includes('SH05')&&(await driver().locator('.drive-destination').innerText()).includes(truckId)&&!(await driver().locator('.drive-destination').innerText()).includes(originalNode.name));
  pending=nextPost('/api/drive/'+truckId+'/focus');await driver().getByRole('button',{name:'Confirm safely parked',exact:true}).click();const parked=await bodyOf(await pending,'driver explicitly confirms parked use');check('parked controls require a recorded confirmation',parked.interaction_allowed===true);
  await driver().getByRole('button',{name:/^Dispatch instructions/}).click();await driver().getByRole('heading',{name:'Dispatcher-approved trip instructions',exact:true}).waitFor();check('parked instructions contain the actual approved rescue destination',(await driver().locator('.driver-instruction').innerText()).includes('Save the Load: reviewed destination D06'));
  await driver().locator('.drive-detail-panel').scrollIntoViewIfNeeded();await capture('desktop-approved-rescue-driver-instructions');
  const beforeFurtherFrames=await get('/api/network');const assignmentsBeforeFurtherFrames=await get('/api/driver');
  phase='postapproval_new_reading';await nav().getByRole('button',{name:'Save the Load',exact:true}).click();await lab().getByRole('combobox',{name:'Open stored experiment',exact:true}).waitFor();pending=nextSession();await lab().getByRole('combobox',{name:'Open stored experiment',exact:true}).selectOption(sessionId);let current=await bodyOf(await pending,'stored approved sensor experiment reopens');await settled(current);await lab().getByRole('checkbox',{name:'Follow incoming readings every 5s',exact:true}).uncheck();
  check('reopened experiment retains its recorded approval',current.status==='approved'&&current.approval.selected_destination_id==='D06');
  const appended=await post(sessionPath('replay'),{expected_version:current.version,event:'normal'});await save('actual-new-postapproval-capture',appended);
  check('a new normal frame changes only the experimental version and requests review',appended.version===current.version+1&&appended.status==='review_required'&&appended.approval.sensor_version===current.approval.sensor_version&&appended.approval.network_revision===approval.receipt.network_revision);
  const beforeRejected=await database(isolated);await post(sessionPath('replay'),{expected_version:current.version,event:'normal'},409);check('actual stale-version HTTP409 preserves every isolated SQLite byte',same(beforeRejected,await database(isolated)));
  phase='actual_stale_ui_rejection';pending=nextPost(sessionPath('replay'));await lab().getByRole('button',{name:'Normal control',exact:true}).click();const rejected=await pending;check('stale visible UI also receives a real HTTP409',rejected.status()===409);await lab().getByRole('alert').getByText('Newer readings or network changes arrived.',{exact:false}).waitFor();check('stale UI failure is visible and blocks a repeat replay',await lab().getByRole('button',{name:'Normal control',exact:true}).isDisabled());
  phase='recover_latest_capture';pending=nextSession();await lab().getByRole('button',{name:'Reload this experiment',exact:true}).click();current=await bodyOf(await pending,'latest capture recovers from actual stale UI request');await settled(current);await lab().getByText('New readings require a fresh decision review.',{exact:true}).waitFor();
  check('historical decision receipt survives new telemetry',(await lab().getByRole('region',{name:'Confirmed rescue receipt',exact:true}).innerText()).includes('Previously recorded rescue decision'));
  await lab().getByRole('region',{name:'Confirmed rescue receipt',exact:true}).scrollIntoViewIfNeeded();await capture('desktop-new-reading-retains-approval-history');
  phase='continuous_capture_polling';await lab().getByRole('checkbox',{name:'Follow incoming readings every 5s',exact:true}).check();const poll=nextSession();const polledCapture=await post(sessionPath('replay'),{expected_version:current.version,event:'normal'});const polled=await bodyOf(await poll,'five-second follow mode reads incoming stored capture');await settled(polledCapture);
  check('follow mode receives the latest stored version without a browser mutation',polled.version===polledCapture.version&&polled.status==='review_required');await lab().getByRole('checkbox',{name:'Follow incoming readings every 5s',exact:true}).uncheck();
  check('new sensor frames cannot automatically reassign or hold any lot',same(await get('/api/network'),beforeFurtherFrames)&&same(await get('/api/driver'),assignmentsBeforeFurtherFrames));
  const readiness=await get('/api/readiness');const pendingTrip=readiness.assignments.find(row=>row.shipment_id==='SH05');check('readiness marks the persistent lot-source review outstanding',pendingTrip.reviews_required.includes('freshness_telemetry_review')&&pendingTrip.freshness_reviews.some(row=>row.session_id===sessionId&&row.context==='lot_quality_link'&&row.latest_version>row.approved_version));
  const driverReview=await get('/api/drive/'+truckId);check('driver snapshot carries a review advisory without fabricated sensor measurements',driverReview.freshness_reviews.some(row=>row.shipment_id==='SH05'&&row.session_id===sessionId&&row.quality_only===true)&&driverReview.assignments.some(row=>row.id==='SH05'&&row.destination==='D06')&&!driverReview.freshness_reviews.some(row=>'temperature_c' in row||'humidity_percent' in row));
  await save('actual-pending-readiness',readiness);await save('actual-driver-review-advisory',driverReview);
  phase='mobile';await page.setViewportSize({width:390,height:844});await lab().locator('.freshness-kpis').scrollIntoViewIfNeeded();await noOverflow('mobile quality clocks have no horizontal page overflow');await capture('mobile-freshness-clocks-and-review');
  await lab().getByRole('button',{name:/^(Open approved driver assignments|Inspect driver assignment context)$/}).click();await driver().waitFor();await driver().getByRole('heading',{name:rescuedNode.name,exact:true}).waitFor();
  await driver().getByRole('region',{name:'Freshness review advisory',exact:true}).waitFor();const lock=driver().getByRole('button',{name:'Lock for driving',exact:true});if(await lock.count()){pending=nextPost('/api/drive/'+truckId+'/focus');await lock.click();await bodyOf(await pending,'driver returns to locked focus');}
  await driver().getByRole('region',{name:'Freshness review advisory',exact:true}).scrollIntoViewIfNeeded();check('freshness advisory remains visual while interaction forms are locked',await driver().getByRole('button',{name:'Confirm safely parked',exact:true}).isVisible()&&await driver().locator('textarea').count()===0&&await driver().getByRole('button',{name:/^Report an issue/}).isDisabled());await noOverflow('mobile driver review advisory has no horizontal page overflow');await capture('mobile-locked-driver-freshness-advisory');
  phase='final_guards';check('all browser writes were explicitly allowlisted isolated workflow actions',result.post_requests.length>0&&result.post_requests.every(row=>row.allowed)&&result.blocked_requests.length===0);
  check('no unexpected JavaScript console local HTTP or request errors',result.page_errors.length===0&&result.console_errors.length===0&&result.http_failures.length===0&&result.request_failures.length===0,JSON.stringify({page:result.page_errors,console:result.console_errors,http:result.http_failures,requests:result.request_failures}));
  result.operator_after=await database(path.join(root,'data/aegis.sqlite'));result.raw_after=await originals();result.fixtures_after=await tree('data/fixtures');result.cache_after=await tree('data/cache');result.isolated_after=await database(isolated);
  check('operator database and every sidecar remain untouched',same(result.operator_before,result.operator_after));check('inventoried original bytes and manifest remain untouched',same(result.raw_before,result.raw_after));check('source fixtures and caches remain untouched',same(result.fixtures_before,result.fixtures_after)&&same(result.cache_before,result.cache_after));
  result.final_network=await get('/api/network');result.final_assignments=await get('/api/driver');check('all postapproval monitoring retains the reviewed operational assignment',same(result.final_network,beforeFurtherFrames)&&same(result.final_assignments,assignmentsBeforeFurtherFrames));result.passed=true;
}catch(error){result.passed=false;result.failure={phase,message:error.stack||String(error)};if(page)await page.screenshot({path:path.join(folder,'failure.png'),fullPage:false}).catch(()=>{});process.exitCode=1;}
finally{if(!result.operator_after)result.operator_after=await database(path.join(root,'data/aegis.sqlite'));if(isolated&&!result.isolated_after)result.isolated_after=await database(isolated);result.finished_at=new Date().toISOString();await save('results',result);await browser?.close();console.log(JSON.stringify({passed:result.passed,checks:result.checks.length,failed:result.checks.filter(row=>!row.passed),failure:result.failure,screenshots:result.screenshots.length,report:'reports/browser_qa/freshness/results.json'},null,2));}
