/** Actual Chrome QA of read-only cross-state road evidence.
 * Requires a verified isolated OFFLINE rehearsal server (default port 8002).
 * Never refreshes providers or changes operational state. Injected browser-only
 * failure responses are reported separately from actual application responses.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {chromium} from '../.tools/browser-qa/node_modules/playwright-core/index.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const base=process.env.AEGIS_QA_BASE_URL||'http://127.0.0.1:8002';
const parsedBase=new URL(base);
if(parsedBase.hostname!=='127.0.0.1'||parsedBase.protocol!=='http:'||['','8000'].includes(parsedBase.port))throw new Error('Use an isolated loopback QA server, never operator port 8000');
const folder=path.join(root,'reports/browser_qa/roads');
await fs.mkdir(folder,{recursive:true});
const result={checked_at:new Date().toISOString(),base_url:base,public_refresh_requested:false,checks:[],page_errors:[],http_failures:[],expected_injected_http_failures:[],resource_failures:[],post_requests:[],screenshots:[],injected_cases:[]};
const hash=body=>createHash('sha256').update(body).digest('hex');
const canonical=value=>JSON.stringify(value,(_key,item)=>item&&typeof item==='object'&&!Array.isArray(item)?Object.fromEntries(Object.keys(item).sort().map(key=>[key,item[key]])):item);
const check=(name,passed,detail='')=>{result.checks.push({name,passed,detail});if(!passed)throw new Error(`${name}: ${detail}`);};
async function fingerprint(filename){try{const body=await fs.readFile(filename);return{exists:true,bytes:body.length,sha256:hash(body)};}catch(error){if(error.code==='ENOENT')return{exists:false};return{exists:null,error:String(error)};}}
async function fixtures(){return Object.fromEntries(await Promise.all(['modot','iowa_dot'].map(async name=>[name,await fingerprint(path.join(root,'data/fixtures',name+'.json'))])));}
async function database(filename){return Object.fromEntries(await Promise.all(['','-wal','-shm','-journal'].map(async suffix=>[suffix||'sqlite',await fingerprint(filename+suffix)])))}
let browser,page,phase='actual',dbPath,fixtureBefore,dbBefore;
try{
  browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
  result.browser_version=browser.version();
  const context=await browser.newContext({viewport:{width:1440,height:1000},timezoneId:'America/Chicago',locale:'en-US',acceptDownloads:true});
  const get=async endpoint=>{const response=await context.request.get(base+endpoint);if(!response.ok())throw new Error(`${endpoint}: HTTP ${response.status()}`);return response.json();};
  const runtime=await get('/api/runtime-context');result.runtime=runtime;
  check('server_is_verified_isolated_offline_rehearsal',runtime.mode==='isolated_rehearsal'&&runtime.isolated===true&&runtime.offline===true&&typeof runtime.rehearsal_id==='string');
  const relative=runtime.database_relative_path;
  dbPath=path.resolve(root,relative||'');
  check('runtime_database_is_under_rehearsals',typeof relative==='string'&&dbPath.startsWith(path.join(root,'data/rehearsals')+path.sep)&&path.basename(dbPath)===runtime.rehearsal_id+'.sqlite');
  // Initialize the dedicated server's normal read paths before the immutable
  // comparison baseline. No reset, assignment or inventory action is performed.
  const networkBefore=await get('/api/network');const driverBefore=await get('/api/driver');
  fixtureBefore=await fixtures();dbBefore=await database(dbPath);
  check('both_dated_official_fixture_files_present',Object.values(fixtureBefore).every(item=>item.exists===true&&/^[a-f0-9]{64}$/.test(item.sha256)));
  const snapshot=await get('/api/road-intelligence');
  check('actual_snapshot_has_separate_missouri_and_iowa_sources',snapshot.offline===true&&snapshot.sources.length===2&&snapshot.sources.some(item=>item.id==='modot'&&item.state==='MO')&&snapshot.sources.some(item=>item.id==='iowa_dot'&&item.state==='IA'));
  const iowa=snapshot.sources.find(item=>item.id==='iowa_dot');result.iowa_snapshot={event_count:iowa.event_count,listed_events:iowa.events.length,query_summary:iowa.query_summary,retrieved_at:iowa.retrieved_at};
  check('iowa_fixture_is_available_dated_and_stale',iowa.available===true&&iowa.fixture===true&&iowa.stale===true&&iowa.event_count===599);
  check('preview_bound_does_not_erase_captured_records',iowa.events.length===200&&iowa.events_truncated===true&&iowa.query_summary.returned_records===599);
  check('iowa_record_identity_does_not_collapse_repeated_cars_ids',new Set(iowa.events.map(item=>item.id)).size===iowa.events.length&&Object.keys(iowa.query_summary.duplicate_cars_event_ids).length===294);
  page=await context.newPage();page.setDefaultTimeout(20000);
  page.on('pageerror',error=>result.page_errors.push({phase,error:error.message}));
  page.on('response',response=>{if(response.url().startsWith(base)&&response.status()>=400){const item={phase,url:response.url(),status:response.status()};if(phase==='injected_http_failure')result.expected_injected_http_failures.push(item);else result.http_failures.push(item);}});
  page.on('requestfailed',request=>{if(!request.url().startsWith(base))result.resource_failures.push({url:request.url(),reason:request.failure()?.errorText});});
  page.on('request',request=>{if(request.method()==='POST')result.post_requests.push({phase,url:request.url(),path:new URL(request.url()).pathname});});
  const capture=async name=>{await page.screenshot({path:path.join(folder,name+'.png'),fullPage:false});result.screenshots.push(name+'.png');};
  const align=async locator=>locator.evaluate(element=>element.scrollIntoView({block:'start'}));
  const noOverflow=async name=>{const size=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth}));check(name,size.document<=size.viewport,JSON.stringify(size));};
  const workspace=()=>page.getByRole('region',{name:'Road intelligence workspace',exact:true});
  const compareButton=()=>workspace().getByRole('button',{name:'Compare planning routes',exact:true});
  const loadButton=()=>workspace().getByRole('button',{name:'Recheck saved road evidence',exact:true});
  const waitIdle=async()=>page.waitForFunction(()=>{const button=[...document.querySelectorAll('.road-toolbar button')].find(item=>item.textContent.includes('Recheck saved road evidence'));return button&&!button.disabled;});
  const loadSaved=async()=>{const pending=page.waitForResponse(response=>response.url()===base+'/api/road-intelligence'&&response.request().method()==='GET');await loadButton().click();const response=await pending;await waitIdle();return response;};
  const compare=async()=>{const pending=page.waitForResponse(response=>response.url()===base+'/api/road-intelligence/compare'&&response.request().method()==='POST');await compareButton().click();const response=await pending;check('actual_compare_HTTP_success',response.ok(),`HTTP ${response.status()}`);const output=await response.json();await waitIdle();await workspace().getByRole('heading',{name:'Alternative review',exact:true}).waitFor();return output;};
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.getByRole('button',{name:'Road intelligence',exact:true}).click();
  await workspace().getByRole('heading',{name:'Road evidence, before the next decision.',exact:true}).waitFor();await waitIdle();
  check('navigation_opens_real_road_workspace',await workspace().isVisible());
  check('offline_provider_refresh_is_disabled',await workspace().getByRole('button',{name:'Refresh official road feeds',exact:true}).isDisabled());
  check('fixture_and_read_only_labels_visible',(await workspace().innerText()).includes('DATED FIXTURE')&&(await workspace().innerText()).includes('READ-ONLY PLANNING'));
  check('source_cards_show_both_official_providers',await workspace().locator('.road-source-card').count()===2&&(await workspace().innerText()).includes('599'));
  const iowaCard=workspace().locator('.road-source-card').filter({has:page.getByRole('heading',{name:'Iowa DOT 511 events',exact:true})});
  check('source_attribution_and_licenses_are_actual_links',(await iowaCard.getByRole('link',{name:'Data license',exact:true}).getAttribute('href'))==='https://creativecommons.org/licenses/by/4.0/'&&(await iowaCard.getByRole('link',{name:'Provider terms',exact:true}).getAttribute('href'))===iowa.terms_url);
  await iowaCard.getByRole('button',{name:'Inspect IA events',exact:false}).click();
  check('source_inspect_button_selects_iowa',await workspace().getByLabel(/^Official road feed/).inputValue()==='iowa_dot');
  const event=iowa.events[0];
  await workspace().getByLabel('Filter captured road events',{exact:true}).fill(event.id);
  const eventButton=workspace().locator('.road-event-row').first();await eventButton.focus();await page.keyboard.press('Enter');
  const detail=workspace().getByRole('article',{name:'Road event detail',exact:true});
  await detail.getByRole('heading',{name:event.title,exact:true}).waitFor();
  check('event_can_be_selected_with_keyboard',(await detail.innerText()).includes(event.id));
  await detail.getByText('Original provider fields',{exact:true}).click();
  check('original_fields_match_actual_fixture',JSON.parse(await detail.locator('pre').last().innerText()).OBJECTID===event.properties.OBJECTID);
  if(event.provider_times&&Object.keys(event.provider_times).length){await detail.getByText('Original provider time values',{exact:true}).click();check('literal_provider_times_match_actual_fixture',canonical(JSON.parse(await detail.locator('pre').first().innerText()))===canonical(event.provider_times));}
  check('unverified_event_timestamps_are_not_fabricated',(await detail.innerText()).includes('Not supplied')&&event.updated_at===null&&event.starts_at===null&&event.ends_at===null);
  await align(detail);await capture('desktop-iowa-provider-record');
  await workspace().getByLabel('Filter captured road events',{exact:true}).fill('NO-SUCH-EVENT-ROAD-QA');
  check('empty_filter_preserves_selected_record_without_clear_road_claim',await workspace().locator('.road-event-row').count()===0&&(await detail.innerText()).includes(event.id));
  await workspace().getByLabel(/^Official road feed/).selectOption('modot');
  check('empty_filter_message_does_not_claim_clear_roads',(await workspace().innerText()).includes('This does not establish clear roads or full coverage.'));
  await workspace().getByLabel('Filter captured road events',{exact:true}).fill('');
  await workspace().getByLabel(/^Official road feed/).selectOption('iowa_dot');
  await workspace().getByLabel(/^Planning corridor/).selectOption('iowa-corridor');
  check('cross_state_preset_uses_verified_coordinate_order',await workspace().getByLabel('Origin longitude',{exact:true}).inputValue()==='-92.3341'&&await workspace().getByLabel('Destination latitude',{exact:true}).inputValue()==='41.5868');
  await workspace().getByLabel('Origin latitude',{exact:true}).fill('91');check('invalid_latitude_prevents_comparison',await compareButton().isDisabled());
  await workspace().getByLabel(/^Planning corridor/).selectOption('iowa-corridor');
  await workspace().getByLabel('Event proximity buffer (meters)',{exact:true}).fill('49');check('invalid_buffer_prevents_comparison',await compareButton().isDisabled());
  await workspace().getByLabel('Event proximity buffer (meters)',{exact:true}).fill('250');
  const first=await compare();result.actual_comparison_sha256=hash(canonical(first));
  check('routing_metadata_fields_are_explicit_and_typed',typeof first.routing_stale==='boolean'&&typeof first.routing_cache==='boolean'&&typeof first.routing_provenance==='string'&&'routing_retrieved_at'in first&&'routing_refresh_error'in first);
  check('estimated_comparison_is_an_explicit_straight_connection',first.request.routing==='estimated'&&first.alternatives.length===1&&first.alternatives[0].fallback===true&&first.alternatives[0].geometry.type==='LineString'&&first.alternatives[0].geometry.coordinates.length===2);
  check('both_sources_independently_screened',first.alternatives[0].reviews.length===2&&first.alternatives[0].reviews.every(item=>['modot','iowa_dot'].includes(item.source_id)&&item.stale===true));
  check('comparison_preserves_human_review_and_operational_state',first.alternatives.every(item=>item.review_required===true)&&first.operational_state_modified===false);
  check('route_and_truck_limitations_are_visible',(await workspace().innerText()).includes('ESTIMATED CONNECTION')&&(await workspace().innerText()).includes('No alternative is certified truck-safe.'));
  check('real_map_renders_routes_and_event_geometry',await workspace().locator('.leaflet-container').count()===1&&await workspace().locator('.leaflet-overlay-pane path').count()>3);
  await workspace().locator('.road-alternative').first().focus();await page.keyboard.press('Enter');
  check('route_selection_supports_keyboard',await workspace().locator('.road-alternative').first().getAttribute('aria-pressed')==='true');
  const exportJson=async name=>{const pending=page.waitForEvent('download');await workspace().getByRole('button',{name:'Export comparison JSON',exact:true}).click();const download=await pending;const filename=path.join(folder,name);await download.saveAs(filename);const body=await fs.readFile(filename);return{value:JSON.parse(body),sha256:hash(body),filename:name};};
  const exported=await exportJson('actual-road-comparison.json');const{exported_at,inputs_changed_since_comparison,export_note,...exportedCore}=exported.value;
  check('JSON_export_preserves_exact_actual_API_snapshot',hash(canonical(exportedCore))===result.actual_comparison_sha256&&inputs_changed_since_comparison===false&&typeof exported_at==='string');result.export={filename:exported.filename,sha256:exported.sha256};
  await align(workspace().locator('.road-comparison'));await capture('desktop-cross-state-comparison');
  await workspace().getByLabel('Event proximity buffer (meters)',{exact:true}).fill('300');
  check('edited_inputs_mark_existing_comparison_stale',(await workspace().innerText()).includes('Inputs or saved evidence changed.'));
  const staleExport=await exportJson('stale-input-road-comparison.json');
  check('stale_export_keeps_original_request_and_changed_flag',staleExport.value.inputs_changed_since_comparison===true&&staleExport.value.request.buffer_m===250);
  const second=await compare();check('rerun_uses_edited_buffer_and_clears_stale_notice',second.request.buffer_m===300&&!((await workspace().innerText()).includes('Inputs or saved evidence changed.')));
  await loadSaved();check('rechecking_saved_evidence_invalidates_old_comparison',(await workspace().innerText()).includes('Inputs or saved evidence changed.'));
  await workspace().getByLabel(/^Road comparison travel source/).selectOption('osrm');
  const offlineOSRM=await compare();
  check('offline_OSRM_request_returns_labeled_fallback_without_provider_access',offlineOSRM.request.routing==='osrm'&&offlineOSRM.alternatives.every(item=>item.fallback===true)&&offlineOSRM.routing_error.includes('Offline rehearsal disables provider requests'));
  const routingMetadata=workspace().locator('.road-routing-metadata');
  check('offline_fallback_reason_and_missing_provider_timestamp_visible',(await routingMetadata.innerText()).includes('Estimated fallback reason')&&(await routingMetadata.innerText()).includes(offlineOSRM.routing_error)&&(await routingMetadata.innerText()).includes('No provider retrieval timestamp'));
  await align(routingMetadata);await capture('desktop-offline-routing-provenance');
  result.offline_osrm={routing_error:offlineOSRM.routing_error,alternatives:offlineOSRM.alternatives.length};
  await workspace().getByLabel(/^Road comparison travel source/).selectOption('estimated');await compare();
  await workspace().getByText('Coverage and interpretation limits',{exact:true}).click();
  check('expanded_limits_preserve_separation_from_food_safety',(await workspace().locator('.road-boundaries').innerText()).includes('creates no mandatory hold or dispatcher approval'));

  phase='injected_http_failure';result.injected_cases.push({name:'saved_source_HTTP_503',kind:'browser-only failure response; not a provider request'});
  await page.route(base+'/api/road-intelligence',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'QA injected saved-evidence failure'})}),{times:1});
  await loadSaved();await workspace().getByRole('alert').waitFor();
  check('failed_recheck_keeps_previous_snapshot_and_honest_warning',(await workspace().getByRole('alert').innerText()).includes('QA injected saved-evidence failure')&&(await workspace().innerText()).includes('599')&&(await workspace().getByRole('alert').innerText()).includes('did not establish fresh coverage'));
  phase='actual';const recovered=page.waitForResponse(response=>response.url()===base+'/api/road-intelligence'&&response.request().method()==='GET');await workspace().getByRole('button',{name:'Retry road evidence',exact:true}).click();await recovered;await waitIdle();
  check('retry_recovers_saved_snapshot',await workspace().getByRole('alert').count()===0);
  phase='injected_malformed_comparison';result.injected_cases.push({name:'malformed_comparison_geometry',kind:'browser-only schema failure; previous actual comparison retained'});
  await page.route(base+'/api/road-intelligence/compare',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({compared_at:'2026-10-28T00:00:00Z',alternatives:[]})}),{times:1});
  await compareButton().click();await workspace().getByRole('alert').waitFor();await waitIdle();
  check('malformed_comparison_rejected_without_erasing_actual_result',(await workspace().getByRole('alert').innerText()).includes('unsupported or inconsistent response')&&await workspace().getByRole('heading',{name:'Alternative review',exact:true}).isVisible());
  phase='injected_unavailable_feed';result.injected_cases.push({name:'unavailable_iowa_source',kind:'browser-only synthetic failure presentation; no claim of actual provider failure'});
  const unavailable=structuredClone(snapshot);const missing=unavailable.sources.find(item=>item.id==='iowa_dot');Object.assign(missing,{available:false,event_count:0,events:[],events_truncated:false,returned_event_count:0,coverage_complete:false,stale:true,error:'QA injected Iowa feed unavailable'});
  await page.route(base+'/api/road-intelligence',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(unavailable)}),{times:1});
  await loadSaved();await workspace().getByLabel(/^Official road feed/).selectOption('iowa_dot');
  check('unavailable_feed_shows_failure_without_clear_road_claim',(await iowaCard.innerText()).includes('UNAVAILABLE')&&(await workspace().innerText()).includes('No road-clear conclusion can be drawn.'));
  phase='actual';await loadSaved();await compare();
  await page.setViewportSize({width:390,height:844});await align(workspace());await noOverflow('mobile_workspace_has_no_horizontal_overflow');await capture('mobile-source-coverage');
  await align(workspace().locator('.road-planner'));await noOverflow('mobile_corridor_inputs_have_no_horizontal_overflow');await capture('mobile-corridor-inputs');
  await align(workspace().locator('.road-comparison'));await noOverflow('mobile_comparison_has_no_horizontal_overflow');await capture('mobile-route-comparison');
  await workspace().getByLabel(/^Official road feed/).selectOption('iowa_dot');await workspace().getByLabel('Filter captured road events',{exact:true}).fill(event.id);await workspace().locator('.road-event-row').first().click();
  await detail.getByText('Original provider fields',{exact:true}).click();await align(detail);await noOverflow('mobile_original_provider_fields_have_no_horizontal_overflow');await capture('mobile-provider-fields');
  const width=await detail.evaluate(element=>element.getBoundingClientRect().width);check('mobile_event_detail_remains_readable',width>=260,`${width}px`);
  await page.setViewportSize({width:1440,height:1000});await align(workspace());await capture('desktop-road-workspace');
  check('no_refresh_or_operational_mutation_POST_sent',result.post_requests.every(item=>item.url===base+'/api/road-intelligence/compare'));
  check('viewing_roads_preserves_network_snapshot',canonical(await get('/api/network'))===canonical(networkBefore));
  check('viewing_roads_preserves_driver_assignments',canonical(await get('/api/driver'))===canonical(driverBefore));
  check('no_uncaught_javascript_errors',result.page_errors.length===0,JSON.stringify(result.page_errors));
  check('no_unexpected_application_HTTP_failures',result.http_failures.length===0,JSON.stringify(result.http_failures));
  result.passed=true;
}catch(error){result.passed=false;result.error=String(error);process.exitCode=1;if(page)await page.screenshot({path:path.join(folder,'failure.png'),fullPage:false}).catch(()=>{});
}finally{
  if(browser)await browser.close();
  if(fixtureBefore){result.fixture_fingerprints_before=fixtureBefore;result.fixture_fingerprints_after=await fixtures();const unchanged=canonical(fixtureBefore)===canonical(result.fixture_fingerprints_after);result.checks.push({name:'official_fixture_bytes_unchanged',passed:unchanged});if(!unchanged){result.passed=false;process.exitCode=1;}}
  if(dbBefore){result.database_fingerprints_before=dbBefore;result.database_fingerprints_after=await database(dbPath);const unchanged=canonical(dbBefore)===canonical(result.database_fingerprints_after);result.checks.push({name:'isolated_operational_database_and_sidecars_unchanged',passed:unchanged});if(!unchanged){result.passed=false;process.exitCode=1;}}
  result.finished_at=new Date().toISOString();await fs.writeFile(path.join(folder,'results.json'),JSON.stringify(result,null,2));
  console.log(JSON.stringify({passed:result.passed,checks:result.checks.length,injected_cases:result.injected_cases.length,expected_http_failures:result.expected_injected_http_failures.length,error:result.error,screenshots:result.screenshots},null,2));
}
