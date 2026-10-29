/** Actual Chrome checks for Command's action/results workflow.
 * Operational mutations are confined to a verified isolated offline session on
 * port 8014. One two-alternative response is explicitly browser-injected; real
 * route checks use the actual offline endpoint. No provider/model is called.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';
import { chromium } from '../.tools/browser-qa/node_modules/playwright-core/index.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const base = 'http://127.0.0.1:8014';
const folder = path.join(root, 'reports/browser_qa/command_workflow');
const downloads = path.join(root, '.tools/command-workflow-downloads');
const launch = JSON.parse((await fs.readFile(path.join(root, '.tools/command-qa-launch.json'), 'utf8')).replace(/^\uFEFF/, ''));
if (launch.port !== 8014 || launch.environment.AEGIS_OFFLINE_DEMO !== '1') throw new Error('Expected the reserved isolated offline session');
await fs.mkdir(folder, { recursive: true }); await fs.mkdir(downloads, { recursive: true });
const hash = body => createHash('sha256').update(body).digest('hex');
const canonical = value => JSON.stringify(value, (_key, item) => item && typeof item === 'object' && !Array.isArray(item) ? Object.fromEntries(Object.keys(item).sort().map(key => [key, item[key]])) : item);
const same = (left, right) => canonical(left) === canonical(right);
const normal = value => value.replace(/\s+/g, ' ').trim();
const save = async (name, value) => fs.writeFile(path.join(folder, name + '.json'), JSON.stringify(value, null, 2) + '\n');
async function fingerprint(filename) { try { const body = await fs.readFile(filename); return { exists: true, bytes: body.length, sha256: hash(body) }; } catch (error) { if (error.code === 'ENOENT') return { exists: false }; throw error; } }
async function database(filename) { return Object.fromEntries(await Promise.all(['', '-wal', '-shm', '-journal'].map(async suffix => [suffix || 'sqlite', await fingerprint(filename + suffix)]))); }
async function tree(relative) {
  const found = {};
  async function visit(directory) { let entries; try { entries = await fs.readdir(directory, { withFileTypes: true }); } catch (error) { if (error.code === 'ENOENT') return; throw error; }
    for (const entry of entries) { const filename = path.join(directory, entry.name); if (entry.isDirectory()) await visit(filename); else if (entry.isFile()) found[path.relative(root, filename).replaceAll('\\', '/')] = await fingerprint(filename); }
  }
  await visit(path.join(root, relative)); return found;
}
const result = { checked_at: new Date().toISOString(), base_url: base, isolated: true, offline: true, rehearsal_id: launch.rehearsal_id, actual_llm_queried: false, source_refresh_requested: false, actual_osrm_queried: false, checks: [], screenshots: [], page_errors: [], console_errors: [], http_failures: [], expected_api_rejections: [], expected_injected_failures: [], allowed_external_tile_failures: [], post_requests: [], control_api_requests: [], injected_cases: [] };
const check = (name, passed, detail = '') => { result.checks.push({ name, passed, detail }); if (!passed) throw new Error(`${name}: ${detail}`); };
let browser, page, context, phase = 'startup';
const operatorPath = path.join(root, 'data/aegis.sqlite');
const isolatedPath = path.resolve(launch.database_path);
if (isolatedPath === operatorPath || !isolatedPath.startsWith(path.join(root, 'data/rehearsals') + path.sep)) throw new Error('Refusing an unsafe QA database path');

const referenceCode = `import copy,json,sys
from backend.optimization import optimize
from backend.simulation import apply_event
q=json.load(sys.stdin);n=copy.deepcopy(q['network']);apply_event(n,q['event'],q['shipment_id'])
print(json.dumps({'network':n,'scenarios':[optimize(n,k) for k in ('A','B','C','D')]}))`;
async function independentReference(network, event, shipment_id) {
  return new Promise((resolve, reject) => {
    const child = spawn(path.join(root, '.venv/Scripts/python.exe'), ['-c', referenceCode], { cwd: root, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] });
    let output = '', errors = ''; const timer = setTimeout(() => { child.kill(); reject(new Error('Pure reference solver exceeded 30 seconds')); }, 30000);
    child.stdout.on('data', body => { output += body; if (output.length > 2 * 1024 * 1024) child.kill(); }); child.stderr.on('data', body => { errors += body; });
    child.on('error', error => { clearTimeout(timer); reject(error); }); child.on('close', code => { clearTimeout(timer); if (code !== 0) reject(new Error(`Pure reference solver failed (${code}): ${errors.slice(0, 500)}`)); else { try { resolve(JSON.parse(output)); } catch (error) { reject(error); } } });
    child.stdin.end(JSON.stringify({ network, event, shipment_id }));
  });
}

try {
  result.operator_database_before = await database(operatorPath);
  result.fixtures_before = await tree('data/fixtures'); result.cache_before = await tree('data/cache');
  browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  result.browser_version = browser.version();
  context = await browser.newContext({ viewport: { width: 1440, height: 1050 }, locale: 'en-US', timezoneId: 'America/Chicago', acceptDownloads: true });
  const request = async (endpoint, body, expectedStatus = 200) => {
    if (!endpoint.startsWith('/api/')) throw new Error('Only local application APIs are permitted');
    const response = body === undefined ? await context.request.get(base + endpoint) : await context.request.post(base + endpoint, { data: body });
    result.control_api_requests.push({ method: body === undefined ? 'GET' : 'POST', endpoint, phase, status: response.status() });
    check(`${phase}: control ${endpoint}`, response.status() === expectedStatus, `HTTP ${response.status()}`); return response.json();
  };
  const runtime = await request('/api/runtime-context');
  check('verified_isolated_offline_runtime', runtime.isolated === true && runtime.offline === true && runtime.mode === 'isolated_rehearsal' && runtime.rehearsal_id === launch.rehearsal_id && runtime.database_relative_path === launch.database_relative_path);
  result.runtime = runtime;
  // Establish a repeatable seed only after verifying the reserved isolated runtime.
  // This deliberately clears this QA session's previous assignments on reruns.
  result.isolated_setup_reset = await request('/api/demo/reset', {});
  result.isolated_database_before = await database(isolatedPath);
  page = await context.newPage(); page.setDefaultTimeout(20000);
  page.on('pageerror', error => result.page_errors.push({ phase, message: error.message }));
  page.on('console', message => {
    if (message.type() !== 'error') return;
    const item = { phase, message: message.text(), location: message.location() };
    if (item.location.url.includes('tile.openstreetmap.org')) result.allowed_external_tile_failures.push(item);
    else if (phase === 'stale_approval' && (item.message.includes('409') || item.location.url.includes('/approve'))) result.expected_api_rejections.push({ console: item });
    else if (phase === 'confirmed_receipt_network_failure' && item.message.includes('503') && item.location.url.includes('/api/network')) result.expected_injected_failures.push({ console: item });
    else result.console_errors.push(item);
  });
  page.on('response', response => {
    if (response.status() < 400) return;
    const item = { phase, url: response.url(), status: response.status() };
    if (response.url().includes('tile.openstreetmap.org')) result.allowed_external_tile_failures.push(item);
    else if (response.headers()['x-aegis-browser-qa'] === 'receipt-network-failure' && response.status() === 503 && new URL(response.url()).pathname === '/api/network') result.expected_injected_failures.push(item);
    else if (response.url().startsWith(base) && phase === 'stale_approval' && response.status() === 409 && response.url().endsWith('/approve')) result.expected_api_rejections.push(item);
    else if (response.url().startsWith(base)) result.http_failures.push(item);
  });
  page.on('request', request => { if (request.method() === 'POST') { const url = new URL(request.url()); if (url.origin !== base) throw new Error('A browser POST escaped the isolated app'); result.post_requests.push({ phase, path: url.pathname, body: request.postDataJSON() }); } });
  const guide = () => page.getByRole('complementary', { name: 'Workspace guide' });
  const impact = () => page.getByRole('region', { name: 'Preview a disruption before applying it' });
  const navigation = () => page.getByRole('navigation', { name: 'Main navigation' });
  const capture = async name => { await page.screenshot({ path: path.join(folder, name + '.png'), fullPage: false }); result.screenshots.push(name + '.png'); };
  const overflow = async name => { const value = await page.evaluate(() => ({ viewport: innerWidth, scroll: document.documentElement.scrollWidth })); check(name, value.scroll <= value.viewport, JSON.stringify(value)); };
  const focused = async id => { await page.waitForFunction(value => document.activeElement?.id === value, id); check(`${phase}: visible focus ${id}`, await page.locator('#' + id).isVisible()); };
  const responseFor = endpoint => page.waitForResponse(response => new URL(response.url()).pathname === endpoint && response.request().method() === 'POST');
  const waitIdle = () => page.getByRole('button', { name: 'Recompute', exact: true }).waitFor({ state: 'visible' });
  const exportJSON = async (button, name) => { const pending = page.waitForEvent('download'); await button.click(); const download = await pending; const destination = path.join(downloads, name); await download.saveAs(destination); const value = JSON.parse(await fs.readFile(destination, 'utf8')); await save(name.replace(/\.json$/, ''), value); return value; };
  async function command() { await navigation().getByRole('button', { name: 'Command center', exact: true }).click(); await page.getByRole('combobox', { name: 'Select shipment', exact: true }).waitFor(); await waitIdle(); }
  async function refresh() { const pending = page.waitForResponse(response => new URL(response.url()).pathname === '/api/scenarios'); await page.getByRole('button', { name: 'Recompute', exact: true }).click(); await pending; await page.locator('#command-scenarios .command-inline-status').filter({ hasText: 'Last computation' }).waitFor(); await waitIdle(); }
  async function approveScenario(scenario, name) {
    const prepared = responseFor('/api/proposals/' + scenario); await page.getByRole('button', { name: 'Review scenario ' + scenario, exact: true }).click(); const proposalResponse = await prepared; check(`${phase}: proposal produced`, proposalResponse.ok()); const proposal = await proposalResponse.json();
    const dialog = page.getByRole('dialog', { name: 'Review scenario ' + scenario, exact: true }); await dialog.waitFor();
    check(`${phase}: approval initially gated`, await dialog.getByRole('button', { name: 'Approve simulated plan', exact: true }).isDisabled());
    await dialog.getByLabel('Dispatcher name', { exact: true }).fill(name); await dialog.getByLabel('Reason for approval', { exact: true }).fill('Isolated browser exercise: reviewed simulated safety and capacity constraints.');
    const pending = responseFor('/api/proposals/' + proposal.id + '/approve'); await dialog.getByRole('button', { name: 'Approve simulated plan', exact: true }).click(); const response = await pending; check(`${phase}: actual approval accepted`, response.ok()); await dialog.waitFor({ state: 'hidden' }); await waitIdle();
    const assignments = await request('/api/driver'); check(`${phase}: published exact proposal assignments`, assignments.length === proposal.shipments.length && proposal.shipments.every(row => assignments.some(item => item.id === row.id && item.lot_id === row.lot_id && item.truck_id === row.truck_id)));
    return { proposal, assignments, receipt: await response.json() };
  }
  async function preview(event, before) {
    await impact().getByRole('combobox', { name: 'Event type', exact: true }).selectOption(event);
    const unchanged = await database(isolatedPath), beforePosts = result.post_requests.length;
    const pending = responseFor('/api/events/preview'); await impact().getByRole('button', { name: 'Preview event impact', exact: true }).click(); const response = await pending;
    check(`${phase}: preview HTTP success`, response.ok()); const value = await response.json(); await impact().getByText(`Preview produced for SH11 · revision ${before.revision}.`, { exact: true }).waitFor();
    check(`${phase}: preview contract`, value.read_only && value.simulation && !value.operational_state_modified && value.event === event && value.shipment_id === 'SH11' && value.network_revision === before.revision && value.scenarios.length === 4);
    check(`${phase}: actual preview did not alter SQLite or sidecars`, same(unchanged, await database(isolatedPath)));
    check(`${phase}: only preview was posted`, result.post_requests.slice(beforePosts).every(row => row.path === '/api/events/preview'));
    check(`${phase}: explicit apply remains gated`, await impact().getByRole('button', { name: 'Apply previewed event', exact: true }).isDisabled());
    check(`${phase}: geometry limit visible`, await impact().getByText('Road geometry and stop order stay unchanged.', { exact: true }).isVisible());
    return value;
  }

  phase = 'desktop_orientation'; await page.goto(base + '/', { waitUntil: 'domcontentloaded' }); await page.getByRole('combobox', { name: 'Select shipment', exact: true }).waitFor(); await waitIdle();
  result.frontend_assets = await page.evaluate(() => ({ scripts: [...document.querySelectorAll('script[src]')].map(item => item.getAttribute('src')), styles: [...document.querySelectorAll('link[rel="stylesheet"]')].map(item => item.getAttribute('href')) }));
  check('Command guide explains actual scope', (await guide().innerText()).includes('current simulated distribution network') && (await guide().innerText()).includes('explicit apply or approval'));
  await guide().locator('summary').click(); check('Command connections explain separate route and approval', (await guide().innerText()).includes('does not change a truck assignment') && (await guide().innerText()).includes('clears approved assignments'));
  check('candidate framing and historical chart distinction', (await page.locator('#command-trip-detail').innerText()).includes('CANDIDATE TRUCK') && (await page.locator('#command-trip-detail').innerText()).includes('seeded historical simulation trace'));
  await guide().scrollIntoViewIfNeeded(); await capture('desktop-command-orientation'); await overflow('desktop command has no page overflow');
  await page.getByRole('button', { name: 'Open review queue', exact: true }).click(); await focused('command-review-queue');
  await page.getByRole('button', { name: 'Inspect SH03', exact: true }).click(); await focused('command-trip-detail'); check('queue action selects actual excursion candidate', await page.getByRole('combobox', { name: 'Select shipment', exact: true }).inputValue() === 'SH03');
  await page.getByRole('button', { name: 'Open review queue', exact: true }).click(); await page.getByRole('button', { name: 'Open lot review', exact: true }).click(); check('lot queue action opens dispatcher', await guide().getByRole('heading', { name: 'Turn review into a recorded decision', exact: true }).isVisible()); await command();
  phase = 'recompute'; const beforeRecompute = await request('/api/network'); const beforeRecomputeDB = await database(isolatedPath); await refresh();
  check('recompute shows completed identical result receipt', (await page.locator('#command-scenarios .command-inline-status').innerText()).includes('Totals and selected trips match the previous run; nothing was approved.'));
  check('recompute does not alter network or SQLite', same(beforeRecompute, await request('/api/network')) && same(beforeRecomputeDB, await database(isolatedPath)));
  phase = 'scenario_overlay'; const beforeOverlay = await database(isolatedPath), postCount = result.post_requests.length;
  await page.getByRole('button', { name: 'Show scenario D allocation on map', exact: true }).click(); await focused('command-network-map');
  check('scenario D overlay selection visible', await page.getByRole('combobox', { name: 'Map allocation', exact: true }).inputValue() === 'D' && (await page.locator('.command-map-caption').innerText()).includes('proposed allocation'));
  check('overlay never creates a proposal or assignment', result.post_requests.length === postCount && same(beforeOverlay, await database(isolatedPath)));
  await capture('desktop-scenario-allocation-map');
  await page.getByRole('combobox', { name: 'Map allocation', exact: true }).selectOption('approved'); check('empty approved map does not show candidates as dispatch', (await page.locator('.command-map-caption').innerText()).includes('0 approved assignment connections shown'));
  await page.getByRole('combobox', { name: 'Map allocation', exact: true }).selectOption('candidates');

  phase = 'actual_offline_route'; await page.getByRole('combobox', { name: 'Select shipment', exact: true }).selectOption('SH11'); const routeDB = await database(isolatedPath); let actualRoute;
  for (let repeat = 0; repeat < 2; repeat++) { const pending = responseFor('/api/route'); await page.getByRole('button', { name: 'Request road route', exact: true }).click(); const response = await pending; check(`offline route ${repeat + 1} actual endpoint`, response.ok()); actualRoute = await response.json(); await focused('command-route-result'); check(`offline route ${repeat + 1} usable labeled fallback`, actualRoute.fallback === true && actualRoute.payload.routes.length >= 1 && (await page.locator('#command-route-result').innerText()).includes('Estimated fallback')); }
  result.actual_route = { fallback: actualRoute.fallback, provenance: actualRoute.provenance, alternatives: actualRoute.payload.routes.length };
  const exportedRoute = await exportJSON(page.getByRole('button', { name: 'Export route comparison JSON', exact: true }), 'actual-route-export.json');
  check('route export preserves actual payload and captured scope', exportedRoute.captured_export === true && exportedRoute.operational_state_modified === false && exportedRoute.shipmentId === 'SH11' && exportedRoute.selected_alternative === 0 && same(exportedRoute.payload, actualRoute.payload));
  await page.getByRole('button', { name: 'Focus route map', exact: true }).click(); await focused('command-network-map');
  check('actual route has a visible highlighted SVG path', await page.locator('.network-map path[stroke="#b47a35"][stroke-width="5"]').count() === 1);
  check('route requests and exports leave operational database unchanged', same(routeDB, await database(isolatedPath))); await capture('desktop-actual-fallback-route-map');

  phase = 'injected_alternative_UI';
  const injected = structuredClone(actualRoute); const second = structuredClone(injected.payload.routes[0]); const [start, end] = second.geometry.coordinates; second.geometry.coordinates = [start, [(start[0] + end[0]) / 2 + .15, (start[1] + end[1]) / 2 + .08], end]; second.distance *= 1.15; second.duration *= 1.1; injected.payload.routes.push(second); injected.provenance = 'Explicit browser-injected two-alternative fixture; no actual OSRM call';
  result.injected_cases.push({ phase, scope: 'Route response fulfilled in browser only to check alternative selection; not provider data or actual OSRM success' }); await save('injected-two-alternative-fixture', injected);
  await page.route('**/api/route', route => route.fulfill({ status: 200, contentType: 'application/json', headers: { 'x-aegis-browser-qa': 'injected-alternative' }, body: JSON.stringify(injected) }));
  let pending = responseFor('/api/route'); await page.getByRole('button', { name: 'Request road route', exact: true }).click(); await pending; await focused('command-route-result'); await page.getByRole('button', { name: 'Highlight alternative 2', exact: true }).click();
  check('injected alternative selection produces a visible selected result', await page.getByRole('button', { name: 'Highlight alternative 2', exact: true }).getAttribute('aria-pressed') === 'true' && (await page.locator('.command-map-caption').innerText()).includes('alternative 2'));
  const alternateExport = await exportJSON(page.getByRole('button', { name: 'Export route comparison JSON', exact: true }), 'injected-alternative-export.json'); check('injected alternative export retains exact selected geometry', alternateExport.selected_alternative === 1 && same(alternateExport.payload, injected.payload)); await page.unroute('**/api/route');
  phase = 'actual_offline_route_restored'; pending = responseFor('/api/route'); await page.getByRole('button', { name: 'Request road route', exact: true }).click(); const restoredRoute = await pending; check('actual offline route restored after injected UI case', (await restoredRoute.json()).payload.routes.length === actualRoute.payload.routes.length); await waitIdle();

  phase = 'approval_before_preview'; const approved = await approveScenario('A', 'Browser QA dispatcher'); check('actual approved assignments exist before all previews', approved.assignments.length > 0); await save('approved-before-preview', approved);
  await page.getByRole('combobox', { name: 'Select shipment', exact: true }).selectOption('SH11'); const beforeEvents = await request('/api/network'); const beforeScenarios = await request('/api/scenarios'); const allPreviews = {};
  for (const event of ['road_closure', 'severe_weather', 'delivery_delay', 'refrigeration_fault', 'temperature_excursion', 'inventory_shortage']) {
    phase = 'preview_' + event; const value = await preview(event, beforeEvents); allPreviews[event] = value;
    const reference = await independentReference(beforeEvents, event, 'SH11'); const target = reference.network.shipments.find(row => row.id === 'SH11');
    check(`${phase}: direct post-event fields match pure simulator`, ['estimated_hours', 'temperature_c', 'review_priority', 'lot_id', 'truck_id', 'estimated_distance_km'].every(key => value.shipment.after[key] === target[key]));
    check(`${phase}: shared resource effects match actual reference`, value.shipment.after.truck_eligible === reference.network.trucks.find(row => row.id === target.truck_id).eligible && value.shipment.after.lot_inventory_kg === reference.network.lots.find(row => row.id === target.lot_id).inventory_kg);
    check(`${phase}: all four before metrics match actual current scenarios`, value.scenarios.every(row => { const expected = beforeScenarios.find(item => item.scenario === row.scenario); return ['total_logistics_cost', 'unmet_demand_kg', 'delayed_shipments', 'affected_shipments', 'review_priority_count', 'food_waste_kg'].every(key => row.before[key] === expected[key]); }));
    check(`${phase}: all four after metrics and assignments match independent pure solve`, value.scenarios.every(row => { const expected = reference.scenarios.find(item => item.scenario === row.scenario); return ['total_logistics_cost', 'unmet_demand_kg', 'delayed_shipments', 'affected_shipments', 'review_priority_count', 'food_waste_kg', 'solver_status', 'feasible', 'constraint_violations'].every(key => row.after[key] === expected[key]) && same(row.after.selected_lots, Object.fromEntries(expected.shipments.map(item => [item.id, item.lot_id]))); }));
    check(`${phase}: retained approved assignments disclosed`, value.assignments.current_count === approved.assignments.length && value.assignments.would_be_invalidated === approved.assignments.length);
    await save('actual-' + event + '-preview', value);
  }
  check('all six actual UI previews left operational state unchanged', same(beforeEvents, await request('/api/network')) && same(approved.assignments, await request('/api/driver')));
  phase = 'apply_previewed_event'; const previewed = await preview('temperature_excursion', beforeEvents); const previewExport = await exportJSON(impact().getByRole('button', { name: 'Export event impact JSON', exact: true }), 'actual-preview-stage-export.json'); check('preview export contains exact read-only comparison and no receipt', previewExport.stage === 'preview' && previewExport.receipt === null && same(previewExport.comparison, previewed));
  await impact().scrollIntoViewIfNeeded(); await capture('desktop-event-impact-preview');
  await impact().getByRole('checkbox', { name: 'I intend to change this simulation and clear all approved assignments.', exact: true }).check(); check('explicit consent enables apply only for current preview', await impact().getByRole('button', { name: 'Apply previewed event', exact: true }).isEnabled());
  pending = responseFor('/api/events'); await impact().getByRole('button', { name: 'Apply previewed event', exact: true }).click(); const appliedResponse = await pending; check('explicit preview application reaches actual endpoint', appliedResponse.ok()); const receipt = await appliedResponse.json(); await impact().getByText('Simulated event applied to SH11.', { exact: true }).waitFor(); await waitIdle();
  check('actual apply receipt records revision and all assignment invalidation', receipt.preview_id === previewed.preview_id && receipt.network_revision_before === beforeEvents.revision && receipt.revision === beforeEvents.revision + 1 && receipt.assignments_removed === approved.assignments.length && receipt.operational_state_modified === true);
  const afterApplied = await request('/api/network'); check('actual network changed only after explicit apply', afterApplied.revision === receipt.revision && afterApplied.events.length === beforeEvents.events.length + 1 && afterApplied.shipments.find(row => row.id === 'SH11').temperature_c === 9 && (await request('/api/driver')).length === 0);
  check('applied event does not invent new historical temperature samples', same(afterApplied.telemetry, beforeEvents.telemetry));
  const appliedExport = await exportJSON(impact().getByRole('button', { name: 'Export event impact JSON', exact: true }), 'actual-applied-stage-export.json'); check('applied export preserves exact receipt and used comparison', appliedExport.stage === 'applied' && same(appliedExport.receipt, receipt) && same(appliedExport.comparison, previewed));
  await impact().locator('.event-impact-applied').scrollIntoViewIfNeeded(); await capture('desktop-applied-event-receipt');
  phase = 'repeated_event_preview'; const repeated = await preview('temperature_excursion', afterApplied); check('repeated event explicitly reports unchanged direct fields', repeated.shipment.changes.length === 0 && await impact().getByText(/already at this event's modeled setting/).isVisible());

  phase = 'stale_approval'; pending = responseFor('/api/proposals/A'); await page.getByRole('button', { name: 'Review scenario A', exact: true }).click(); const staleProposal = await (await pending).json(); const dialog = page.getByRole('dialog', { name: 'Review scenario A', exact: true }); await dialog.waitFor();
  await dialog.getByLabel('Dispatcher name', { exact: true }).fill('Browser QA reviewer'); await dialog.getByLabel('Reason for approval', { exact: true }).fill('Attempt obsolete proposal to verify visible rejection in this isolated test.');
  const forcedEvent = await request('/api/events', { event: 'delivery_delay', shipment_id: 'SH11', expected_network_revision: afterApplied.revision }); const staleBefore = await database(isolatedPath); pending = responseFor('/api/proposals/' + staleProposal.id + '/approve'); await dialog.getByRole('button', { name: 'Approve simulated plan', exact: true }).click(); const rejected = await pending;
  check('actual obsolete proposal rejected with HTTP409', rejected.status() === 409); await dialog.getByRole('alert').filter({ hasText: 'Approval did not complete: Network changed' }).waitFor(); check('rejected approval has visible inline dialog error', await dialog.getByRole('alert').isVisible());
  check('rejected approval does not change SQLite or publish assignments', same(staleBefore, await database(isolatedPath)) && (await request('/api/driver')).length === 0); await capture('desktop-visible-stale-approval-error'); await dialog.getByRole('button', { name: 'Keep under review', exact: true }).click(); await refresh();

  phase = 'reset_cancel'; const beforeCancel = await request('/api/network'), resetPosts = result.post_requests.filter(row => row.path === '/api/demo/reset').length; await page.getByRole('button', { name: 'Reset demo', exact: true }).click(); const resetDialog = page.getByRole('dialog', { name: 'Reset the simulated network?', exact: true }); await resetDialog.waitFor(); await resetDialog.getByRole('button', { name: 'Keep current network', exact: true }).click(); check('cancel reset performs no mutation', result.post_requests.filter(row => row.path === '/api/demo/reset').length === resetPosts && same(beforeCancel, await request('/api/network')));
  phase = 'reset_confirm'; await page.getByRole('button', { name: 'Reset demo', exact: true }).click(); pending = responseFor('/api/demo/reset'); await resetDialog.getByRole('button', { name: 'Confirm reset simulation', exact: true }).click(); const resetReceipt = await (await pending).json(); await resetDialog.waitFor({ state: 'hidden' }); await waitIdle(); const resetNetwork = await request('/api/network');
  check('confirmed reset produces actual revision and clears events', resetNetwork.revision === resetReceipt.revision && resetNetwork.revision === forcedEvent.revision + 1 && resetNetwork.events.length === 0 && (await request('/api/driver')).length === 0 && resetNetwork.shipments.find(row => row.id === 'SH11').temperature_c === beforeEvents.shipments.find(row => row.id === 'SH11').temperature_c);

  phase = 'fresh_approval_and_drive'; const finalApproval = await approveScenario('A', 'Final isolated QA dispatcher'); await save('final-approved-plan', finalApproval); const drive = await request('/api/drive/T01'); check('fresh approval publishes a real simulated T01 assignment', drive.assignments.length > 0);
  await navigation().getByRole('button', { name: 'AEGIS Drive', exact: true }).click(); await page.getByRole('region', { name: 'AEGIS Drive workspace', exact: true }).waitFor(); await page.getByText('CURRENT ASSIGNED DESTINATION', { exact: false }).waitFor(); check('Drive displays actual approved trip and remains safely locked', (await page.locator('.drive-workspace').innerText()).includes(drive.assignments[0].id) && (await page.locator('.drive-workspace').innerText()).includes(drive.assignments[0].lot_id) && await page.getByRole('button', { name: 'Trip route', exact: false }).isDisabled());

  phase = 'all_workspace_guides'; const titles = { 'Command center': 'Understand the current operation', 'Route laboratory': 'Experiment with a route design', 'Road intelligence': 'Inspect routes alongside road evidence', 'Dispatcher desk': 'Turn review into a recorded decision', 'Sources & evidence': 'Check what the sources actually provide', 'Model evaluation': 'Read the measured scientific result', 'Evidence assistant': 'Ask for an explanation of captured evidence', 'Project brief': 'Learn, rehearse and present', 'AEGIS Drive': 'Follow the approved simulated trip' };
  const guidancePosts = result.post_requests.length;
  for (const [label, title] of Object.entries(titles)) { await navigation().getByRole('button', { name: label, exact: true }).click(); await guide().getByRole('heading', { name: title, exact: true }).waitFor(); await guide().locator('summary').click(); check(`${label}: guide and relationships explain actual scope`, (await guide().locator('li').count()) === 3 && (await guide().getByRole('button').count()) === 2); await overflow(`${label}: desktop layout`); }
  check('workspace guide browsing performs no operational POST', result.post_requests.length === guidancePosts);
  await guide().getByRole('button', { name: 'Review assignment plans', exact: true }).click(); await page.getByRole('heading', { name: 'Regional command center', exact: true }).waitFor(); check('connected workspace button actually navigates', await guide().getByRole('heading', { name: titles['Command center'], exact: true }).isVisible());

  phase = 'mobile'; await page.setViewportSize({ width: 390, height: 844 }); await guide().scrollIntoViewIfNeeded(); await overflow('mobile Command guide layout'); await capture('mobile-command-guide');
  await page.getByRole('button', { name: 'Show scenario D allocation on map', exact: true }).click(); await focused('command-network-map'); await overflow('mobile map allocation layout'); await capture('mobile-scenario-allocation-map');
  await page.getByRole('combobox', { name: 'Select shipment', exact: true }).selectOption('SH11'); const mobileBefore = await request('/api/network'); const mobilePreview = await preview('road_closure', mobileBefore); check('mobile actual preview shows two-hour planning change', mobilePreview.route_effects.duration_change_hours === 2 && mobilePreview.route_effects.geometry_changed === false); await impact().scrollIntoViewIfNeeded(); await overflow('mobile impact table contained in scroll region'); await capture('mobile-event-impact-preview');
  await navigation().getByRole('button', { name: 'AEGIS Drive', exact: true }).click(); await page.getByRole('region', { name: 'AEGIS Drive workspace', exact: true }).waitFor(); await page.locator('.drive-header').scrollIntoViewIfNeeded(); await overflow('mobile approved Drive layout'); await capture('mobile-approved-drive');
  const activeMobileNav = await navigation().getByRole('button', { name: 'AEGIS Drive', exact: true }).boundingBox();
  check('mobile nav keeps active workspace visible', !!activeMobileNav && activeMobileNav.x >= 0 && activeMobileNav.x + activeMobileNav.width <= 390);

  phase = 'confirmed_receipt_network_failure';
  await page.setViewportSize({ width: 1440, height: 1050 }); await command(); await refresh();
  await page.getByRole('combobox', { name: 'Select shipment', exact: true }).selectOption('SH11');
  const beforeFailureEvent = await request('/api/network'); const beforeFailureAssignments = await request('/api/driver');
  const failurePreview = await preview('delivery_delay', beforeFailureEvent);
  result.injected_cases.push({ phase, scope: 'Actual consented /events application succeeds on isolated server; only subsequent browser /api/network reload is fulfilled with HTTP503 to test durable receipt UI. This is not an actual server/provider outage.' });
  let injectedNetworkFailures = 0;
  await page.route('**/api/network', route => { injectedNetworkFailures++; return route.fulfill({ status: 503, contentType: 'application/json', headers: { 'x-aegis-browser-qa': 'receipt-network-failure' }, body: JSON.stringify({ detail: 'Explicit browser-injected network reload failure after a successful isolated event' }) }); });
  await impact().getByRole('checkbox', { name: 'I intend to change this simulation and clear all approved assignments.', exact: true }).check();
  const failureApplyPosts = result.post_requests.filter(item => item.path === '/api/events').length;
  pending = responseFor('/api/events'); await impact().getByRole('button', { name: 'Apply previewed event', exact: true }).click();
  const failureApplyResponse = await pending; check('durable receipt case uses an actually successful event endpoint', failureApplyResponse.ok()); const durableReceipt = await failureApplyResponse.json();
  const durableBanner = page.getByRole('complementary', { name: 'Confirmed event receipt', exact: true });
  await durableBanner.getByRole('alert').waitFor();
  check('confirmed receipt survives simulator unmount on failed network reload', await impact().count() === 0 && await durableBanner.isVisible() && injectedNetworkFailures === 1);
  check('durable receipt shows actual applied revision and removed assignments', (await durableBanner.innerText()).includes(`Applied at network revision ${durableReceipt.revision}; ${durableReceipt.assignments_removed} approved assignments were removed.`) && durableReceipt.assignments_removed === beforeFailureAssignments.length && durableReceipt.preview_id === failurePreview.preview_id);
  check('durable receipt makes successful action and unavailable current state explicit', (await durableBanner.getByRole('alert').innerText()).includes('The event was applied, but the current network is unavailable.') && (await durableBanner.innerText()).includes('not a new action'));
  const durableExport = await exportJSON(durableBanner.getByRole('button', { name: 'Export confirmed event JSON', exact: true }), 'actual-confirmed-event-after-injected-network-failure.json');
  check('confirmed receipt export retains exact actual application and comparison', durableExport.stage === 'applied' && same(durableExport.receipt, durableReceipt) && same(durableExport.comparison, failurePreview));
  const actualAfterFailure = await request('/api/network');
  check('actual server confirms event applied once despite browser reload failure', actualAfterFailure.revision === beforeFailureEvent.revision + 1 && actualAfterFailure.revision === durableReceipt.revision && actualAfterFailure.events.length === beforeFailureEvent.events.length + 1 && actualAfterFailure.shipments.find(item => item.id === 'SH11').estimated_hours === beforeFailureEvent.shipments.find(item => item.id === 'SH11').estimated_hours + 2 && (await request('/api/driver')).length === 0);
  await durableBanner.scrollIntoViewIfNeeded(); await capture('desktop-confirmed-receipt-network-failure');
  const beforeDismissPosts = result.post_requests.length; await durableBanner.getByRole('button', { name: 'Dismiss confirmed receipt', exact: true }).click(); await durableBanner.waitFor({ state: 'hidden' });
  check('dismissing confirmed receipt performs no event or assignment action', result.post_requests.length === beforeDismissPosts && same(actualAfterFailure, await request('/api/network')));
  await page.unroute('**/api/network'); pending = page.waitForResponse(response => new URL(response.url()).pathname === '/api/network'); await page.getByRole('button', { name: 'Reload application data', exact: true }).click();
  check('network reload recovers from the explicitly injected failure', (await pending).ok()); await impact().getByRole('button', { name: 'Preview event impact', exact: true }).waitFor(); await waitIdle();
  check('recovery does not retry the event or recreate assignments', result.post_requests.filter(item => item.path === '/api/events').length === failureApplyPosts + 1 && (await request('/api/driver')).length === 0 && await durableBanner.count() === 0);

  phase = 'final_guards'; result.operator_database_after = await database(operatorPath); result.fixtures_after = await tree('data/fixtures'); result.cache_after = await tree('data/cache'); result.isolated_database_after = await database(isolatedPath);
  check('operator database and every SQLite sidecar unchanged', same(result.operator_database_before, result.operator_database_after));
  check('all dated source fixtures unchanged', same(result.fixtures_before, result.fixtures_after)); check('all public source cache bytes unchanged', same(result.cache_before, result.cache_after));
  check('all browser actions confined to permitted isolated APIs', result.post_requests.every(row => /^\/api\/(route$|events(?:\/preview)?$|proposals\/[A-D]$|proposals\/[A-Za-z0-9-]+\/approve$|demo\/reset$)/.test(row.path)));
  check('no actual provider refresh model or driver writes', !result.post_requests.some(row => /refresh|assistant\/interpret|\/drive\/|\/driver\//.test(row.path)));
  check('no uncaught browser JavaScript errors', result.page_errors.length === 0, JSON.stringify(result.page_errors)); check('no unexpected application HTTP failures', result.http_failures.length === 0, JSON.stringify(result.http_failures)); check('no unexpected console errors', result.console_errors.length === 0, JSON.stringify(result.console_errors));
  result.passed = true;
} catch (error) { result.passed = false; result.error = { phase, message: error.message, stack: error.stack }; if (page) await page.screenshot({ path: path.join(folder, 'failure.png'), fullPage: false }).catch(() => {}); }
finally { if (browser) await browser.close(); result.finished_at = new Date().toISOString(); await save('results', result); }
console.log(JSON.stringify({ passed: result.passed, checks: result.checks.length, screenshots: result.screenshots.length, error: result.error, page_errors: result.page_errors.length, http_failures: result.http_failures.length, console_errors: result.console_errors.length }));
if (!result.passed) process.exitCode = 1;
