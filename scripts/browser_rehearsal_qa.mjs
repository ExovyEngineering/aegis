/** Actual Chrome workflow checks, restricted to a verified isolated rehearsal.
 * No operational mutation is allowed on the operator app. A rehearsal start is
 * deliberately rejected there before any database is opened. Practice is automated QA,
 * not evidence of a genuine five-minute team presentation.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {chromium} from '../.tools/browser-qa/node_modules/playwright-core/index.mjs';
import {parkDriver} from './qa_drive_helpers.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const base='http://127.0.0.1:8001';
const operator='http://127.0.0.1:8000';
const folder=path.join(root,'reports/browser_qa/rehearsal');
await fs.mkdir(folder,{recursive:true});
const previousFiles=await fs.readdir(folder);
if(previousFiles.includes('results.json')) {
  const attempts=previousFiles.map(name=>/^attempt(\d+)\.results\.json$/.exec(name)).filter(Boolean).map(match=>Number(match[1]));
  const nextAttempt=Math.max(0,...attempts)+1;
  await fs.copyFile(path.join(folder,'results.json'),path.join(folder,`attempt${nextAttempt}.results.json`));
  if(previousFiles.includes('failure.png'))await fs.copyFile(path.join(folder,'failure.png'),path.join(folder,`attempt${nextAttempt}.failure.png`));
}
const result={checked_at:new Date().toISOString(),base_url:base,operator_url:operator,
  run_kind:'automated_check',human_rehearsal_verified:false,checks:[],page_errors:[],
  http_failures:[],expected_http_rejections:[],post_requests:[],screenshots:[]};
const check=(name,passed,detail='')=>{result.checks.push({name,passed,detail});if(!passed)throw new Error(`${name}: ${detail}`);};
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const fingerprint=async()=>Object.fromEntries(await Promise.all(['','-wal','-shm','-journal'].map(async suffix=>{
  try{return [suffix,hash(await fs.readFile(path.join(root,'data','aegis.sqlite'+suffix)))];}
  catch(error){if(error.code==='ENOENT')return [suffix,null];throw error;}
})));
const operatorBefore=await fingerprint();
const expectedResponses=new Set();
let browser,page;
try {
  browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
  result.browser_version=browser.version();
  const context=await browser.newContext({viewport:{width:1440,height:1000},timezoneId:'America/Chicago',locale:'en-US',acceptDownloads:true});
  page=await context.newPage();page.setDefaultTimeout(20000);
  page.on('pageerror',error=>result.page_errors.push(error.message));
  page.on('response',response=>{
    if(!response.url().startsWith(base)||response.status()<400)return;
    const key=`${new URL(response.url()).pathname}|${response.status()}`;
    (expectedResponses.has(key)?result.expected_http_rejections:result.http_failures).push({url:response.url(),status:response.status()});
  });
  page.on('request',request=>{if(request.method()==='POST')result.post_requests.push({url:request.url(),path:new URL(request.url()).pathname});});
  const get=async(endpoint,origin=base)=>{
    const response=await context.request.get(origin+endpoint);
    if(!response.ok())throw new Error(`${endpoint}: HTTP ${response.status()}`);
    return response.json();
  };
  const uiPost=async(endpoint,action,status=200)=>{
    const key=`${endpoint}|${status}`;if(status>=400)expectedResponses.add(key);
    try {
      const pending=page.waitForResponse(response=>response.url()===base+endpoint&&response.request().method()==='POST');
      await action();const response=await pending;
      check(`UI ${endpoint} returns ${status}`,response.status()===status,`HTTP ${response.status()}`);
      return response.json();
    } finally {expectedResponses.delete(key);}
  };
  const panel=()=>page.getByRole('region',{name:'Guided presentation rehearsal',exact:true});
  const capture=async name=>{await page.screenshot({path:path.join(folder,name+'.png'),fullPage:false});result.screenshots.push(name+'.png');};
  const align=async locator=>locator.evaluate(element=>element.scrollIntoView({block:'start'}));
  const noOverflow=async label=>{const widths=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth}));check(label,widths.document<=widths.viewport,JSON.stringify(widths));};
  const brief=async()=>{await page.getByRole('button',{name:'Project brief',exact:true}).click();await panel().getByRole('heading',{name:'Practice the five-minute story',exact:true}).waitFor();};
  const notes=async text=>panel().getByLabel('Current stage notes').fill(text);
  const covered=async(run,stage)=>{
    await notes(`Automated Chrome check covered ${stage}; no human presentation claim.`);
    const updated=await uiPost(`/api/rehearsal/${run.id}/checkpoint`,()=>panel().getByRole('button',{name:'Record stage covered',exact:true}).click());
    check(`${stage} recorded in order`,updated.milestones.at(-1).stage_id===stage&&updated.milestones.at(-1).outcome==='covered');
    await panel().locator('.rehearsal-stages li.recorded').nth(updated.milestones.length-1).waitFor();
    return updated;
  };
  const configure=async purpose=>{
    const back=panel().getByRole('button',{name:'Return to current rehearsal',exact:true});
    if(await back.count())await back.click();
    await panel().getByLabel('Rehearsal presenter').fill('Automated Chrome rehearsal');
    await panel().getByLabel('Rehearsal purpose').fill(purpose);
    await panel().getByLabel('Rehearsal record type',{exact:true}).selectOption('automated_check');
  };

  const runtime=await get('/api/runtime-context');
  check('server_is_verified_isolated_and_offline',runtime.mode==='isolated_rehearsal'&&runtime.isolated===true&&runtime.offline===true,JSON.stringify(runtime));
  result.runtime=runtime;
  const operatorRuntime=await get('/api/runtime-context',operator);
  check('operator_server_remains_operator',operatorRuntime.mode==='operator'&&!operatorRuntime.isolated);
  const denied=await context.request.post(operator+'/api/rehearsal/start',{data:{presenter:'Browser QA',purpose:'This operator write must be rejected',run_kind:'automated_check'}});
  check('operator_rehearsal_write_is_rejected',denied.status()===403);
  result.expected_http_rejections.push({url:operator+'/api/rehearsal/start',status:denied.status()});
  const originalStatus=await get('/api/rehearsal');
  if(originalStatus.active?.run_kind==='automated_check'&&originalStatus.active.presenter==='Automated Chrome rehearsal') {
    const unfinished=originalStatus.active;
    const recovery=await context.request.post(base+`/api/rehearsal/${unfinished.id}/finish`,{data:{expected_version:unfinished.version,outcome:'aborted',notes:'Earlier automated Chrome attempt stopped before completion; retain its partial record before this rerun.'}});
    check('prior_owned_automated_attempt_retained_as_aborted',recovery.ok());
    result.recovered_automated_run_id=unfinished.id;
  }
  check('isolated_server_has_no_unfinished_run',!(await get('/api/rehearsal')).active,'Only an earlier owned automated Chrome attempt may be aborted automatically; use a fresh launcher-owned database for any other active run.');
  const reset=await context.request.post(base+'/api/demo/reset',{data:{}});
  check('only_isolated_state_reset_for_setup',reset.ok());
  await page.goto(base+'/?mode=rehearsal',{waitUntil:'domcontentloaded'});
  await panel().getByLabel('Rehearsal presenter').waitFor();
  await page.getByLabel('Isolated rehearsal runtime',{exact:true}).waitFor();
  check('rehearsal_runtime_banner_visible',await page.getByLabel('Isolated rehearsal runtime',{exact:true}).isVisible());
  check('timer_start_requires_presenter_and_purpose',await panel().getByRole('button',{name:'Start rehearsal timer',exact:true}).isDisabled());
  await configure('Exercise six stages and isolated operation evidence through the actual UI.');
  let run=await uiPost('/api/rehearsal/start',()=>panel().getByRole('button',{name:'Start rehearsal timer',exact:true}).click());
  result.run_id=run.id;
  check('record_type_is_explicitly_automated',run.run_kind==='automated_check');
  check('timer_budget_is_five_minutes',run.target_seconds===300&&run.elapsed_seconds>=0);
  await panel().getByLabel('Rehearsal elapsed time',{exact:true}).waitFor();
  check('presentation_verification_limit_visible',(await panel().innerText()).includes('not proof of presentation quality'));
  await align(panel());await capture('desktop-guided-timer');await noOverflow('desktop_timer_has_no_horizontal_overflow');
  const versionAtStart=run.version;
  run=await covered(run,'overview');
  const stale=await context.request.post(base+`/api/rehearsal/${run.id}/checkpoint`,{data:{expected_version:versionAtStart,stage_id:'evidence_science',outcome:'covered',notes:'Obsolete version must not record a milestone.'}});
  check('obsolete_checkpoint_version_rejected',stale.status()===409);
  result.expected_http_rejections.push({url:base+`/api/rehearsal/${run.id}/checkpoint`,status:stale.status(),reason:'stale version'});
  check('stale_checkpoint_does_not_change_run',(await get(`/api/rehearsal/${run.id}`)).version===run.version);

  await panel().getByRole('button',{name:'Open Sources & evidence',exact:true}).click();
  await page.getByRole('heading',{name:'Inspect the underlying evidence',exact:true}).waitFor();
  const sources=page.locator('.source-card');
  check('all_five_refresh_controls_locked_offline',await sources.count()===5&&(await sources.locator('button').all()).length===5);
  for(const button of await sources.getByRole('button',{name:'Refresh',exact:true}).all())check('offline_source_refresh_button_disabled',await button.isDisabled());
  const forecast=await get('/api/evidence/openmeteo');
  check('source_is_dated_fixture_not_new_live_response',forecast.fixture===true&&forecast.live===false&&Boolean(forecast.retrieved_at));
  const fixtureBytes=await fs.readFile(path.join(root,'data/fixtures/openmeteo.json'));
  check('rehearsal_source_keeps_original_fixture_time',forecast.retrieved_at===JSON.parse(fixtureBytes).retrieved_at);
  await brief();
  await panel().getByRole('button',{name:'Open Model evaluation',exact:true}).click();
  await page.getByRole('heading',{name:'Where the fitted model makes errors',exact:true}).waitFor();
  check('measured_science_is_accessible_during_timer',await page.getByRole('heading',{name:'Where the fitted model makes errors',exact:true}).isVisible());
  await brief();run=(await get('/api/rehearsal')).active;
  run=await covered(run,'evidence_science');
  await notes('Attempt to cover disruption before any new event must fail.');
  await uiPost(`/api/rehearsal/${run.id}/checkpoint`,()=>panel().getByRole('button',{name:'Record stage covered',exact:true}).click(),409);
  await panel().getByRole('alert').waitFor();
  check('missing_operational_evidence_is_explained',(await panel().getByRole('alert').innerText()).includes('record event'));
  check('no_fake_disruption_milestone_recorded',(await get(`/api/rehearsal/${run.id}`)).milestones.length===2);
  await panel().getByRole('button',{name:'Open Command',exact:true}).click();
  await page.getByLabel('Select shipment',{exact:true}).selectOption('SH11');
  await page.getByLabel('Event type',{exact:true}).selectOption('temperature_excursion');
  await uiPost('/api/events',()=>page.getByRole('button',{name:'Introduce event',exact:true}).click());
  check('simulated_disruption_recorded_in_rehearsal',(await get('/api/network')).events.some(event=>event.type==='temperature_excursion'&&event.shipment_id==='SH11'));
  const route=await uiPost('/api/route',()=>page.getByRole('button',{name:'Request road route',exact:true}).click());
  check('offline_route_is_visibly_estimated',route.fallback===true&&Boolean(route.error?.includes('Offline rehearsal'))&&route.payload.routes.length>0);
  const modotFixture=JSON.parse(await fs.readFile(path.join(root,'data/fixtures/modot.json'),'utf8'));
  check('offline_road_review_retains_dated_fixture',route.road_review.modot_retrieved_at===modotFixture.retrieved_at);
  check('route_fallback_notice_visible',await page.getByText('Route fallback: straight-line estimated geometry.',{exact:false}).isVisible());
  await brief();run=(await get('/api/rehearsal')).active;run=await covered(run,'disruption');

  await panel().getByRole('button',{name:'Open Command',exact:true}).click();
  const dRow=page.locator('.scenario-panel tbody tr').filter({has:page.locator('.scenario-letter',{hasText:'D'})});
  const proposal=await uiPost('/api/proposals/D',()=>dRow.getByRole('button',{name:'Review',exact:false}).click());
  check('approval_still_requires_dispatcher_identity',await page.getByRole('button',{name:'Approve simulated plan',exact:true}).isDisabled());
  await page.getByLabel('Dispatcher name',{exact:true}).fill('Automated rehearsal dispatcher');
  await page.getByLabel('Reason for approval',{exact:true}).fill('Reviewed isolated simulated event, allocation and hard eligibility constraints.');
  await uiPost(`/api/proposals/${proposal.id}/approve`,()=>page.getByRole('button',{name:'Approve simulated plan',exact:true}).click());
  const assignments=await get('/api/driver');
  check('reviewed_plan_publishes_only_isolated_assignments',assignments.length>0);
  const target=assignments[0];result.target={shipment_id:target.id,truck_id:target.truck_id,lot_id:target.lot_id};
  const network=await get('/api/network');
  check('held_recalled_lots_stay_excluded',assignments.every(trip=>{const lot=network.lots.find(lot=>lot.id===trip.lot_id);return lot&&!lot.held&&!lot.recalled;}));
  await brief();run=(await get('/api/rehearsal')).active;run=await covered(run,'approval');
  await page.reload();await panel().getByLabel('Rehearsal elapsed time',{exact:true}).waitFor();
  check('active_rehearsal_survives_reload',(await get('/api/rehearsal')).active.id===run.id);
  check('recorded_milestones_survive_navigation_reload',(await panel().locator('.rehearsal-stages li.recorded').count())===4);

  await panel().getByRole('button',{name:'Open AEGIS Drive',exact:true}).click();
  await parkDriver(page,target.truck_id);
  const trips=page.getByLabel('Trip for advisories and incident reporting',{exact:true});
  if(await trips.count())await trips.selectOption(target.id);
  await page.getByRole('button',{name:/^Dispatch instructions/}).click();
  await uiPost(`/api/driver/${target.id}/acknowledge`,()=>page.getByRole('button',{name:'Acknowledge assignment',exact:true}).click());
  await page.getByRole('button',{name:/^Report an issue/}).click();
  await page.getByLabel('Report a driver incident').fill('Automated browser report while parked in an isolated rehearsal.');
  await uiPost('/api/driver/incident',()=>page.getByRole('button',{name:'Send to dispatcher',exact:true}).click());
  const audit=await get('/api/audit');
  check('parked_driver_workflow_has_actual_audit_records',['driver_focus','acknowledge','incident'].every(action=>audit.some(item=>item.action===action)));
  await brief();run=(await get('/api/rehearsal')).active;run=await covered(run,'driver');
  await page.setViewportSize({width:390,height:844});await align(panel());await capture('mobile-guided-rehearsal');await noOverflow('mobile_timer_has_no_horizontal_overflow');
  await page.setViewportSize({width:1440,height:1000});
  run=await covered(run,'closing');
  check('six_stages_covered_with_evidence',run.milestones.length===6&&run.milestones.every(item=>item.outcome==='covered'));
  await panel().getByLabel('Rehearsal closing notes').fill('Automated flow completed; the team still needs a real timed presentation and author review.');
  const finished=await uiPost(`/api/rehearsal/${run.id}/finish`,()=>panel().getByRole('button',{name:'Finish and save rehearsal',exact:true}).click());
  check('finished_record_retains_measured_duration',finished.status==='completed'&&finished.run_kind==='automated_check'&&finished.elapsed_seconds>=0&&Boolean(finished.finished_at));
  result.recorded_elapsed_seconds=finished.elapsed_seconds;
  const frozen=await context.request.get(base+`/api/rehearsal/${run.id}/export`);
  check('finished_record_exports_successfully',frozen.ok());
  const frozenBytes=await frozen.body();const frozenData=JSON.parse(frozenBytes);
  check('export_checksum_matches_actual_bytes',frozen.headers()['x-aegis-snapshot-sha256']===hash(frozenBytes));
  check('automated_export_never_closes_human_acceptance_gates',frozenData.five_minute_presentation_verified===false&&frozenData.genuine_kiro_execution_verified===false&&frozenData.author_signoff_verified===false);
  check('operational_milestones_record_audit_evidence',frozenData.run.milestones.filter(item=>['disruption','approval','driver'].includes(item.stage_id)).every(item=>item.evidence.kind==='recorded_operational_actions'&&item.evidence.audit_ids.length>0));
  const fixtureRecord=frozenData.source_report_evidence.find(item=>item.path==='data/fixtures/openmeteo.json');
  check('export_hashes_actual_frozen_source_not_mutable_cache',fixtureRecord?.sha256===hash(fixtureBytes));
  await page.reload();await panel().getByLabel('Saved rehearsal',{exact:true}).selectOption(run.id);
  await panel().getByRole('button',{name:'Open saved rehearsal',exact:true}).click();
  const download=page.waitForEvent('download');
  await panel().getByRole('link',{name:'Download rehearsal evidence JSON',exact:true}).click();
  const saved=await download;await saved.saveAs(path.join(folder,'automated-rehearsal.json'));
  check('UI_download_preserves_frozen_snapshot',hash(await fs.readFile(path.join(folder,'automated-rehearsal.json')))===hash(frozenBytes));
  await align(panel());await capture('desktop-completed-evidence');
  await page.setViewportSize({width:390,height:844});await align(panel());await capture('mobile-saved-evidence');await noOverflow('mobile_saved_record_has_no_horizontal_overflow');
  await page.setViewportSize({width:1440,height:1000});
  await page.getByRole('button',{name:'Command center',exact:false}).click();
  await uiPost('/api/demo/reset',()=>page.getByRole('button',{name:'Reset demo',exact:true}).click());
  const afterReset=await context.request.get(base+`/api/rehearsal/${run.id}/export`);
  check('scenario_reset_cannot_rewrite_completed_export',hash(await afterReset.body())===hash(frozenBytes));
  await brief();await configure('Exercise explicit abort while retaining a partial record.');
  const abortRun=await uiPost('/api/rehearsal/start',()=>panel().getByRole('button',{name:'Start rehearsal timer',exact:true}).click());
  await panel().getByLabel('Rehearsal closing notes').fill('Automated abort path, intentionally stopped before stage coverage.');
  const aborted=await uiPost(`/api/rehearsal/${abortRun.id}/finish`,()=>panel().getByRole('button',{name:'Abort and save record',exact:true}).click());
  check('aborted_rehearsal_retains_partial_state',aborted.status==='aborted'&&aborted.milestones.length===0);
  const abortedExport=await get(`/api/rehearsal/${abortRun.id}/export`);
  check('aborted_export_does_not_invent_covered_stages',abortedExport.run.status==='aborted'&&abortedExport.run.milestones.length===0&&!abortedExport.five_minute_presentation_verified);
  check('no_provider_refresh_POST_sent',result.post_requests.every(item=>!item.path.startsWith('/api/refresh/')));
  check('all_UI_mutations_remained_on_isolated_origin',result.post_requests.every(item=>item.url.startsWith(base)));
  check('no_uncaught_javascript',result.page_errors.length===0,JSON.stringify(result.page_errors));
  check('no_unexpected_application_HTTP_failures',result.http_failures.length===0,JSON.stringify(result.http_failures));
  result.passed=true;
} catch(error) {
  result.passed=false;result.error=String(error);process.exitCode=1;
  if(page)await page.screenshot({path:path.join(folder,'failure.png'),fullPage:false}).catch(()=>{});
} finally {
  if(browser)await browser.close();
  const operatorAfter=await fingerprint();
  result.operator_fingerprints_before=operatorBefore;result.operator_fingerprints_after=operatorAfter;
  const unchanged=JSON.stringify(operatorBefore)===JSON.stringify(operatorAfter);
  result.checks.push({name:'operator_database_and_sidecars_unchanged',passed:unchanged,detail:'Compared actual file hashes before and after; no operator mutation was authorized.'});
  if(!unchanged){result.passed=false;process.exitCode=1;result.error=(result.error??'')+' Operator database fingerprints changed.';}
  result.finished_at=new Date().toISOString();
  await fs.writeFile(path.join(folder,'results.json'),JSON.stringify(result,null,2));
  console.log(JSON.stringify({passed:result.passed,checks:result.checks.length,expected_rejections:result.expected_http_rejections.length,error:result.error,screenshots:result.screenshots},null,2));
}
