/** Actual Chrome checks of historical USDA context and read-only readiness.
 * Mutations are restricted to the dedicated, isolated server on port 8001.
 * No public-provider refresh is requested by this rehearsal.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {chromium} from '../.tools/browser-qa/node_modules/playwright-core/index.mjs';
import {parkDriver} from './qa_drive_helpers.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const base = 'http://127.0.0.1:8001';
const folder = path.join(root, 'reports/browser_qa/readiness');
await fs.mkdir(folder, {recursive:true});
const result = {checked_at:new Date().toISOString(),base_url:base,isolated_database:true,public_refresh_requested:false,checks:[],page_errors:[],http_failures:[],screenshots:[],post_requests:[]};
const check = (name,passed,detail='') => {result.checks.push({name,passed,detail});if(!passed)throw new Error(`${name}: ${detail}`);};
const parseCsv = text => {
  const output=[];let row=[],cell='',quoted=false;
  for(let i=0;i<text.length;i++) {
    const character=text[i];
    if(character==='"') {if(quoted&&text[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}
    else if(character===','&&!quoted){row.push(cell);cell='';}
    else if(character==='\n'&&!quoted){row.push(cell.replace(/\r$/,''));output.push(row);row=[];cell='';}
    else cell+=character;
  }
  if(cell||row.length){row.push(cell.replace(/\r$/,''));output.push(row);}
  const header=output.shift();return output.map(values=>Object.fromEntries(header.map((key,index)=>[key,values[index]??''])));
};
let browser,page;
try {
  browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
  result.browser_version=browser.version();
  const context=await browser.newContext({viewport:{width:1440,height:1000},timezoneId:'America/Chicago',locale:'en-US',acceptDownloads:true});
  page=await context.newPage();page.setDefaultTimeout(20000);
  page.on('pageerror',error=>result.page_errors.push(error.message));
  page.on('response',response=>{if(response.url().startsWith(base)&&response.status()>=400)result.http_failures.push({url:response.url(),status:response.status()});});
  page.on('request',request=>{if(request.method()==='POST'&&request.url().startsWith(base))result.post_requests.push(new URL(request.url()).pathname);});
  const get=async endpoint=>{const response=await context.request.get(base+endpoint);if(!response.ok())throw new Error(`${endpoint}: HTTP ${response.status()}`);return response.json();};
  const uiPost=async(endpoint,action)=>{const pending=page.waitForResponse(response=>response.url()===base+endpoint&&response.request().method()==='POST');await action();const response=await pending;check(`ui_${endpoint}`,response.ok(),`HTTP ${response.status()}`);return response.json();};
  const capture=async name=>{await page.screenshot({path:path.join(folder,name+'.png'),fullPage:false});result.screenshots.push(name+'.png');};
  const alignTop=async locator=>locator.evaluate(element=>element.scrollIntoView({block:'start'}));
  const noOverflow=async name=>{const size=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth}));check(name,size.document<=size.viewport,JSON.stringify(size));};
  const checklist=()=>page.getByRole('region',{name:'Dispatch readiness review',exact:true});
  const selectReadiness=async(status='all',shipment='SH03')=>{await checklist().getByLabel('Readiness status',{exact:true}).selectOption(status);await checklist().getByLabel('Trip readiness',{exact:true}).selectOption(shipment);};
  const refreshReadiness=async()=>{const panel=checklist();await panel.getByRole('button',{name:'Refresh readiness',exact:true}).waitFor({state:'visible'});await page.waitForFunction(()=>!document.querySelector('.readiness-panel button')?.disabled);const pending=page.waitForResponse(response=>response.url()===base+'/api/readiness');await panel.getByRole('button',{name:'Refresh readiness',exact:true}).click();return (await pending).json();};
  const openDesk=async()=>{await page.getByRole('button',{name:'Dispatcher desk',exact:true}).click();await page.getByRole('heading',{name:'Dispatch readiness review',exact:true}).waitFor();};
  const openTargetDriver=async()=>{await page.getByRole('button',{name:'AEGIS Drive',exact:true}).click();await parkDriver(page,'T03');const trips=page.getByLabel('Trip for advisories and incident reporting',{exact:true});if(await trips.count())await trips.selectOption('SH03');await page.getByRole('button',{name:/^Dispatch instructions/}).click();};
  const reset=await context.request.post(base+'/api/demo/reset',{data:{}});check('isolated_demo_reset',reset.ok());
  check('isolated_assignments_initially_empty',(await get('/api/driver')).length===0);
  const originalNetwork=await get('/api/network');
  const initialReadiness=await get('/api/readiness');
  check('readiness_does_not_invent_assignments',initialReadiness.summary.total_assignments===0&&initialReadiness.assignments.length===0);
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.getByRole('heading',{name:'Regional command center',exact:true}).waitFor();
  await openDesk();await checklist().getByText(/No approved trips to inspect/).waitFor();
  check('empty_readiness_visible',await checklist().getByText(/No approved trips to inspect/).isVisible());
  await capture('desktop-empty-readiness');

  await page.getByRole('button',{name:'Sources & evidence',exact:true}).click();
  const ingestionPanel=page.locator('section.panel').filter({has:page.getByRole('heading',{name:'Source-specific ingestion',exact:true})});
  await ingestionPanel.getByRole('row').nth(1).waitFor();
  const ingestion=await get('/api/evidence-summary');
  const unrecognized=ingestion.filter(item=>item.status==='unrecognized');
  let unsupportedLabelsCorrect=unrecognized.length>0;
  for(const item of unrecognized) {
    const text=await ingestionPanel.getByRole('row').filter({hasText:item.file}).innerText();
    unsupportedLabelsCorrect=unsupportedLabelsCorrect&&!text.includes('Source schema accepted')&&/not.*(?:ingested|merged)|unsupported/i.test(text);
  }
  check('unrecognized_imports_never_claim_schema_acceptance',unsupportedLabelsCorrect);
  let acceptedLabelsCorrect=true;
  for(const item of ingestion.filter(row=>row.status==='ingested')) {
    const text=await ingestionPanel.getByRole('row').filter({hasText:item.file}).innerText();
    acceptedLabelsCorrect=acceptedLabelsCorrect&&text.includes('Source schema accepted');
  }
  check('accepted_import_notes_match_actual_ingested_status',acceptedLabelsCorrect);
  await alignTop(ingestionPanel);await capture('desktop-ingestion-status-notes');
  const countyPanel=page.getByRole('region',{name:'Historical USDA food access context',exact:true});
  await countyPanel.getByLabel('USDA county',{exact:true}).waitFor();
  const countyData=await get('/api/food-access');result.usda_source={source_id:countyData.source_id,source_sha256:countyData.source_file.sha256,processed_sha256:countyData.processed_file.sha256,ingested_at:countyData.ingested_at,counties:countyData.records.length};
  check('usda_checked_extract_has_115_distinct_missouri_counties',countyData.integrity_verified===true&&countyData.records.length===115&&new Set(countyData.records.map(row=>row.FIPS)).size===115&&countyData.records.every(row=>/^29\d{3}$/.test(row.FIPS)&&row.State==='MO'));
  check('usda_ten_variables_keep_documented_vintages_and_units',countyData.variables.length===10&&countyData.variables.every(variable=>variable.unit&&variable.denominator&&[2019,2020,2023].includes(variable.year)));
  const rawFile=await fs.readFile(path.join(root,path.basename(countyData.source_file.filename)));
  check('usda_original_workbook_hash_matches_served_provenance',createHash('sha256').update(rawFile).digest('hex')===countyData.source_file.sha256);
  await countyPanel.getByLabel('USDA county',{exact:true}).selectOption('29019');
  const firstMetric=countyPanel.locator('.food-metric').filter({has:page.getByRole('heading',{name:countyData.variables[0].label,exact:true})});
  const boone=countyData.records.find(row=>row.FIPS==='29019');
  check('county_selection_renders_real_numeric_observation',(await firstMetric.locator('strong').innerText())===boone[countyData.variables[0].code].toLocaleString('en-US',{maximumFractionDigits:2}));
  await countyPanel.getByLabel('Compare USDA county',{exact:true}).selectOption('29510');
  check('county_comparison_retains_fips_identity',(await countyPanel.innerText()).includes('29510')&&await countyPanel.locator('.food-comparison').count()===10);
  for(const year of [2019,2020,2023])check(`usda_year_${year}_visible`,(await countyPanel.locator('.food-metric .eyebrow').allTextContents()).some(text=>text.includes(String(year))));
  await firstMetric.getByText('Definition and denominator',{exact:true}).click();
  check('metric_definition_and_denominator_available',(await firstMetric.innerText()).includes(countyData.variables[0].denominator));
  const missingCounty=countyData.records.find(row=>row.GROC20===null);check('actual_suppressed_county_available',Boolean(missingCounty));
  await countyPanel.getByLabel('USDA county',{exact:true}).selectOption(missingCounty.FIPS);
  const groceryCard=countyPanel.locator('.food-metric').filter({has:page.getByRole('heading',{name:countyData.variables.find(variable=>variable.code==='GROC20').label,exact:true})});
  check('suppressed_measure_is_missing_not_zero',(await groceryCard.locator('strong').innerText())==='Missing / suppressed');
  await countyPanel.getByText('Source provenance and interpretation limits',{exact:true}).click();
  check('original_hash_and_source_limits_visible',(await countyPanel.innerText()).includes(countyData.source_file.sha256)&&(await countyPanel.innerText()).includes('No geometry, allocation weighting'));
  const downloadPromise=page.waitForEvent('download');await countyPanel.getByRole('link',{name:'Download county CSV',exact:true}).click();const download=await downloadPromise;
  const csvPath=path.join(folder,'missouri-county-context.csv');await download.saveAs(csvPath);const csvRows=parseCsv(await fs.readFile(csvPath,'utf8'));
  check('county_csv_download_has_all_checked_rows',csvRows.length===115&&csvRows.every(row=>row.source_sha256===countyData.source_file.sha256));
  check('county_csv_preserves_suppression_as_blank',csvRows.find(row=>row.FIPS===missingCounty.FIPS).GROC20==='');
  check('county_csv_not_a_dispatch_score',csvRows.every(row=>row.interpretation.includes('not a safety or dispatch score')));
  await alignTop(countyPanel);await capture('desktop-historical-county-context');
  const catalog=await get('/api/data/catalog');
  check('catalog_contains_eight_separate_semantic_sources',catalog.length===8&&new Set(catalog.map(source=>source.source_key)).size===8&&catalog.every(source=>source.status==='available'&&source.source_key));
  check('catalog_input_hashes_and_output_hashes_recorded',catalog.every(source=>/^[a-f0-9]{64}$/.test(source.sha256)&&Array.isArray(source.input_files)&&source.input_files.length>0&&source.input_files.every(file=>/^[a-f0-9]{64}$/.test(file.sha256))));
  const explorer=page.getByRole('region',{name:'Ingested data explorer',exact:true});
  await explorer.getByLabel('Dataset',{exact:true}).selectOption('beam_0');
  await explorer.getByText('Source identity and import provenance',{exact:true}).waitFor();await explorer.getByText('Source identity and import provenance',{exact:true}).click();
  const beam=catalog.find(source=>source.id==='beam_0');
  check('semantic_source_identity_and_original_hash_are_visible',(await explorer.innerText()).includes(beam.source_key)&&(await explorer.innerText()).includes(beam.input_files[0].sha256));
  check('source_identity_does_not_follow_download_order',(await explorer.innerText()).includes('rather than download order'));
  await explorer.locator('details').filter({has:page.getByText('Source identity and import provenance',{exact:true})}).scrollIntoViewIfNeeded();await capture('desktop-source-import-provenance');
  await page.setViewportSize({width:390,height:844});await alignTop(countyPanel);await noOverflow('mobile_county_context_has_no_horizontal_overflow');await capture('mobile-historical-county-context');
  await alignTop(groceryCard);await capture('mobile-suppressed-grocery-observation');
  await page.setViewportSize({width:1440,height:1000});
  check('viewing_sources_does_not_change_network',JSON.stringify(await get('/api/network'))===JSON.stringify(originalNetwork));
  check('viewing_sources_does_not_dispatch',(await get('/api/driver')).length===0);

  await page.getByRole('button',{name:'Command center',exact:true}).click();
  const row=page.locator('.scenario-panel tbody tr').filter({has:page.locator('.scenario-letter',{hasText:'B'})});
  const proposal=await uiPost('/api/proposals/B',()=>row.getByRole('button',{name:'Review',exact:false}).click());
  check('scenario_B_requires_identified_human_approval',await page.getByRole('button',{name:'Approve simulated plan',exact:true}).isDisabled());
  await page.getByLabel('Dispatcher name',{exact:true}).fill('Readiness QA dispatcher');
  await page.getByLabel('Reason for approval',{exact:true}).fill('Reviewed the simulated allocation and scenario-B verification requirements in the isolated rehearsal');
  await uiPost(`/api/proposals/${proposal.id}/approve`,()=>page.getByRole('button',{name:'Approve simulated plan',exact:true}).click());
  const approved=await get('/api/driver');const target=approved.find(assignment=>assignment.id==='SH03');result.target={shipment_id:target?.id,truck_id:target?.truck_id,lot_id:target?.lot_id};
  check('targeted_trip_was_actually_approved',target?.verification_required===true&&target.truck_id==='T03');
  await openDesk();await selectReadiness();
  const pending=await get('/api/readiness');const pendingTarget=pending.assignments.find(assignment=>assignment.shipment_id==='SH03');
  check('unacknowledged_verification_trip_requires_review',pendingTarget.status==='review_required'&&pendingTarget.blockers.length===0&&pendingTarget.reviews_required.includes('assignment_acknowledged')&&pendingTarget.reviews_required.includes('targeted_verification'));
  check('readiness_has_inspectable_constraint_and_workflow_rows',await checklist().getByRole('row').count()===17&&(await checklist().innerText()).includes('Operational workflow')&&(await checklist().innerText()).includes('Hard eligibility / resource check'));
  await checklist().scrollIntoViewIfNeeded();await capture('desktop-readiness-before-review');
  await openTargetDriver();
  await uiPost('/api/driver/SH03/acknowledge',()=>page.getByRole('button',{name:'Acknowledge assignment',exact:true}).click());
  const afterAck=(await get('/api/readiness')).assignments.find(assignment=>assignment.shipment_id==='SH03');
  check('driver_acknowledgment_clears_only_its_own_check',afterAck.status==='review_required'&&!afterAck.reviews_required.includes('assignment_acknowledged')&&afterAck.reviews_required.includes('targeted_verification'));
  await openDesk();
  await page.getByLabel('Reviewing dispatcher',{exact:true}).fill('Readiness QA dispatcher');
  await page.getByLabel('Decision reason',{exact:true}).fill('Reviewed the simulated temperature history, packaging condition and selected lot identity while preserving human control');
  await page.getByLabel('Trip requiring verification',{exact:true}).selectOption('SH03');
  check('verification_complete_is_disabled_before_checklist',await page.getByRole('button',{name:'Record verification review complete',exact:true}).isDisabled());
  for(const label of ['Reviewed simulated temperature history','Reviewed packaging-condition scenario','Reviewed simulated lot identity and assignment'])await page.getByLabel(label,{exact:true}).check();
  const verified=await uiPost('/api/dispatch/assignments/SH03/verification',()=>page.getByRole('button',{name:'Record verification review complete',exact:true}).click());
  check('verification_records_exact_assignment_context',verified.status==='complete'&&verified.context.id==='SH03'&&verified.context.lot_id===target.lot_id&&Object.values(verified.checks).every(Boolean));
  await refreshReadiness();await selectReadiness('ready_for_review');
  check('completed_human_checks_improve_readiness',(await get('/api/readiness')).assignments.find(assignment=>assignment.shipment_id==='SH03').status==='ready_for_review');
  check('checklist_pass_does_not_consume_inventory',(await get('/api/network')).lots.find(lot=>lot.id===target.lot_id).inventory_kg===originalNetwork.lots.find(lot=>lot.id===target.lot_id).inventory_kg);
  const issue=async text=>{await page.getByLabel('Approved trip for instruction').selectOption('SH03');await page.getByLabel('New dispatcher instruction').fill(text);return uiPost('/api/dispatch/assignments/SH03/instruction',()=>page.getByRole('button',{name:'Approve and send instruction',exact:true}).click());};
  const firstInstruction=await issue('Readiness QA: review the assigned loading documentation while safely parked.');
  const secondInstruction=await issue('Readiness QA updated instruction: contact the dispatcher before any proposed change.');
  check('new_instruction_gets_its_own_revision',secondInstruction.instruction_revision>firstInstruction.instruction_revision);
  await refreshReadiness();await selectReadiness('review_required');
  const instructionPending=(await get('/api/readiness')).assignments.find(assignment=>assignment.shipment_id==='SH03');
  check('new_instruction_reopens_only_instruction_review',instructionPending.status==='review_required'&&instructionPending.reviews_required.length===1&&instructionPending.reviews_required[0]==='instruction_acknowledged');
  const stale=await context.request.post(base+'/api/driver/SH03/instruction-ack',{data:{instruction_revision:firstInstruction.instruction_revision}});
  check('obsolete_instruction_cannot_be_acknowledged',stale.status()===409);
  check('rejected_old_ack_preserves_current_instruction',!(await get('/api/driver')).find(assignment=>assignment.id==='SH03').instruction_acknowledged);
  await openTargetDriver();
  await uiPost('/api/driver/SH03/instruction-ack',()=>page.getByRole('button',{name:'Acknowledge new instruction',exact:true}).click());
  check('driver_acknowledges_the_displayed_current_version',(await get('/api/driver')).find(assignment=>assignment.id==='SH03').instruction_revision===secondInstruction.instruction_revision&&(await get('/api/readiness')).assignments.find(assignment=>assignment.shipment_id==='SH03').status==='ready_for_review');
  await openDesk();await selectReadiness('ready_for_review');await alignTop(checklist());await capture('desktop-readiness-checks-complete');
  await page.setViewportSize({width:390,height:844});await alignTop(checklist());await noOverflow('mobile_readiness_has_no_horizontal_overflow');await capture('mobile-readiness-review');
  const firstReadinessRow=checklist().locator('.readiness-detail tbody tr').first();
  const cellLayout=await firstReadinessRow.locator('td').nth(2).evaluate(element=>({width:element.getBoundingClientRect().width,height:element.getBoundingClientRect().height,wordBreak:getComputedStyle(element).wordBreak,text:element.textContent}));
  check('mobile_readiness_evidence_has_readable_stacked_width',cellLayout.width>=200&&cellLayout.height<150&&cellLayout.wordBreak==='normal',JSON.stringify(cellLayout));
  await alignTop(firstReadinessRow);await capture('mobile-readiness-check-detail');await page.setViewportSize({width:1440,height:1000});
  await page.getByLabel('Reviewing dispatcher',{exact:true}).fill('Readiness QA dispatcher');
  await page.getByLabel('Decision reason',{exact:true}).fill('Explicit precautionary hold for the isolated workflow test; no predictive score imposed this hold');
  const beforeHold=await get('/api/driver');
  const held=await uiPost(`/api/dispatch/lots/${target.lot_id}/hold`,()=>page.getByRole('button',{name:`Place hold on ${target.lot_id}`,exact:true}).click());
  check('explicit_hold_invalidates_all_affected_assignments',held.invalidated_shipments.includes('SH03')&&held.invalidated_shipments.length===beforeHold.filter(assignment=>assignment.lot_id===target.lot_id).length);
  const afterHold=await get('/api/readiness');
  check('held_lot_cannot_remain_ready_or_assigned',!afterHold.assignments.some(assignment=>assignment.lot_id===target.lot_id)&&!(await get('/api/driver')).some(assignment=>assignment.lot_id===target.lot_id));
  const released=await uiPost(`/api/dispatch/lots/${target.lot_id}/release`,()=>page.getByRole('button',{name:`Release hold on ${target.lot_id}`,exact:true}).click());
  check('release_does_not_automatically_republish_trip',released.assignments_republished===false&&!(await get('/api/driver')).some(assignment=>assignment.id==='SH03'));
  await refreshReadiness();
  const current=await get('/api/readiness');
  check('readiness_summary_matches_current_approved_manifest',current.summary.total_assignments===(await get('/api/driver')).length&&current.network_revision===released.network_revision);
  check('readiness_remains_diagnostic_not_dispatch_authority',(await checklist().innerText()).includes('does not dispatch, certify food safety'));
  check('no_public_refresh_actions_requested',!result.post_requests.some(endpoint=>endpoint.startsWith('/api/refresh/')));
  check('no_uncaught_javascript',result.page_errors.length===0,JSON.stringify(result.page_errors));
  check('no_application_http_failures',result.http_failures.length===0,JSON.stringify(result.http_failures));
  result.passed=true;
} catch(error) {
  result.passed=false;result.error=String(error);process.exitCode=1;
  if(page)await page.screenshot({path:path.join(folder,'failure.png'),fullPage:false}).catch(()=>{});
} finally {
  if(browser)await browser.close();result.finished_at=new Date().toISOString();
  await fs.writeFile(path.join(folder,'results.json'),JSON.stringify(result,null,2));
  console.log(JSON.stringify({passed:result.passed,checks:result.checks.length,error:result.error,screenshots:result.screenshots},null,2));
}
