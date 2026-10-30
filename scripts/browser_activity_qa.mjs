/** Actual Chrome activity-history checks. Mutations are confined to a verified
 * isolated/offline QA server on 8016. Corrupt/oversized SQL rows and one browser
 * 409 response are explicitly labeled injected fixtures, not real actions.
 */
import fs from 'node:fs/promises';
import { createReadStream } from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';
import { chromium } from '../.tools/browser-qa/node_modules/playwright-core/index.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const base='http://127.0.0.1:8016';
const folder=path.join(root,'reports/browser_qa/activity');
const downloads=path.join(root,'.tools/activity-browser-downloads');
const launch=JSON.parse((await fs.readFile(path.join(root,'.tools/activity-qa-launch.json'),'utf8')).replace(/^\uFEFF/,''));
if(launch.port!==8016||launch.environment.AEGIS_OFFLINE_DEMO!=='1')throw new Error('Expected reserved isolated offline 8016 session');
const operator=path.join(root,'data/aegis.sqlite');const isolated=path.resolve(launch.database_path);
if(isolated===operator||!isolated.startsWith(path.join(root,'data/rehearsals')+path.sep))throw new Error('Refusing unsafe QA database path');
await fs.mkdir(folder,{recursive:true});await fs.mkdir(downloads,{recursive:true});
const canonical=value=>JSON.stringify(value,(_key,item)=>item&&typeof item==='object'&&!Array.isArray(item)?Object.fromEntries(Object.keys(item).sort().map(key=>[key,item[key]])):item);
const same=(left,right)=>canonical(left)===canonical(right);
const save=(name,value)=>fs.writeFile(path.join(folder,name+'.json'),JSON.stringify(value,null,2)+'\n');
async function fingerprint(filename){try{const stat=await fs.stat(filename);const hash=createHash('sha256');for await(const chunk of createReadStream(filename))hash.update(chunk);return{exists:true,bytes:stat.size,sha256:hash.digest('hex')};}catch(error){if(error.code==='ENOENT')return{exists:false};throw error;}}
async function database(filename){return Object.fromEntries(await Promise.all(['','-wal','-shm','-journal'].map(async suffix=>[suffix||'sqlite',await fingerprint(filename+suffix)])));}
async function tree(relative){const found={};async function visit(directory){let entries;try{entries=await fs.readdir(directory,{withFileTypes:true});}catch(error){if(error.code==='ENOENT')return;throw error;}for(const entry of entries){const filename=path.join(directory,entry.name);if(entry.isDirectory())await visit(filename);else if(entry.isFile())found[path.relative(root,filename).replaceAll('\\','/')]=await fingerprint(filename);else if(entry.isSymbolicLink())found[path.relative(root,filename).replaceAll('\\','/')]={symlink_not_followed:true};}}await visit(path.join(root,relative));return found;}
const result={checked_at:new Date().toISOString(),base_url:base,isolated:true,offline:true,rehearsal_id:launch.rehearsal_id,actual_llm_queried:false,source_refresh_requested:false,actual_osrm_queried:false,checks:[],screenshots:[],page_errors:[],console_errors:[],http_failures:[],expected_injected_failures:[],allowed_external_tile_failures:[],browser_activity_requests:[],browser_post_requests:[],control_requests:[],fixture_injections:[]};
const check=(name,passed,detail='')=>{result.checks.push({name,passed,detail});if(!passed)throw new Error(`${name}: ${detail}`);};
let browser,context,page,phase='startup';
const fixtureCode=`import json,sqlite3,sys
from pathlib import Path
q=json.load(sys.stdin);root=Path.cwd().resolve();p=Path(q['database']).resolve()
assert p.parent==(root/'data/rehearsals').resolve() and p.stem==q['session']
with sqlite3.connect(p) as c:
 rows=[]
 for action,payload in [('qa_fixture_corrupt_payload','{not-json'),('qa_fixture_oversized_payload',json.dumps({'padding':'x'*33000}))]:
  cur=c.execute('INSERT INTO audit(timestamp,actor,action,payload) VALUES (?,?,?,?)',('2026-10-29 20:00:00','Injected QA fixture; not a human action',action,payload));rows.append({'id':cur.lastrowid,'action':action})
 print(json.dumps(rows))`;
async function insertEvidenceFixtures(){return new Promise((resolve,reject)=>{const child=spawn(path.join(root,'.venv/Scripts/python.exe'),['-c',fixtureCode],{cwd:root,windowsHide:true,stdio:['pipe','pipe','pipe']});let output='',errors='';child.stdout.on('data',body=>output+=body);child.stderr.on('data',body=>errors+=body);child.on('error',reject);child.on('close',code=>code===0?resolve(JSON.parse(output)):reject(new Error(errors)));child.stdin.end(JSON.stringify({database:isolated,session:launch.rehearsal_id}));});}
try{
  result.operator_database_before=await database(operator);result.fixtures_before=await tree('data/fixtures');result.cache_before=await tree('data/cache');
  browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});result.browser_version=browser.version();
  context=await browser.newContext({viewport:{width:1440,height:1050},locale:'en-US',timezoneId:'America/Chicago',acceptDownloads:true});
  const request=async(endpoint,body,expected=200)=>{if(!endpoint.startsWith('/api/'))throw new Error('Only local app API requests permitted');const reply=body===undefined?await context.request.get(base+endpoint):await context.request.post(base+endpoint,{data:body});result.control_requests.push({phase,endpoint,method:body===undefined?'GET':'POST',status:reply.status()});check(`${phase}: control ${endpoint}`,reply.status()===expected,`HTTP ${reply.status()}`);return reply.json();};
  const runtime=await request('/api/runtime-context');result.runtime=runtime;
  check('verified isolated offline runtime',runtime.isolated===true&&runtime.offline===true&&runtime.mode==='isolated_rehearsal'&&runtime.rehearsal_id===launch.rehearsal_id&&runtime.database_relative_path===launch.database_relative_path);
  phase='seed_recorded_actions';result.isolated_setup_reset=await request('/api/demo/reset',{});
  // Repeated simulator settings deliberately exercise pagination; they are not
  // independent physical observations or a count of real disruptions.
  for(let index=0;index<24;index++)await request('/api/events',{event:'temperature_excursion',shipment_id:index%2?'SH11':'SH12'});
  const proposal=await request('/api/proposals/A',{});check('actual plan is feasible before approval',proposal.feasible&&proposal.shipments.length>0);
  await request(`/api/proposals/${proposal.id}/approve`,{actor:'Activity QA dispatcher',reason:'Explicit isolated activity-history verification; modeled constraints reviewed'});
  const network=await request('/api/network');const assignments=await request('/api/driver');check('actual approval creates simulated assignments',assignments.length>0);
  const assignment=assignments[0];const drive=await request('/api/drive/'+assignment.truck_id);
  await request('/api/drive/'+assignment.truck_id+'/focus',{mode:'parked',expected_version:drive.focus.version,parked_confirmation:true});
  await request('/api/driver/'+assignment.id+'/acknowledge',{expected_network_revision:network.revision});
  await request('/api/drive/'+assignment.truck_id+'/quick-report',{shipment_id:assignment.id,kind:'road_delay',expected_network_revision:network.revision});
  const instruction=await request('/api/dispatch/assignments/'+assignment.id+'/instruction',{actor:'Activity QA dispatcher',reason:'Exercise recorded instruction and acknowledgment in isolated parked use',instruction:'Remain safely parked for the isolated QA review; no automatic reroute.',expected_instruction_revision:assignment.instruction_revision??0,expected_network_revision:network.revision});
  await request('/api/driver/'+assignment.id+'/instruction-ack',{instruction_revision:instruction.instruction_revision});
  result.fixture_injections=await insertEvidenceFixtures();await save('injected-evidence-row-identities',result.fixture_injections);
  const all=await request('/api/activity?limit=100');await save('actual-initial-history',all);
  check('actual internal actions cover paging and multiple workflows',all.total_matching>25&&['event','approve','driver_focus','acknowledge','incident','driver_quick_report','dispatcher_instruction','instruction_acknowledge'].every(action=>all.records.some(row=>row.action===action)));
  result.isolated_history_only_before=await database(isolated);
  page=await context.newPage();page.setDefaultTimeout(20000);
  page.on('pageerror',error=>result.page_errors.push({phase,message:error.message}));
  page.on('console',message=>{if(message.type()!=='error')return;const item={phase,message:message.text(),location:message.location()};if(item.location.url.includes('tile.openstreetmap.org'))result.allowed_external_tile_failures.push(item);else if(phase==='injected_paging_failure'&&item.message.includes('409'))result.expected_injected_failures.push(item);else result.console_errors.push(item);});
  page.on('request',request=>{const url=new URL(request.url());if(url.origin===base&&request.method()==='POST')result.browser_post_requests.push({phase,path:url.pathname});if(url.origin===base&&url.pathname==='/api/activity')result.browser_activity_requests.push({phase,path:url.pathname+url.search,method:request.method()});});
  page.on('response',reply=>{if(reply.status()<400)return;const item={phase,url:reply.url(),status:reply.status()};if(reply.url().includes('tile.openstreetmap.org'))result.allowed_external_tile_failures.push(item);else if(phase==='injected_paging_failure'&&reply.url().includes('/api/activity')&&reply.status()===409)result.expected_injected_failures.push(item);else if(reply.url().startsWith(base))result.http_failures.push(item);});
  const nav=()=>page.getByRole('navigation',{name:'Main navigation'});
  const panel=()=>page.getByRole('region',{name:'Activity history',exact:true});
  const nextActivity=()=>page.waitForResponse(reply=>reply.url().startsWith(base+'/api/activity?')&&reply.request().method()==='GET');
  const rows=async()=>panel().getByRole('article').evaluateAll(items=>items.map(item=>Number(item.getAttribute('aria-label').replace('Audit record ',''))));
  const capture=async name=>{await page.screenshot({path:path.join(folder,name+'.png'),fullPage:false});result.screenshots.push(name+'.png');};
  const overflow=async name=>check(name,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  const open=async()=>{const pending=nextActivity();await page.getByRole('button',{name:'Open activity history',exact:true}).click();const reply=await pending;check('actual activity UI response',reply.ok());const body=await reply.json();await panel().getByText(`${body.records.length} of ${body.total_matching} matching records loaded`,{exact:true}).waitFor();return body;};
  const filter=async(action,shipment='')=>{await panel().getByRole('combobox',{name:'Recorded action'}).selectOption(action);await panel().getByRole('textbox',{name:'Explicit shipment ID'}).fill(shipment);const waiting=nextActivity();await panel().getByRole('button',{name:'Apply activity filters',exact:true}).click();const reply=await waiting;check('filter response uses actual API',reply.ok());const body=await reply.json();await panel().getByText(`${body.records.length} of ${body.total_matching} matching records loaded`,{exact:true}).waitFor();return body;};
  const exportPage=async name=>{const waiting=page.waitForEvent('download');await panel().getByRole('button',{name:'Export captured activity JSON',exact:true}).click();const download=await waiting;const target=path.join(downloads,name+'.json');await download.saveAs(target);const body=JSON.parse(await fs.readFile(target,'utf8'));await save(name,body);return body;};
  phase='desktop_history';await page.goto(base+'/',{waitUntil:'domcontentloaded'});await page.getByRole('combobox',{name:'Select shipment',exact:true}).waitFor();
  result.served_assets={scripts:await page.locator('script[type="module"][src]').evaluateAll(items=>items.map(item=>item.getAttribute('src'))),styles:await page.locator('link[rel="stylesheet"][href]').evaluateAll(items=>items.map(item=>item.getAttribute('href')))};
  check('history does not add a tenth workspace',(await nav().getByRole('button').count())===9);
  const initial=await open();await save('actual-first-browser-page',initial);check('displayed first page exactly matches captured API IDs',same(await rows(),initial.records.map(row=>row.id)));
  check('history explains identity and missing recorded actions',(await panel().innerText()).includes('self-declared, not authenticated identities')&&(await panel().innerText()).includes('empty history does not mean a button failed'));
  await panel().scrollIntoViewIfNeeded();await overflow('desktop history has no page overflow');await capture('desktop-captured-activity');
  const beforeReopenRequests=result.browser_activity_requests.length;await page.locator('#command-scenarios').scrollIntoViewIfNeeded();await page.getByRole('button',{name:'Open activity history',exact:true}).click();
  await page.waitForFunction(()=>{const node=document.getElementById('activity-history');return node&&node.getBoundingClientRect().top>=0&&node.getBoundingClientRect().top<300;},{},{timeout:5000});
  check('reopening visible history refocuses it without silently refreshing',result.browser_activity_requests.length===beforeReopenRequests&&same(await rows(),initial.records.map(row=>row.id)));
  for(const injected of result.fixture_injections){const row=panel().getByRole('article',{name:`Audit record ${injected.id}`,exact:true});await row.locator('summary').click();check('injected evidence row remains explicitly inspectable '+injected.id,(await row.innerText()).includes('Injected QA fixture; not a human action')&&(await row.innerText()).includes('Payload unavailable')&&(await row.innerText()).includes('Time not verified'));check('internal citation preserves exact row identity '+injected.id,(await row.innerText()).includes('audit/'+injected.id));}
  const oversized=panel().getByRole('article',{name:`Audit record ${result.fixture_injections[1].id}`,exact:true});check('oversized evidence labels prefix rather than full hash',(await oversized.innerText()).includes('Inspected prefix SHA-256 (not the full payload)'));await oversized.scrollIntoViewIfNeeded();await capture('desktop-unreadable-record-evidence');
  const beforeDraftRequests=result.browser_activity_requests.length;await panel().getByRole('combobox',{name:'Recorded action'}).selectOption('approve');
  check('draft filter does not change captured rows or call API',same(await rows(),initial.records.map(row=>row.id))&&result.browser_activity_requests.length===beforeDraftRequests&&await panel().getByRole('button',{name:'Load older activity',exact:true}).isDisabled());
  const draftExport=await exportPage('actual-draft-filter-export');check('export retains captured filters instead of edited draft',same(draftExport.filters,{action:'',shipment:''})&&same(draftExport.pages[0],initial));
  const approvalOnly=await filter('approve');check('actual action filter shows only recorded approvals',approvalOnly.records.length>0&&approvalOnly.records.every(row=>row.action==='approve')&&same(await rows(),approvalOnly.records.map(row=>row.id)));
  await panel().scrollIntoViewIfNeeded();await capture('desktop-approved-action-filter');
  const shipmentOnly=await filter('',assignment.id);check('actual shipment filter never infers global approval rows',shipmentOnly.records.length>0&&shipmentOnly.records.every(row=>row.explicit_shipment_id===assignment.id)&&!shipmentOnly.records.some(row=>row.action==='approve'));
  const requestsBeforeInvalid=result.browser_activity_requests.length;await panel().getByRole('textbox',{name:'Explicit shipment ID'}).fill('../invalid?');check('invalid shipment filter blocks request',await panel().getByRole('button',{name:'Apply activity filters',exact:true}).isDisabled()&&result.browser_activity_requests.length===requestsBeforeInvalid);
  const empty=await filter('','SH-NOT-RECORDED');check('valid empty filter is an explicit empty captured result',empty.records.length===0&&empty.total_matching===0&&(await panel().innerText()).includes('No recorded actions match'));
  const fresh=await filter('');check('reset filters produce a fresh bounded page',fresh.records.length===25);
  result.isolated_history_only_after=await database(isolated);check('opening details filtering and exporting history do not change isolated DB or sidecars',same(result.isolated_history_only_before,result.isolated_history_only_after));
  phase='stable_snapshot';const beforeNew=fresh;await request('/api/events',{event:'temperature_excursion',shipment_id:'SH11'});const afterNew=await request('/api/activity?limit=100');result.newer_action={before_latest:beforeNew.snapshot_latest_id,after_latest:afterNew.snapshot_latest_id};check('a deliberately recorded newer action exists outside captured snapshot',afterNew.snapshot_latest_id>beforeNew.snapshot_latest_id);
  const beforePaging=await database(isolated);let waiting=nextActivity();await panel().getByRole('button',{name:'Load older activity',exact:true}).click();let reply=await waiting;check('actual older page is available',reply.ok());const older=await reply.json();const expectedIds=[...beforeNew.records,...older.records].map(row=>row.id);
  await panel().getByText(`${expectedIds.length} of ${beforeNew.total_matching} matching records loaded`,{exact:true}).waitFor();check('older page remains in original snapshot and excludes newer IDs',older.snapshot_id===beforeNew.snapshot_id&&older.snapshot_latest_id===beforeNew.snapshot_latest_id&&same(await rows(),expectedIds)&&expectedIds.every(id=>id<=beforeNew.snapshot_latest_id));
  const snapshotExport=await exportPage('actual-two-page-snapshot-export');check('two-page export exactly preserves both API pages',same(snapshotExport.pages,[beforeNew,older]));check('older paging and snapshot export preserve SQLite/sidecars',same(beforePaging,await database(isolated)));
  waiting=nextActivity();await panel().getByRole('button',{name:'Refresh activity',exact:true}).click();reply=await waiting;const refreshed=await reply.json();await panel().getByText(`${refreshed.records.length} of ${refreshed.total_matching} matching records loaded`,{exact:true}).waitFor();check('explicit refresh captures the newer recorded action',refreshed.snapshot_latest_id===afterNew.snapshot_latest_id&&refreshed.snapshot_id!==beforeNew.snapshot_id&&same(await rows(),refreshed.records.map(row=>row.id)));
  phase='injected_paging_failure';result.fixture_injections.push({kind:'browser_injected_409',description:'Explicitly injected paging failure tests retained captured UI and reload recovery; the actual captured SQL rows were not edited.'});
  await page.route('**/api/activity?*',async route=>{if(new URL(route.request().url()).searchParams.has('cursor'))await route.fulfill({status:409,contentType:'application/json',body:JSON.stringify({detail:'Injected fixture: captured activity changed; reload'})});else await route.continue();});
  waiting=nextActivity();await panel().getByRole('button',{name:'Load older activity',exact:true}).click();reply=await waiting;check('expected browser-injected conflict delivered',reply.status()===409);await panel().getByRole('alert').waitFor();check('failure keeps captured rows and blocks stale paging',same(await rows(),refreshed.records.map(row=>row.id))&&await panel().getByRole('button',{name:'Load older activity',exact:true}).isDisabled()&&(await panel().getByRole('alert').innerText()).includes('previous captured records remain'));
  await panel().getByRole('alert').scrollIntoViewIfNeeded();await capture('desktop-visible-captured-history-conflict');await page.unroute('**/api/activity?*');
  phase='recover_snapshot';waiting=nextActivity();await panel().getByRole('button',{name:'Refresh activity',exact:true}).click();reply=await waiting;check('explicit history recovery uses actual endpoint',reply.ok());await panel().getByRole('alert').waitFor({state:'hidden'});check('refresh restores pagination after failure',await panel().getByRole('button',{name:'Load older activity',exact:true}).isEnabled());
  phase='navigation';const explicit=await filter('',assignment.id);const linked=explicit.records.find(row=>row.explicit_shipment_id===assignment.id);check('there is an actual explicit shipment link',!!linked);
  const postsBeforeNav=result.browser_post_requests.length;await panel().getByRole('article',{name:`Audit record ${linked.id}`,exact:true}).getByRole('button',{name:'Inspect shipment '+assignment.id,exact:true}).click();await panel().waitFor({state:'hidden'});check('shipment link selects the current candidate in Command',await page.getByRole('combobox',{name:'Select shipment',exact:true}).inputValue()===assignment.id);
  await open();const instructions=await filter('dispatcher_instruction');check('actual instruction history exists',instructions.records.length>0);await panel().getByRole('article',{name:`Audit record ${instructions.records[0].id}`,exact:true}).getByRole('button',{name:'Open Dispatcher desk',exact:true}).click();await panel().waitFor({state:'hidden'});await page.getByRole('heading',{name:'Turn reports into reviewed action',exact:true}).waitFor();check('activity navigation is inspection only',result.browser_post_requests.length===postsBeforeNav);
  const sidebarTitles=['Command center','Route laboratory','Road intelligence','Dispatcher desk','Sources & evidence','Model evaluation','Evidence assistant','Project brief','AEGIS Drive'];
  for(const title of sidebarTitles){await nav().getByRole('button',{name:title,exact:true}).click();check(title+' retains the shared history entry point',await page.getByRole('button',{name:'Open activity history',exact:true}).isVisible());}
  phase='mobile';await nav().getByRole('button',{name:'Command center',exact:true}).click();await page.setViewportSize({width:390,height:844});await open();await panel().scrollIntoViewIfNeeded();await overflow('mobile history has no page overflow');await capture('mobile-captured-activity');
  const mobile=await filter('dispatcher_instruction');const mobileRow=panel().getByRole('article',{name:`Audit record ${mobile.records[0].id}`,exact:true});await mobileRow.locator('summary').click();await mobileRow.scrollIntoViewIfNeeded();await overflow('mobile evidence detail remains inside page');await capture('mobile-instruction-evidence');
  const mobileExport=await exportPage('actual-mobile-filter-export');check('mobile export retains actual filtered record payloads',same(mobileExport.pages[0],mobile));const postsBeforeClose=result.browser_post_requests.length;await panel().getByRole('button',{name:'Close activity history',exact:true}).click();await panel().waitFor({state:'hidden'});check('history close is a visibility change only',await page.getByRole('button',{name:'Open activity history',exact:true}).isVisible()&&result.browser_post_requests.length===postsBeforeClose);
  phase='dedicated_drive';await page.goto(base+'/?mode=drive',{waitUntil:'domcontentloaded'});await page.getByRole('region',{name:'AEGIS Drive workspace',exact:true}).waitFor();check('dedicated parked-use Drive has no history/header distraction',await page.getByRole('button',{name:'Open activity history',exact:true}).count()===0&&await nav().count()===0);await overflow('dedicated Drive still has no page overflow');
  phase='final_guards';result.operator_database_after=await database(operator);result.fixtures_after=await tree('data/fixtures');result.cache_after=await tree('data/cache');result.isolated_database_after=await database(isolated);
  check('operator database and every sidecar unchanged',same(result.operator_database_before,result.operator_database_after));check('dated fixtures unchanged',same(result.fixtures_before,result.fixtures_after));check('public source cache unchanged',same(result.cache_before,result.cache_after));
  check('all browser history calls are GET',result.browser_activity_requests.length>0&&result.browser_activity_requests.every(row=>row.method==='GET'));check('history browsing navigation and exports issue zero browser operational POSTs',result.browser_post_requests.length===0,JSON.stringify(result.browser_post_requests));
  check('no source refresh model or routing controls requested',!result.control_requests.some(row=>/refresh|assistant\/interpret|route-lab|\/api\/route$/.test(row.endpoint)));
  check('no uncaught browser JavaScript errors',result.page_errors.length===0,JSON.stringify(result.page_errors));check('no unexpected application HTTP failures',result.http_failures.length===0,JSON.stringify(result.http_failures));check('no unexpected console errors',result.console_errors.length===0,JSON.stringify(result.console_errors));result.passed=true;
}catch(error){result.passed=false;result.error={phase,message:error.message,stack:error.stack};if(page)await page.screenshot({path:path.join(folder,'failure.png'),fullPage:false}).catch(()=>{});}
finally{if(browser)await browser.close();result.finished_at=new Date().toISOString();await save('results',result);}
console.log(JSON.stringify({passed:result.passed,checks:result.checks.length,screenshots:result.screenshots.length,error:result.error,page_errors:result.page_errors.length,http_failures:result.http_failures.length,console_errors:result.console_errors.length}));
if(!result.passed)process.exitCode=1;
