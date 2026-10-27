/** Broader control checks; mutations are restricted to the isolated port 8001 app. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from '../.tools/browser-qa/node_modules/playwright-core/index.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const base='http://127.0.0.1:8001';const folder=path.join(root,'reports/browser_qa/controls');await fs.mkdir(folder,{recursive:true});
const result={checked_at:new Date().toISOString(),base_url:base,isolated_database:true,checks:[],page_errors:[],http_failures:[],source_actions:[],screenshots:[]};
const check=(name,passed,details='')=>{result.checks.push({name,passed,details});if(!passed)throw new Error(name+': '+details);};
let browser,page;
try {
  browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
  const context=await browser.newContext({viewport:{width:1440,height:1000},timezoneId:'America/Chicago'});
  page=await context.newPage();page.setDefaultTimeout(20000);
  page.on('pageerror',e=>result.page_errors.push(e.message));
  page.on('response',r=>{if(r.status()>=400&&r.url().startsWith(base))result.http_failures.push({url:r.url(),status:r.status()});});
  const read=async endpoint=>{const r=await context.request.get(base+endpoint);if(!r.ok())throw new Error(endpoint+' '+r.status());return r.json();};
  const action=async(endpoint,fn,timeout=30000)=>{const pending=page.waitForResponse(r=>r.url().endsWith(endpoint)&&r.request().method()==='POST',{timeout});await fn();const r=await pending;check(endpoint,r.ok(),`HTTP ${r.status()}`);return r.json();};
  await page.goto(base,{waitUntil:'domcontentloaded'});await page.getByRole('heading',{name:'Regional command center',exact:true}).waitFor();
  for(const label of ['Simulated logistics','FSIS establishments','NWS alert geometry','MoDOT incident geometry','Route geometry']) {
    const box=page.getByLabel(label,{exact:true});await box.uncheck();check('layer_off_'+label,!(await box.isChecked()));await box.check();check('layer_on_'+label,await box.isChecked());
  }
  const map=page.locator('.network-map');
  await map.locator('.leaflet-control-zoom-in').click();await map.locator('.leaflet-control-zoom-out').click();check('map_zoom_controls_usable',await map.isVisible());
  const reset=()=>action('/api/demo/reset',()=>page.getByRole('button',{name:'Reset demo',exact:true}).click());await reset();
  for(const scenario of ['A','B','D']) {
    const row=page.locator('.scenario-panel tbody tr').filter({has:page.locator('.scenario-letter',{hasText:scenario})});
    await action('/api/proposals/'+scenario,()=>row.getByRole('button',{name:'Review',exact:false}).click());
    await page.getByRole('dialog').waitFor();check('proposal_'+scenario+'_requires_identity',await page.getByRole('button',{name:'Approve simulated plan',exact:true}).isDisabled());
    if(scenario==='B')await page.getByRole('button',{name:'Close proposal',exact:true}).click();else await page.getByRole('button',{name:'Keep under review',exact:true}).click();
    check('proposal_'+scenario+'_closed',await page.getByRole('dialog').count()===0);
  }
  const cRow=page.locator('.scenario-panel tbody tr').filter({has:page.locator('.scenario-letter',{hasText:'C'})});
  const proposal=await action('/api/proposals/C',()=>cRow.getByRole('button',{name:'Review',exact:false}).click());
  await page.getByLabel('Dispatcher name',{exact:true}).fill('Control QA dispatcher');await page.getByLabel('Reason for approval',{exact:true}).fill('Reviewed simulated excursion evidence and proposed precautionary holds');
  await action(`/api/proposals/${proposal.id}/approve`,()=>page.getByRole('button',{name:'Approve simulated plan',exact:true}).click());
  const held=await read('/api/network');check('scenario_C_holds_are_explicitly_approved',proposal.proposed_hold_lots.length>0&&proposal.proposed_hold_lots.every(id=>held.lots.find(l=>l.id===id)?.held));
  check('scenario_C_never_assigns_held_lots',(await read('/api/driver')).every(s=>!held.lots.find(l=>l.id===s.lot_id).held));
  for(const event of ['road_closure','severe_weather','delivery_delay','refrigeration_fault','temperature_excursion','inventory_shortage']) {
    await reset();await page.getByLabel('Select shipment',{exact:true}).selectOption('SH03');await page.getByLabel('Event type',{exact:true}).selectOption(event);
    await action('/api/events',()=>page.getByRole('button',{name:'Introduce event',exact:true}).click());
    const n=await read('/api/network');check('event_'+event+'_changes_actual_simulation',n.events.length===1&&n.events[0].type===event&&n.events[0].shipment_id==='SH03');
    check('event_'+event+'_invalidates_assignments',(await read('/api/driver')).length===0);
  }
  await reset();await page.getByRole('button',{name:'Recompute',exact:true}).click();
  await page.getByRole('button',{name:'Sources & evidence',exact:true}).click();await page.getByRole('heading',{name:'Inspect the underlying evidence',exact:true}).waitFor();
  await page.getByLabel('Dataset',{exact:true}).selectOption('fsis_poultry');
  await page.getByRole('button',{name:'Next rows',exact:true}).click();await page.getByText(/Showing 26/).waitFor();
  check('source_next_page_works',(await page.locator('.data-explorer').innerText()).includes('Showing 26'));
  await page.getByRole('button',{name:'Previous rows',exact:true}).click();await page.getByText(/Showing 1/).first().waitFor();
  await page.getByLabel('Filter column',{exact:true}).selectOption('establishment_state');await page.getByLabel('Contains text',{exact:true}).fill('MO');await page.getByRole('button',{name:'Apply source filter',exact:true}).click();
  await page.getByRole('button',{name:'Clear filter',exact:true}).click();await page.getByText('78,607 matching rows.',{exact:false}).waitFor();check('source_filter_can_be_cleared',true);
  const sources=[['openmeteo','Open-Meteo forecast'],['nws_alerts','NWS official alerts'],['ncei_historical','NCEI historical observations'],['fsis_recalls','FSIS official recalls'],['modot','MoDOT traveler information']];
  for(const [key,title] of sources) {
    const card=page.locator('.source-card').filter({has:page.getByRole('heading',{name:title,exact:true})});
    const response=await action('/api/refresh/'+key+'?summary=true',()=>card.getByRole('button',{name:'Refresh',exact:true}).click(),240000);
    result.source_actions.push({source:key,retrieved_at:response.retrieved_at,cache:response.cache,stale:response.stale,refresh_error:response.refresh_error,status:response.status});
    const fresh=response.status!=='failed'&&!response.stale&&!response.refresh_error;
    if(fresh)await page.getByText(`${title} source check completed. Read the response retrieval time and coverage.`,{exact:true}).waitFor();
    else await page.getByRole('alert').waitFor();
    check('source_refresh_'+key+'_reports_actual_outcome',true,fresh?'Usable dated response; cache status retained':'Explicit failure/fallback shown');
  }
  await page.screenshot({path:path.join(folder,'source-refresh-controls.png'),fullPage:false});result.screenshots.push('source-refresh-controls.png');
  const icon=await context.request.get(base+'/favicon.svg');check('favicon_is_served',icon.ok()&&(await icon.text()).includes('<svg'));
  check('no_uncaught_javascript',result.page_errors.length===0,JSON.stringify(result.page_errors));check('no_app_http_failures',result.http_failures.length===0,JSON.stringify(result.http_failures));result.passed=true;
} catch(e) {result.passed=false;result.error=String(e);process.exitCode=1;if(page)await page.screenshot({path:path.join(folder,'failure.png'),fullPage:false}).catch(()=>{});}
finally {if(browser)await browser.close();result.finished_at=new Date().toISOString();await fs.writeFile(path.join(folder,'results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify({passed:result.passed,checks:result.checks.length,error:result.error,source_actions:result.source_actions},null,2));}
