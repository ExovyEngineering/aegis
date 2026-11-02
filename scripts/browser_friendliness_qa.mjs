/** Actual Chrome checks of the plain-language planning journey.
 * Requires an explicitly selected, verified isolated OFFLINE rehearsal UUID.
 * Only read-only planning/assistant POSTs are permitted. External browser requests
 * are replaced with labeled QA placeholders; no tile/provider or LLM is called.
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
if(parsed.protocol!=='http:'||parsed.hostname!=='127.0.0.1'||['','8000'].includes(parsed.port)||parsed.pathname!=='/'||parsed.search||parsed.hash)throw new Error('Set AEGIS_BASE_URL to an isolated loopback QA port; never use operator port 8000');
if(!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(expectedUUID))throw new Error('Set AEGIS_QA_REHEARSAL_ID to the expected isolated UUID before running');
const folder=path.join(root,'reports/browser_qa/friendliness');
await fs.mkdir(folder,{recursive:true});
const previous=await fs.readdir(folder);
if(previous.includes('results.json')){
  const attempts=previous.map(name=>/^attempt(\d+)\.results\.json$/.exec(name)).filter(Boolean).map(match=>Number(match[1]));
  const attempt=Math.max(0,...attempts)+1;
  await fs.copyFile(path.join(folder,'results.json'),path.join(folder,`attempt${attempt}.results.json`));
  if(previous.includes('failure.png'))await fs.copyFile(path.join(folder,'failure.png'),path.join(folder,`attempt${attempt}.failure.png`));
  const history=path.join(folder,'history',new Date().toISOString().replace(/[:.]/g,'-'));
  await fs.mkdir(history,{recursive:true});
  for(const filename of previous)if(!filename.startsWith('attempt')&&/\.(?:json|png)$/.test(filename))await fs.copyFile(path.join(folder,filename),path.join(history,filename));
}
const canonical=value=>JSON.stringify(value,(_key,item)=>item&&typeof item==='object'&&!Array.isArray(item)?Object.fromEntries(Object.keys(item).sort().map(key=>[key,item[key]])):item);
const same=(left,right)=>canonical(left)===canonical(right);
const normal=value=>value.replace(/\s+/g,' ').trim();
const escape=value=>value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
const save=(name,value)=>fs.writeFile(path.join(folder,name+'.json'),JSON.stringify(value,null,2)+'\n');
async function fingerprint(filename){try{const stat=await fs.stat(filename);const hash=createHash('sha256');for await(const bytes of createReadStream(filename))hash.update(bytes);return{exists:true,bytes:stat.size,sha256:hash.digest('hex')};}catch(error){if(error.code==='ENOENT')return{exists:false};throw error;}}
async function database(filename){return Object.fromEntries(await Promise.all(['','-wal','-shm','-journal'].map(async suffix=>[suffix||'sqlite',await fingerprint(filename+suffix)])));}
async function tree(relative){const found={};async function visit(directory){let entries;try{entries=await fs.readdir(directory,{withFileTypes:true});}catch(error){if(error.code==='ENOENT')return;throw error;}for(const entry of entries){const filename=path.join(directory,entry.name);if(entry.isDirectory())await visit(filename);else if(entry.isFile())found[path.relative(root,filename).replaceAll('\\','/')]=await fingerprint(filename);else if(entry.isSymbolicLink())found[path.relative(root,filename).replaceAll('\\','/')]={symlink_not_followed:true};}}await visit(path.join(root,relative));return found;}
const result={checked_at:new Date().toISOString(),base_url:base,expected_rehearsal_id:expectedUUID,run_kind:'automated_check',human_rehearsal_verified:false,read_only:true,public_provider_refresh_requested:false,actual_osrm_queried:false,actual_llm_queried:false,external_map_tiles_replaced_with_qa_placeholders:true,checks:[],screenshots:[],page_errors:[],console_errors:[],http_failures:[],request_failures:[],blocked_requests:[],external_qa_placeholders:[],post_requests:[],control_requests:[]};
const check=(name,passed,detail='')=>{result.checks.push({name,passed,detail});if(!passed)throw new Error(`${name}: ${detail}`);};
let browser,context,page,phase='guard',isolated,baselineNetwork,baselineAssignments;
try{
  result.operator_before=await database(path.join(root,'data/aegis.sqlite'));
  browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});result.browser_version=browser.version();
  context=await browser.newContext({viewport:{width:1440,height:1050},locale:'en-US',timezoneId:'America/Chicago',acceptDownloads:true});
  const get=async endpoint=>{if(!['/api/runtime-context','/api/network','/api/driver','/api/dispatch','/api/assistant/context','/api/assistant/engine','/api/road-intelligence'].includes(endpoint))throw new Error('Control request is outside the explicit read-only allowlist');const reply=await context.request.get(base+endpoint);result.control_requests.push({phase,endpoint,method:'GET',status:reply.status()});check('GET '+endpoint,reply.ok(),`HTTP ${reply.status()}`);return reply.json();};
  const runtime=await get('/api/runtime-context');result.runtime=runtime;
  check('expected isolated offline UUID verified',runtime.mode==='isolated_rehearsal'&&runtime.isolated===true&&runtime.offline===true&&runtime.rehearsal_id===expectedUUID);
  isolated=path.resolve(root,runtime.database_relative_path||'');
  check('database is exactly the UUID rehearsal path',isolated===path.join(root,'data/rehearsals',expectedUUID+'.sqlite'));
  baselineNetwork=await get('/api/network');baselineAssignments=await get('/api/driver');const dispatch=await get('/api/dispatch');
  check('fresh rehearsal has no approved driver assignments',baselineAssignments.length===0&&dispatch.assignments.length===0);
  const initial=await get('/api/assistant/context');const engine=await get('/api/assistant/engine');const roads=await get('/api/road-intelligence');
  check('assistant uses deterministic evidence without configured model',engine.configured===false&&initial.engine.llm_used===false&&initial.engine.mode==='deterministic');
  check('road workspace uses offline captured evidence',roads.offline===true&&roads.examples.length>0);
  result.isolated_before=await database(isolated);result.fixtures_before=await tree('data/fixtures');result.cache_before=await tree('data/cache');
  await save('actual-initial-context',initial);await save('actual-initial-network',baselineNetwork);
  // This route guard is independent of the server's offline mode: an accidental
  // operator endpoint or provider request is refused before the browser sends it.
  await context.route('**/*',async route=>{
    const request=route.request();const url=new URL(request.url());
    if(['data:','blob:','about:'].includes(url.protocol)){await route.continue();return;}
    if(url.origin!==parsed.origin){result.external_qa_placeholders.push({phase,url:request.url(),method:request.method(),kind:'browser-only blank image placeholder; provider not contacted'});await route.fulfill({status:200,contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#eef0ec"/></svg>'});return;}
    let allowed=['GET','HEAD'].includes(request.method())&&!/\/(?:refresh|route)(?:\/|$)/.test(url.pathname)&&!url.searchParams.has('refresh');
    if(request.method()==='POST'){
      const body=request.postDataJSON();
      allowed=url.pathname==='/api/delivery-outlook'||url.pathname==='/api/assistant/ask'||url.pathname==='/api/assistant/interpret'&&body?.allow_model===false||url.pathname==='/api/road-intelligence/compare'&&body?.routing==='estimated';
      result.post_requests.push({phase,path:url.pathname,body,allowed});
    }
    if(!allowed){result.blocked_requests.push({phase,path:url.pathname,method:request.method()});await route.abort('blockedbyclient');return;}
    await route.continue();
  });
  page=await context.newPage();page.setDefaultTimeout(25000);
  page.on('pageerror',error=>result.page_errors.push({phase,message:error.message}));
  page.on('console',message=>{if(message.type()==='error')result.console_errors.push({phase,message:message.text(),location:message.location()});});
  page.on('response',reply=>{if(reply.status()>=400&&new URL(reply.url()).origin===parsed.origin)result.http_failures.push({phase,url:reply.url(),status:reply.status()});});
  page.on('requestfailed',request=>result.request_failures.push({phase,url:request.url(),reason:request.failure()?.errorText}));
  const nav=()=>page.getByRole('navigation',{name:'Main navigation',exact:true});
  const outlook=()=>page.getByRole('region',{name:'Where could this delivery plan run into trouble?',exact:true});
  const assistant=()=>page.getByRole('region',{name:'Evidence assistant',exact:true});
  const answer=()=>page.getByRole('region',{name:'Captured evidence briefing',exact:true});
  const road=()=>page.getByRole('region',{name:'Road intelligence workspace',exact:true});
  const desk=()=>page.getByRole('region',{name:'Dispatcher desk',exact:true});
  const nextPost=endpoint=>page.waitForResponse(reply=>reply.url()===base+endpoint&&reply.request().method()==='POST');
  const capture=async name=>{await page.screenshot({path:path.join(folder,name+'.png'),fullPage:false});result.screenshots.push(name+'.png');};
  const noOverflow=async name=>check(name,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  const download=async(button,name)=>{const pending=page.waitForEvent('download');await button.click();const exported=await pending;const filename=path.join(folder,name+'.json');await exported.saveAs(filename);return JSON.parse(await fs.readFile(filename,'utf8'));};
  const settledOutlook=async reply=>{check('actual delivery estimate HTTP success',reply.ok(),`HTTP ${reply.status()}`);const value=await reply.json();await outlook().getByRole('button',{name:'Estimate impact',exact:true}).waitFor();await page.waitForFunction(delay=>document.querySelector('.outlook-result-stamp')?.textContent.includes(`${delay} extra minutes per candidate`),value.parameters.added_delay_minutes);return value;};
  phase='delivery_outlook';let pending=nextPost('/api/delivery-outlook');await page.goto(base+'/',{waitUntil:'domcontentloaded'});const baseline=await settledOutlook(await pending);await save('actual-current-input-outlook',baseline);
  result.served_assets=await page.locator('script[type="module"][src]').evaluateAll(items=>items.map(item=>item.getAttribute('src')));
  check('current plan receives a real automatic baseline estimate',baseline.parameters.added_delay_minutes===0&&baseline.network_revision===baselineNetwork.revision&&baseline.read_only===true&&baseline.operational_state_modified===false);
  const assertSummary=async(value,name)=>{const text=normal(await outlook().innerText());check(name,text.includes(`${value.summary.after_unmet_demand_kg.toLocaleString('en-US')} kg`)&&text.includes(`${value.summary.candidate_deadline_misses} candidate trips`)&&text.includes(`${value.summary.candidate_temperature_reviews} candidate trips`)&&text.includes('Candidate checks include trips that may not be selected'));};
  await assertSummary(baseline,'current input metrics match the captured backend result');await outlook().scrollIntoViewIfNeeded();await capture('desktop-current-delivery-outlook');
  pending=nextPost('/api/delivery-outlook');await outlook().getByRole('button',{name:'Try a 1-hour delay',exact:true}).click();const delayed=await settledOutlook(await pending);await save('actual-one-hour-outlook',delayed);
  check('one-click delay calls real estimator with same network revision',delayed.parameters.added_delay_minutes===60&&delayed.network_revision===baseline.network_revision&&delayed.snapshot_id!==baseline.snapshot_id&&delayed.read_only===true&&delayed.operational_state_modified===false);
  await assertSummary(delayed,'one-hour metrics match actual estimator result');await outlook().locator('summary').filter({hasText:'Compare the four preview responses'}).click();
  const responseRows=outlook().locator('.outlook-details').filter({has:page.locator('summary').filter({hasText:'Compare the four preview responses'})});
  check('all four real constrained response previews are visible',delayed.scenarios.length===4&&(await responseRows.innerText()).includes('not approved assignments')&&await responseRows.locator('tbody tr').count()===4);
  const beforeDraft=result.post_requests.length;await outlook().getByRole('combobox',{name:'Extra road delay',exact:true}).selectOption('120');await outlook().getByText('Assumptions changed.',{exact:false}).waitFor();
  check('editing delay is a draft and leaves captured result visible',result.post_requests.length===beforeDraft&&(await outlook().locator('.outlook-result-stamp').innerText()).includes('60 extra minutes'));
  const exported=await download(outlook().getByRole('button',{name:'Export outlook JSON',exact:true}),'captured-one-hour-outlook-export');
  check('dirty-input export contains actual captured result rather than draft',same(exported,{...delayed,captured_export:true})&&exported.parameters.added_delay_minutes===60);
  await outlook().scrollIntoViewIfNeeded();await capture('desktop-one-hour-draft-and-response-preview');
  const firstInspect=outlook().getByRole('button',{name:/^Inspect SH/}).first();const candidate=(await firstInspect.innerText()).match(/SH\w+/)?.[0];check('priority candidate has an inspect action',!!candidate);await firstInspect.click();await page.waitForFunction(()=>document.activeElement?.id==='command-trip-detail');
  check('candidate Inspect focuses actual trip and updates selected shipment',await page.getByRole('combobox',{name:'Select shipment',exact:true}).inputValue()===candidate);await capture('desktop-candidate-inspect-focus');
  phase='candidate_road_handoff';
  const handoffCandidate=baselineNetwork.shipments.filter((shipment,index)=>index>0&&shipment.origin!==baselineNetwork.shipments[0].origin&&delayed.shipments.some(row=>row.id===shipment.id)).at(-1);
  check('an actual non-first candidate has a different origin for handoff verification',!!handoffCandidate);
  const origin=baselineNetwork.nodes.find(node=>node.id===handoffCandidate.origin);const destination=baselineNetwork.nodes.find(node=>node.id===handoffCandidate.destination);
  const expectedContext={shipmentId:handoffCandidate.id,networkRevision:baselineNetwork.revision,origin:origin.coordinates,destination:destination.coordinates,originName:origin.name,destinationName:destination.name};
  result.tested_candidate_handoff=expectedContext;
  await outlook().getByRole('button',{name:new RegExp(`^Show all ${delayed.shipments.length} candidates$`)}).click();
  const handoffPostCount=result.post_requests.length;
  await outlook().getByRole('button',{name:`Compare roads for ${handoffCandidate.id}`,exact:true}).click();
  const contextPanel=road().getByRole('region',{name:'Selected Command candidate',exact:true});await contextPanel.waitFor();await road().getByRole('button',{name:'Compare this journey',exact:true}).waitFor();
  const actualName=`Selected candidate ${handoffCandidate.id}: ${origin.name} → ${destination.name}`;
  check('per-candidate handoff opens its actual names and captured revision',normal(await contextPanel.innerText()).includes(actualName)&&(await contextPanel.innerText()).includes(`captured network revision ${baselineNetwork.revision}`)&&(await road().getByRole('combobox',{name:'Planning corridor',exact:true}).locator('option:checked').innerText())===actualName);
  check('handoff coordinates come from this candidate rather than a fixed public example',same([Number(await road().getByLabel('Origin longitude',{exact:true}).inputValue()),Number(await road().getByLabel('Origin latitude',{exact:true}).inputValue())],origin.coordinates)&&same([Number(await road().getByLabel('Destination longitude',{exact:true}).inputValue()),Number(await road().getByLabel('Destination latitude',{exact:true}).inputValue())],destination.coordinates));
  check('opening a selected candidate makes no comparison or operational POST',result.post_requests.length===handoffPostCount);
  pending=nextPost('/api/road-intelligence/compare');await road().getByRole('button',{name:'Compare this journey',exact:true}).click();let handoffReply=await pending;check('candidate comparison uses the actual read-only endpoint',handoffReply.ok());const handoffComparison=await handoffReply.json();
  await save('actual-candidate-road-comparison',handoffComparison);await page.waitForFunction(()=>document.activeElement?.id==='road-comparison-result');
  const expectedRoadRequest={origin:origin.coordinates,destination:destination.coordinates,routing:'estimated',buffer_m:250};
  check('actual comparison request is exactly this candidate geometry with unchanged backend schema',same(handoffComparison.request,expectedRoadRequest)&&same(result.post_requests.at(-1).body,expectedRoadRequest));
  check('captured comparison retains the same simulated candidate identity',normal(await road().getByLabel('Captured candidate provenance',{exact:true}).innerText()).includes(`candidate ${handoffCandidate.id} · network revision ${baselineNetwork.revision}`)&&(await road().getByLabel('Captured candidate provenance',{exact:true}).innerText()).includes('not an approved assignment'));
  const candidateExport=await download(road().getByRole('button',{name:'Export comparison JSON',exact:true}),'captured-candidate-road-export');
  check('candidate export preserves identity revision names and actual compared coordinates',same(candidateExport.request,expectedRoadRequest)&&Object.entries(expectedContext).every(([key,value])=>same(candidateExport.journey_context[key],value))&&candidateExport.journey_context.kind==='simulated_command_candidate'&&candidateExport.journey_context.approved_assignment===false&&candidateExport.journey_label===actualName&&!candidateExport.inputs_changed_since_comparison);
  const beforeRoadDraft=result.post_requests.length;await road().getByRole('spinbutton',{name:'Event proximity buffer (meters)',exact:true}).fill('500');
  const candidateDraftExport=await download(road().getByRole('button',{name:'Export comparison JSON',exact:true}),'captured-candidate-road-draft-export');
  check('editing comparison inputs keeps the captured candidate export unchanged with an explicit older-input marker',result.post_requests.length===beforeRoadDraft&&same(candidateDraftExport.request,candidateExport.request)&&same(candidateDraftExport.journey_context,candidateExport.journey_context)&&candidateDraftExport.inputs_changed_since_comparison===true);
  await road().getByRole('heading',{name:'Alternative review',exact:true}).scrollIntoViewIfNeeded();await capture('desktop-actual-candidate-road-handoff');
  pending=nextPost('/api/delivery-outlook');await road().getByRole('button',{name:'Compare delivery responses in Command',exact:true}).click();await settledOutlook(await pending);await page.waitForFunction(()=>document.activeElement?.id==='command-scenarios');
  check('returning from the candidate comparison focuses current response plans without a proposal',await page.locator('#command-scenarios').isVisible()&&await page.getByRole('dialog').count()===0&&!result.post_requests.some(request=>request.path.startsWith('/api/proposals')));await capture('desktop-road-return-current-response-plans');
  const beforePlanReview=result.post_requests.length;await outlook().getByRole('button',{name:'Review current response plans',exact:true}).click();await page.waitForFunction(()=>document.activeElement?.id==='command-scenarios');
  check('outlook review current response plans directly focuses scenarios and sends no planning or approval request',result.post_requests.length===beforePlanReview&&await page.locator('#command-scenarios').isVisible()&&await page.getByRole('dialog').count()===0);
  await nav().getByRole('button',{name:'Road intelligence',exact:true}).click();await road().getByRole('button',{name:'Compare this journey',exact:true}).waitFor();
  check('generic Road navigation clears the candidate and restores a named public example',await road().getByRole('region',{name:'Selected Command candidate',exact:true}).count()===0&&!(await road().getByRole('combobox',{name:'Planning corridor',exact:true}).locator('option:checked').innerText()).startsWith('Selected candidate')&&!!await road().getByRole('combobox',{name:'Planning corridor',exact:true}).inputValue());
  pending=nextPost('/api/delivery-outlook');await nav().getByRole('button',{name:'Command center',exact:true}).click();await settledOutlook(await pending);
  phase='map_guidance';const layerGuide=page.getByRole('region',{name:'Map layer guide',exact:true});const views=page.getByRole('group',{name:'Map views',exact:true});
  check('map guide has five meaningful layer switches',await layerGuide.getByRole('checkbox').count()===5);
  for(const [preset,layer,explanation] of [['Plan deliveries','Simulated deliveries','Truck markers are illustrative midpoints'],['Check weather','Weather warnings','Turning them on does not add a delay'],['Review roads','Road incidents','OSRM does not automatically avoid'],['View facilities','FSIS facilities','does not establish a supply contract']]){
    await views.getByRole('button',{name:preset,exact:true}).click();check('map preset '+preset+' selects its documented layer',await layerGuide.getByRole('checkbox',{name:layer,exact:true}).isChecked()&&(await page.getByRole('region',{name:'Layer explanation',exact:true}).innerText()).includes(explanation));
  }
  await layerGuide.getByRole('button',{name:'Explain requested route',exact:true}).click();check('route layer explains that a switch does not generate routes',(await page.getByRole('region',{name:'Layer explanation',exact:true}).innerText()).includes('A switch cannot generate a route'));
  const mapText=await layerGuide.innerText();check('map layer counts distinguish fictional connections and missing road results',mapText.includes('displayed trip connections')&&mapText.includes('fictional sites')&&mapText.includes('No route result yet'));await layerGuide.scrollIntoViewIfNeeded();await capture('desktop-map-presets-and-layer-explanation');
  phase='assistant_chicken';await nav().getByRole('button',{name:'Evidence assistant',exact:true}).click();await assistant().getByRole('button',{name:'Ask AEGIS',exact:true}).waitFor();await assistant().getByRole('textbox',{name:'Your evidence question',exact:true}).fill('chicken');
  pending=nextPost('/api/assistant/interpret');await assistant().getByRole('button',{name:'Ask AEGIS',exact:true}).click();let reply=await pending;check('short chicken question is accepted',reply.ok(),`HTTP ${reply.status()}`);const clarification=await reply.json();await save('actual-chicken-clarification',clarification);
  const choice=page.getByRole('region',{name:'Choose what to check',exact:true});await choice.waitFor();check('chicken yields useful choices rather than a silent empty answer',clarification.kind==='clarification'&&clarification.clarification.question_ids.length>0&&await choice.getByRole('button').count()===clarification.clarification.question_ids.length);await capture('desktop-chicken-useful-choices');
  const chosenQuestion=initial.questions.find(question=>question.id===clarification.clarification.question_ids[0]);pending=nextPost('/api/assistant/ask');await choice.getByRole('button',{name:chosenQuestion.label,exact:true}).click();reply=await pending;check('one clarification click produces an actual answer',reply.ok());const chickenAnswer=await reply.json();await answer().waitFor();await save('actual-chicken-choice-answer',chickenAnswer);
  const assertGrounded=async(value,name)=>{await page.waitForFunction(ids=>JSON.stringify([...document.querySelectorAll('.assistant-answer .assistant-fact-id')].map(item=>item.textContent))===JSON.stringify(ids),value.answer.items.map(item=>item.id));const text=normal(await answer().innerText());check(name,value.answer.items.length>0&&value.answer.items.every(item=>initial.facts.some(fact=>same(item,fact)))&&value.answer.items.every(item=>text.includes(normal(item.text)))&&value.operational_state_modified===false);};
  await assertGrounded(chickenAnswer,'chicken choice answer uses real captured facts');const fact=answer().locator('.assistant-fact').first();await fact.locator('summary').click();check('useful answer has inspectable exact source citations',await fact.locator('.assistant-provenance code').count()===chickenAnswer.answer.items[0].citations.length&&chickenAnswer.answer.items[0].citations.length>0);await answer().scrollIntoViewIfNeeded();await capture('desktop-chicken-cited-answer');
  const common=initial.questions.find(question=>question.id==='driver_workflow');pending=nextPost('/api/assistant/ask');await assistant().locator('.assistant-question-grid').getByRole('button',{name:new RegExp('^'+escape(common.label))}).click();reply=await pending;check('common question answers on one click without Get answer',reply.ok());const commonAnswer=await reply.json();await assertGrounded(commonAnswer,'common driver workflow answer is cited and captured');check('common question explains approval rather than pretending to dispatch',commonAnswer.question_id==='driver_workflow');await answer().scrollIntoViewIfNeeded();await capture('desktop-one-click-common-question');
  phase='road_guidance';await nav().getByRole('button',{name:'Road intelligence',exact:true}).click();await road().getByRole('button',{name:'Compare this journey',exact:true}).waitFor();const journey=road().getByRole('combobox',{name:'Planning corridor',exact:true});
  check('roads start with a named human-readable journey',!!await journey.inputValue()&&(await journey.locator('option:checked').innerText()).includes('Columbia'));
  check('raw coordinates are optional rather than the initial task',!await road().getByLabel('Origin longitude',{exact:true}).isVisible());await road().getByRole('button',{name:'Choose or change journey',exact:true}).click();check('journey guide focuses the actual selector',await journey.evaluate(element=>element===document.activeElement));
  pending=nextPost('/api/road-intelligence/compare');await road().getByRole('button',{name:'Compare this journey',exact:true}).click();reply=await pending;check('guide button computes the real saved-evidence comparison',reply.ok());const comparison=await reply.json();await save('actual-guided-road-comparison',comparison);await page.waitForFunction(()=>document.activeElement?.id==='road-comparison-result');
  const firstRoute=comparison.alternatives[0];const meaning=road().locator('.journey-plain-result');const meaningText=await meaning.innerText();check('route result interprets actual distance and duration with explicit estimate bounds',meaningText.includes((firstRoute.distance_m/1000).toFixed(1)+' km')&&meaningText.includes(String(Math.round(firstRoute.duration_seconds/60))+' minutes')&&firstRoute.fallback===true&&meaningText.includes('rough estimated connection'));
  check('offline provider refresh is disabled',await road().getByRole('button',{name:'Refresh official road feeds',exact:true}).isDisabled());
  const nearby=firstRoute.reviews.flatMap(review=>review.nearby_events);if(nearby.length){await road().getByRole('button',{name:'Inspect first nearby notice',exact:true}).click();await page.waitForFunction(()=>document.activeElement?.id==='road-selected-event');check('notice action focuses the exact captured record',(await road().getByRole('article',{name:'Road event detail',exact:true}).innerText()).includes(nearby[0].title));}else check('no-hit comparison still explains incomplete road knowledge',meaningText.includes('does not establish a clear road'));
  await road().getByRole('heading',{name:'Alternative review',exact:true}).scrollIntoViewIfNeeded();await capture('desktop-guided-road-comparison');
  phase='dispatch_empty_state';await nav().getByRole('button',{name:'Dispatcher desk',exact:true}).click();await desk().getByRole('heading',{name:'No approved trips available',exact:true}).waitFor();check('empty dispatcher desk points to human-reviewed plan selection',await desk().getByRole('button',{name:'Choose a response plan',exact:true}).isEnabled()&&(await desk().innerText()).includes('There are no approved driver trips yet'));
  check('missing reviewer details visibly explain disabled lot decisions',await desk().getByRole('button',{name:/^Place hold on /}).first().isDisabled()&&(await desk().innerText()).includes('Add your name and decision reason'));await desk().scrollIntoViewIfNeeded();await capture('desktop-empty-dispatcher-direction');
  pending=nextPost('/api/delivery-outlook');await desk().getByRole('button',{name:'Choose a response plan',exact:true}).click();await settledOutlook(await pending);check('empty desk CTA returns to actual Command without creating an approval',await outlook().isVisible());await page.waitForFunction(()=>document.activeElement?.id==='command-scenarios');check('empty Dispatcher CTA directly focuses the response-plan table',await page.locator('#command-scenarios').isVisible()&&await page.getByRole('dialog').count()===0);
  phase='mobile_guidance';await page.setViewportSize({width:390,height:844});await outlook().scrollIntoViewIfNeeded();await noOverflow('mobile delivery outlook has no horizontal page overflow');await capture('mobile-delivery-outlook');
  await nav().getByRole('button',{name:'Evidence assistant',exact:true}).click();await assistant().getByRole('button',{name:'Chicken',exact:true}).waitFor();pending=nextPost('/api/assistant/interpret');await assistant().getByRole('button',{name:'Chicken',exact:true}).click();reply=await pending;check('mobile example gives actual useful choices',reply.ok()&&(await reply.json()).kind==='clarification');await choice.waitFor();await choice.scrollIntoViewIfNeeded();await noOverflow('mobile short-question guidance has no horizontal overflow');await capture('mobile-chicken-choices');
  await nav().getByRole('button',{name:'Road intelligence',exact:true}).click();await road().getByRole('button',{name:'Compare this journey',exact:true}).waitFor();await road().locator('.journey-steps').scrollIntoViewIfNeeded();await noOverflow('mobile road guidance has no horizontal page overflow');await capture('mobile-road-steps');
  phase='immutability';check('all browser POSTs were allowed read-only computations',result.post_requests.length>0&&result.post_requests.every(request=>request.allowed)&&result.blocked_requests.length===0);
  check('no actual JavaScript or local HTTP errors',result.page_errors.length===0&&result.console_errors.length===0&&result.http_failures.length===0&&result.request_failures.length===0,JSON.stringify({page:result.page_errors,console:result.console_errors,http:result.http_failures,requests:result.request_failures}));
  result.network_after=await get('/api/network');result.assignments_after=await get('/api/driver');check('all guided planning leaves network and assignments unchanged',same(baselineNetwork,result.network_after)&&same(baselineAssignments,result.assignments_after));
  result.isolated_after=await database(isolated);result.operator_after=await database(path.join(root,'data/aegis.sqlite'));result.fixtures_after=await tree('data/fixtures');result.cache_after=await tree('data/cache');
  check('isolated database and sidecars unchanged',same(result.isolated_before,result.isolated_after));check('operator database and sidecars untouched',same(result.operator_before,result.operator_after));check('source fixtures and caches unchanged',same(result.fixtures_before,result.fixtures_after)&&same(result.cache_before,result.cache_after));
  result.passed=true;
}catch(error){result.passed=false;result.failure={phase,message:error.stack||String(error)};if(page)try{await page.screenshot({path:path.join(folder,'failure.png'),fullPage:false});}catch{}process.exitCode=1;}
finally{if(isolated&&!result.isolated_after)result.isolated_after=await database(isolated);if(!result.operator_after)result.operator_after=await database(path.join(root,'data/aegis.sqlite'));await save('results',result);await fs.writeFile(path.join(root,'reports/friendliness_workflow_evaluation.json'),JSON.stringify(result,null,2)+'\n');await browser?.close();console.log(JSON.stringify({passed:result.passed,checks:result.checks.length,failed:result.checks.filter(item=>!item.passed),failure:result.failure,report:'reports/friendliness_workflow_evaluation.json'},null,2));}
