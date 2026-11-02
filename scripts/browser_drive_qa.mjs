/** Actual Chrome rehearsal of AEGIS Drive. Mutations are restricted to QA port 8001. */
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '../.tools/browser-qa/node_modules/playwright-core/index.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const base = 'http://127.0.0.1:8001';
const folder = path.join(root, 'reports/browser_qa/drive');
await fs.mkdir(folder, { recursive: true });
const result = { checked_at: new Date().toISOString(), base_url: base, isolated_database: true, checks: [], page_errors: [], http_failures: [], tile_failures: [], screenshots: [], route_requests: 0, page_api_requests: [] };
const check = (name, passed, details = '') => { result.checks.push({ name, passed, details }); if (!passed) throw new Error(`${name}: ${details}`); };
let browser, page;
try {
  browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  result.browser_version = browser.version();
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, timezoneId: 'America/Chicago', locale: 'en-US' });
  page = await context.newPage(); page.setDefaultTimeout(20000);
  page.on('pageerror', error => result.page_errors.push(error.message));
  page.on('response', response => { if (response.url().startsWith(base) && response.status() >= 400 && !response.url().endsWith('/favicon.ico')) result.http_failures.push({ url: response.url(), status: response.status() }); if (response.url().includes('tile.openstreetmap.org/') && response.status() >= 400) result.tile_failures.push({url:response.url(),status:response.status()}); });
  page.on('request', request => { if (request.url().startsWith(base+'/api/')) result.page_api_requests.push({method:request.method(),path:new URL(request.url()).pathname}); if (request.method() === 'POST' && request.url() === base + '/api/route') result.route_requests++; });
  const get = async endpoint => { const response = await context.request.get(base + endpoint); if (!response.ok()) throw new Error(`${endpoint}: HTTP ${response.status()}`); return response.json(); };
  const post = async (endpoint, data, expected = 200) => { const response = await context.request.post(base + endpoint, { data }); check(`api_${endpoint}_${expected}`, response.status() === expected, `HTTP ${response.status()}`); return response.json(); };
  const uiPost = async (endpoint, action) => { const pending = page.waitForResponse(response => response.request().method() === 'POST' && response.url() === base + endpoint); await action(); const response = await pending; check(`ui_${endpoint}`, response.ok(), `HTTP ${response.status()}`); return response.json(); };
  const refresh = async truck => { const pending = page.waitForResponse(response => response.request().method() === 'GET' && response.url() === base + `/api/drive/${truck}`); await page.getByRole('button', { name: 'Refresh driver data', exact: true }).click(); return (await pending).json(); };
  const capture = async (name, fullPage = false) => { await page.screenshot({ path: path.join(folder, name + '.png'), fullPage }); result.screenshots.push(name + '.png'); };
  const noOverflow = async name => { const size = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth })); check(name, size.document <= size.viewport, JSON.stringify(size)); };
  const focus = async (truck, mode) => { const state = await get(`/api/drive/${truck}`); return post(`/api/drive/${truck}/focus`, { mode, expected_version: state.focus.version, parked_confirmation: mode === 'parked' }); };

  await post('/api/demo/reset', {});
  const network = await get('/api/network');
  check('isolated_empty_assignments', (await get('/api/driver')).length === 0, 'No unapproved trip may populate Drive');
  for (const truck of network.trucks) await focus(truck.id, 'driving');
  await page.goto(base + '/?mode=drive', { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: 'Confirm safely parked', exact: true }).waitFor();
  await page.getByRole('heading', { name: 'Ready for a reviewed plan', exact: true }).waitFor();
  result.initial_page_api_paths=[...new Set(result.page_api_requests.map(r=>r.path))];
  check('dedicated_view_avoids_bulk_evidence_requests', result.initial_page_api_paths.every(p=>p==='/api/network'||p.startsWith('/api/drive/')), JSON.stringify(result.initial_page_api_paths));
  check('dedicated_view_hides_command_navigation', await page.getByRole('button', { name: 'Command center', exact: true }).count() === 0 && await page.locator('.sidebar').count() === 0);
  check('empty_view_does_not_invent_trip', (await page.locator('.drive-destination').innerText()).includes('No route or load is invented here.'));
  check('default_locked_has_no_typing', await page.locator('textarea').count() === 0 && await page.getByLabel('Simulated driver truck', { exact: true }).count() === 0);
  for (const name of ['Trip route', 'Dispatch instructions', 'Report an issue']) check('default_locked_' + name, await page.getByRole('button', { name: new RegExp('^' + name) }).isDisabled());
  await capture('desktop-locked-empty');

  const proposal = await post('/api/proposals/B', {});
  await post(`/api/proposals/${proposal.id}/approve`, { actor: 'Drive QA dispatcher', reason: 'Isolated reviewed plan for visual driver and parked-attestation rehearsal' });
  const assignments = await get('/api/driver');
  const groups = Object.groupBy(assignments, item => item.truck_id);
  const pair = Object.entries(groups).find(([truck, trips]) => truck !== 'T01' && trips.length > 1) ?? Object.entries(groups).find(([, trips]) => trips.length > 1);
  check('approved_plan_has_multi_trip_truck', Boolean(pair));
  const [truckId, trips] = pair;
  const target = trips[1]; result.target = { shipment_id: target.id, truck_id: truckId, lot_id: target.lot_id, destination: target.destination, selected_nonfirst_trip: true };
  await page.reload(); await page.getByRole('button', { name: 'Confirm safely parked', exact: true }).waitFor();
  await post(`/api/driver/${target.id}/acknowledge`, {}, 423);
  await post('/api/driver/incident', { shipment_id: target.id, description: 'Locked report must not be recorded' }, 423);
  await post(`/api/driver/${target.id}/instruction-ack`, { instruction_revision: 1 }, 423);
  await post(`/api/drive/${truckId}/quick-report`, { shipment_id: target.id, kind: 'road_delay' }, 423);
  check('locked_writes_preserve_assignment', !(await get('/api/driver')).find(item => item.id === target.id).acknowledged);
  const parkInitial = await uiPost('/api/drive/T01/focus', () => page.getByRole('button', { name: 'Confirm safely parked', exact: true }).click());
  check('park_confirmation_has_finite_expiry', parkInitial.interaction_allowed && Date.parse(parkInitial.parked_until) > Date.now() && Date.parse(parkInitial.parked_until) - Date.now() <= 600000);
  await page.getByLabel('Simulated driver truck', { exact: true }).waitFor();
  if (truckId !== 'T01') {
    await page.getByLabel('Simulated driver truck', { exact: true }).selectOption(truckId);
    await page.getByRole('button', { name: 'Confirm safely parked', exact: true }).waitFor();
    check('truck_switch_relocks_controls', await page.getByLabel('Simulated driver truck', { exact: true }).count() === 0 && await page.getByRole('button', { name: /^Report an issue/ }).isDisabled());
    await uiPost(`/api/drive/${truckId}/focus`, () => page.getByRole('button', { name: 'Confirm safely parked', exact: true }).click());
  }
  await page.getByLabel('Trip for advisories and incident reporting', { exact: true }).selectOption(target.id);
  const destination = network.nodes.find(node => node.id === target.destination);
  await page.getByRole('heading', { name: destination.name, exact: true }).waitFor();
  check('nonfirst_trip_updates_destination_and_cargo', (await page.locator('.drive-destination').innerText()).includes(target.id) && (await page.locator('.drive-temperature').innerText()).includes(target.temperature_c.toFixed(1)));
  const driverState = await get(`/api/drive/${truckId}`);
  result.simulated_vehicle = { truck_id:truckId, fuel_percent:driverState.vehicle.fuel_percent, tank_capacity_liters:driverState.vehicle.tank_capacity_liters, scenario_observed_at:driverState.vehicle.observed_at, provenance:driverState.vehicle.provenance };
  check('fuel_matches_deterministic_server_scenario', (await page.locator('.drive-fuel-display').innerText()).includes(String(driverState.vehicle.fuel_percent)) && driverState.vehicle.simulation === true);
  check('fuel_and_position_provenance_visible', (await page.locator('.drive-gauge.fuel').innerText()).includes('NO FUEL SENSOR') && (await page.locator('.drive-location').innerText()).includes('NOT LIVE GPS'));
  await capture('desktop-approved-parked');

  await page.getByRole('button', { name: /^Trip route/ }).click();
  await page.getByRole('heading', { name: target.id + ' · trip advisories', exact: true }).waitFor();
  const road = await uiPost('/api/route', () => page.getByRole('button', { name: 'Review trip route while parked', exact: true }).click());
  result.routing = {fallback:Boolean(road.fallback),cache:road.cache ?? null,stale:road.stale ?? null,retrieved_at:road.retrieved_at ?? null,provenance:road.provenance ?? null,road_review_retrieved_at:road.road_review?.modot_retrieved_at ?? null,distance_m:road.payload?.routes?.[0]?.distance ?? null,duration_seconds:road.payload?.routes?.[0]?.duration ?? null};
  await page.locator('.driver-exposure .leaflet-container').waitFor();
  await page.waitForFunction(() => [...document.querySelectorAll('.driver-exposure img.leaflet-tile')].some(image => image.complete && image.naturalWidth > 0), undefined, {timeout:10000}).catch(() => {});
  result.route_map_tiles_loaded = await page.locator('.driver-exposure img.leaflet-tile-loaded').count();
  if (!result.route_map_tiles_loaded) result.map_coverage_warning = 'No OSM base tile finished loading within the 10-second wait. The route geometry check is separate from base-map availability.';
  check('trip_route_or_explicit_fallback_rendered', Boolean(road.payload?.routes?.length) && (await page.locator('.driver-exposure').innerText()).includes(road.fallback ? 'Estimated fallback connection' : 'OSRM ordinary driving route'));
  check('route_review_does_not_reassign', (await get('/api/driver')).find(item => item.id === target.id).destination === target.destination);
  await page.locator('.driver-exposure').scrollIntoViewIfNeeded(); await capture('parked-route-review');

  await page.getByRole('button', { name: /^Report an issue/ }).click();
  await page.getByRole('heading', { name: 'Report while safely parked', exact: true }).waitFor();
  const incidentIds = [];
  for (const [kind, label] of [['refrigeration', 'Refrigeration concern'], ['road_delay', 'Road delay'], ['vehicle_issue', 'Vehicle issue'], ['cargo_issue', 'Cargo concern']]) {
    const sent = await uiPost(`/api/drive/${truckId}/quick-report`, () => page.getByRole('button', { name: label, exact: true }).click());
    check('quick_report_kind_' + kind, sent.kind === kind && sent.truck_id === truckId); incidentIds.push(sent.incident_id);
  }
  await page.getByLabel('Report a driver incident', { exact: true }).fill('Isolated driver QA: packaging condition reviewed while safely parked.');
  const textReport = await uiPost('/api/driver/incident', () => page.getByRole('button', { name: 'Send to dispatcher', exact: true }).click());
  incidentIds.push(textReport.incident_id);
  await page.getByText('Incident submitted for dispatcher review.', { exact: true }).waitFor();
  const inbox = await get('/api/dispatch'); const reports = inbox.incidents.filter(item => incidentIds.includes(item.id));
  check('all_five_reports_reach_dispatcher', reports.length === 5 && reports.every(item => item.status === 'open'));
  check('reports_preserve_nonfirst_trip_context', reports.every(item => item.shipment_id === target.id && item.reporting_assignment.truck_id === truckId && item.reporting_assignment.lot_id === target.lot_id && item.reporting_assignment.destination === target.destination));
  await page.setViewportSize({ width: 390, height: 844 }); await noOverflow('mobile_parked_reporting_no_overflow');
  await page.getByRole('heading', { name: 'Report while safely parked', exact: true }).scrollIntoViewIfNeeded(); await capture('mobile-parked-report');
  await page.setViewportSize({ width: 1440, height: 1000 });

  const approved = inbox.assignments.find(item => item.id === target.id);
  const issue = async (expected, instruction) => post(`/api/dispatch/assignments/${target.id}/instruction`, { actor: 'Drive QA dispatcher', reason: 'Versioned parked-use instruction reviewed in isolated driver rehearsal', instruction, expected_instruction_revision: expected, expected_network_revision: inbox.network_revision });
  const firstInstruction = await issue(approved.instruction_revision ?? 0, 'Remain parked and review the current cargo advisory.');
  const currentInstruction = await issue(firstInstruction.instruction_revision, 'Remain safely parked until the dispatcher completes review.');
  await post(`/api/driver/${target.id}/instruction-ack`, { instruction_revision: firstInstruction.instruction_revision }, 409);
  await refresh(truckId);
  await page.getByRole('button', { name: /^Dispatch instructions/ }).click();
  await page.getByRole('heading', { name: 'Dispatcher-approved trip instructions', exact: true }).waitFor();
  await page.getByText('Remain safely parked until the dispatcher completes review.', { exact: true }).waitFor();
  await uiPost(`/api/driver/${target.id}/instruction-ack`, () => page.getByRole('button', { name: 'Acknowledge new instruction', exact: true }).click());
  await page.getByRole('button', { name: 'Instruction acknowledged', exact: true }).waitFor();
  await uiPost(`/api/driver/${target.id}/acknowledge`, () => page.getByRole('button', { name: 'Acknowledge assignment', exact: true }).click());
  await page.getByRole('button', { name: 'Assignment acknowledged', exact: true }).waitFor();
  const acknowledged = (await get('/api/driver')).find(item => item.id === target.id);
  check('assignment_and_exact_instruction_ack_recorded', acknowledged.acknowledged && acknowledged.instruction_acknowledged && acknowledged.instruction_revision === currentInstruction.instruction_revision);
  await page.locator('.drive-detail-panel').scrollIntoViewIfNeeded(); await capture('parked-approved-instructions');

  await uiPost(`/api/drive/${truckId}/focus`, () => page.getByRole('button', { name: 'Lock for driving', exact: true }).click());
  await page.getByRole('button', { name: 'Confirm safely parked', exact: true }).waitFor();
  check('driving_focus_hides_forms_and_acknowledgments', await page.locator('textarea').count() === 0 && await page.getByRole('button', { name: 'Assignment acknowledged', exact: true }).count() === 0);
  check('driving_focus_locks_visual_actions', await page.getByRole('button', { name: /^Trip route/ }).isDisabled() && await page.getByRole('button', { name: /^Report an issue/ }).isDisabled());
  await post('/api/driver/incident', { shipment_id: target.id, description: 'Post-lock report must not be recorded' }, 423);
  const afterLock = await get('/api/dispatch');
  check('lock_does_not_create_extra_reports', afterLock.incidents.length === inbox.incidents.length);
  await page.setViewportSize({ width: 390, height: 844 }); await page.evaluate(() => scrollTo(0, 0)); await noOverflow('mobile_locked_drive_no_overflow'); await capture('mobile-locked-trip-and-gauges', true);
  check('mobile_retains_destination_and_sensor_labels', await page.getByRole('heading', { name: destination.name, exact: true }).isVisible() && (await page.locator('.drive-disclosure').innerText()).includes('no physical sensor'));
  await page.setViewportSize({ width: 1440, height: 1000 }); await noOverflow('desktop_drive_no_overflow'); await capture('desktop-locked-assigned');
  check('only_one_deliberate_road_request', result.route_requests === 1, `${result.route_requests} route requests from UI`);
  check('operator_network_unchanged_by_driver_actions', JSON.stringify(await get('/api/network')) === JSON.stringify({ ...network, revision: network.revision + 1 }));
  check('no_uncaught_javascript', result.page_errors.length === 0, JSON.stringify(result.page_errors));
  check('no_unexpected_application_http_failure', result.http_failures.length === 0, JSON.stringify(result.http_failures));
  result.passed = true;
} catch (error) {
  result.passed = false; result.error = String(error); process.exitCode = 1;
  if (page) { try { await page.screenshot({ path: path.join(folder, 'failure.png'), fullPage: false }); result.screenshots.push('failure.png'); } catch {} }
} finally {
  if (browser) await browser.close();
  result.finished_at = new Date().toISOString();
  await fs.writeFile(path.join(folder, 'results.json'), JSON.stringify(result, null, 2));
  console.log(JSON.stringify({ passed: result.passed, checks: result.checks.length, error: result.error, screenshots: result.screenshots }, null, 2));
}
