/** Real-browser checks. Mutation is explicitly restricted to isolated port 8001. */
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '../.tools/browser-qa/node_modules/playwright-core/index.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const args=process.argv.slice(2);
const value=(key,fallback)=>{const i=args.indexOf(key);return i<0?fallback:args[i+1];};
const base=value('--base-url','http://127.0.0.1:8000').replace(/\/$/,'');
const workflow=args.includes('--workflow');
const routeLab=args.includes('--route-lab');
const reportDir=path.join(root,'reports/browser_qa',value('--run','baseline'));
if(workflow && !/^http:\/\/127\.0\.0\.1:8001$/.test(base))throw new Error('Workflow mutations require the isolated QA server at 127.0.0.1:8001.');
await fs.mkdir(reportDir,{recursive:true});
const result={base_url:base,checked_at:new Date().toISOString(),workflow_isolated:workflow,browser:'installed Chrome',checks:[],page_errors:[],console_errors:[],request_failures:[],http_failures:[],screenshots:[]};
const check=(name,passed,details)=>{result.checks.push({name,passed,details});if(!passed)throw new Error(`${name}: ${details}`);};
let browser;
try{
  browser=await chromium.launch({executablePath:process.env.AEGIS_CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
  result.browser_version=browser.version();
  const context=await browser.newContext({viewport:{width:1440,height:1000},locale:'en-US',timezoneId:'America/Chicago'});
  if(workflow){const reset=await context.request.post(`${base}/api/demo/reset`);check('isolated_demo_reset',reset.ok(),'Only the explicitly isolated QA database is reset');}
  const page=await context.newPage();
  page.on('pageerror',error=>result.page_errors.push(error.stack||error.message));
  page.on('console',message=>{if(message.type()==='error')result.console_errors.push(message.text());});
  page.on('requestfailed',request=>result.request_failures.push({url:request.url(),failure:request.failure()?.errorText}));
  page.on('response',response=>{if(response.status()>=400)result.http_failures.push({url:response.url(),status:response.status()});});
  const capture=async(name)=>{
    if(name.includes('farm-') || name.includes('regional-')){
      const evidenceTop=await page.locator('.lab-unserved').evaluate(element=>element.getBoundingClientRect().top+scrollY);
      await page.evaluate(top=>window.scrollTo(0,Math.max(0,top-100)),evidenceTop);
      await page.waitForFunction(()=>document.querySelectorAll('.lab-map .leaflet-tile-loaded').length>0,undefined,{timeout:8000}).catch(()=>{});
    }else if(name!=='desktop-approval')await page.evaluate(()=>window.scrollTo(0,0));
    await page.waitForTimeout(180);
    await page.screenshot({path:path.join(reportDir,`${name}.png`),fullPage:false});result.screenshots.push(`${name}.png`);
  };
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.getByRole('heading',{name:'Regional command center',exact:true}).waitFor();
  await page.getByRole('heading',{name:'Distribution network',exact:true}).waitFor();
  await page.locator('.leaflet-container').waitFor();
  await page.waitForFunction(()=>document.querySelectorAll('.leaflet-tile-loaded').length>0,undefined,{timeout:12000}).catch(()=>{});
  const tiles=await page.locator('.leaflet-tile-loaded').count();
  check('desktop_command_loaded',true,'React data view and Leaflet container visible');
  result.checks.push({name:'map_tiles_loaded',passed:tiles>0,details:`${tiles} loaded tiles; tile access requires external connectivity`});
  const mapPaths=await page.locator('.leaflet-overlay-pane path').count();
  check('map_network_geometry_rendered',mapPaths>0,`${mapPaths} SVG operational/evidence geometries`);
  await capture('desktop-command');
  for(const [button,heading,screenshot] of [['Sources & evidence','Evidence with a clear origin','desktop-evidence'],['Model evaluation','Measured model performance','desktop-model']]){
    await page.getByRole('button',{name:button,exact:true}).click();
    await page.getByRole('heading',{name:heading,exact:true}).waitFor();
    await capture(screenshot);
    check(`${screenshot}_loaded`,true,heading);
  }
  if(routeLab){
    await page.getByRole('button',{name:/Route laboratory/}).click();
    await page.getByRole('heading',{name:'Test the journey ahead',exact:true}).waitFor();
    const plan=async()=>{
      const pending=page.waitForResponse(r=>r.url().endsWith('/api/route-lab') && r.request().method()==='POST');
      await page.getByRole('button',{name:'Test dispatch plan',exact:true}).click();
      const response=await pending;check('route_lab_http_success',response.ok(),`HTTP ${response.status()}`);
      const data=await response.json();await page.locator('.lab-summary').waitFor();return data;
    };
    const farm=await plan();
    check('single_farm_routes_inspectable',farm.preset.origins.length===1 && farm.routes.length>0 && farm.summary.constraint_violations===0,`${farm.routes.length} routes from one farm; ${farm.summary.constraint_violations} violations`);
    check('route_test_does_not_dispatch',farm.mutates_assignments===false,'No driver assignments changed by route laboratory');
    check('unmet_demand_and_held_exclusion_visible',await page.getByText('300 kg unmet demand',{exact:true}).isVisible() && /FD08 \(held\)/.test(await page.locator('.lab-unserved').innerText()),'300 kg unmet demand and FD08 (held) are explicit above the map');
    await capture('desktop-farm-routes');
    await page.getByLabel('Available trucks',{exact:true}).fill('1');
    await page.getByLabel('Capacity per truck (kg)',{exact:true}).fill('100');
    const constrained=await plan();
    check('reduced_capacity_exposes_unmet_demand',constrained.summary.unmet_demand_kg>farm.summary.unmet_demand_kg && constrained.summary.constraint_violations===0,`${constrained.summary.unmet_demand_kg} kg unmet; ${constrained.summary.constraint_violations} violations`);
    await page.getByLabel('Available trucks',{exact:true}).fill('3');
    await page.getByLabel('Capacity per truck (kg)',{exact:true}).fill('1500');
    await page.getByLabel('Simulate refrigeration failure').check();
    await page.getByLabel('Additional road delay (minutes)').fill('90');
    const fault=await plan();
    check('cold_chain_fault_prompts_review',fault.routes.some(r=>r.cold_chain.status==='review' && r.cold_chain.time_above_threshold_minutes>0),'Fault changes an explicitly uncalibrated temperature projection');
    await capture('desktop-farm-fault');
    await page.getByRole('button',{name:/^Multi-location fleet/}).click();
    const fleet=await plan();
    const origins=[...new Set(fleet.routes.map(r=>r.origin_id))];
    check('fleet_uses_multiple_origins',fleet.preset.origins.length>1 && origins.length>1,`${fleet.routes.length} active routes across ${origins.length} origins`);
    check('fleet_constraints_hold',fleet.summary.constraint_violations===0,`${fleet.summary.constraint_violations} violations`);
    await capture('desktop-regional-routes');
    await page.setViewportSize({width:390,height:844});
    const labSizes=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth}));
    check('mobile_route_lab_no_document_overflow',labSizes.document<=labSizes.viewport,JSON.stringify(labSizes));
    await capture('mobile-route-laboratory');
    await page.setViewportSize({width:1440,height:1000});
  }
  if(workflow){
    await page.getByRole('button',{name:'Command center',exact:true}).click();
    await page.locator('.scenario-panel .text-button').nth(2).click();
    await page.getByRole('dialog').waitFor();
    const approve=page.getByRole('button',{name:'Approve simulated plan',exact:true});
    check('approval_requires_actor_reason',await approve.isDisabled(),'Approval blocked until fields are completed');
    await page.getByLabel('Dispatcher name',{exact:true}).fill('Browser QA dispatcher');
    await page.getByLabel('Reason for approval',{exact:true}).fill('Isolated browser rehearsal: reviewed simulated capacity, eligibility and precautionary holds');
    await capture('desktop-approval');
    await approve.click();
    await page.getByText('Scenario approved. Driver assignments updated and audit recorded.',{exact:true}).waitFor();
    const assignmentResponse=await context.request.get(`${base}/api/driver`);
    const assignments=await assignmentResponse.json();
    check('approval_publishes_assignments',assignments.length>0,`${assignments.length} simulated assignments`);
    await page.setViewportSize({width:390,height:844});
    await page.getByRole('button',{name:'AEGIS Drive',exact:true}).click();
    await page.getByLabel('Simulated driver truck').selectOption(assignments[0].truck_id);
    await page.getByRole('button',{name:'Acknowledge assignment',exact:true}).first().click();
    await page.getByRole('button',{name:'Assignment acknowledged',exact:true}).first().waitFor();
    await page.getByLabel('Report a driver incident').fill('Parked safely during isolated browser QA; requesting simulated dispatcher review');
    await page.getByRole('button',{name:'Send to dispatcher',exact:true}).click();
    await page.getByText('Incident submitted for dispatcher review.',{exact:true}).waitFor();
    const audit=await (await context.request.get(`${base}/api/audit`)).json();
    check('driver_acknowledgment_persisted',audit.some(row=>row.action==='acknowledge'),'Audit contains acknowledgment');
    check('driver_incident_persisted',audit.some(row=>row.action==='incident'),'Audit contains incident report');
  } else {
    await page.setViewportSize({width:390,height:844});
    await page.getByRole('button',{name:'AEGIS Drive',exact:true}).click();
  }
  await page.getByRole('heading',{name:'Your assigned journey',exact:true}).waitFor();
  check('driver_parked_instruction_visible',await page.getByText('Use only while safely parked.',{exact:true}).isVisible(),'Parked-use instruction visible');
  const sizes=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth}));
  check('mobile_no_document_horizontal_overflow',sizes.document<=sizes.viewport,JSON.stringify(sizes));
  await capture('mobile-drive');
  check('no_uncaught_browser_errors',result.page_errors.length===0,JSON.stringify(result.page_errors));
  const resourceFailures=result.http_failures.filter(item=>!item.url.endsWith('/favicon.ico'));
  check('no_application_resource_failures',resourceFailures.length===0,JSON.stringify(resourceFailures));
  result.passed=result.checks.every(item=>item.passed);
  if(!result.passed)process.exitCode=1;
  await context.close();
}catch(error){result.passed=false;result.error=String(error);process.exitCode=1;}
finally{
  if(browser)await browser.close();
  await fs.writeFile(path.join(reportDir,'results.json'),JSON.stringify(result,null,2));
  console.log(JSON.stringify(result,null,2));
}
