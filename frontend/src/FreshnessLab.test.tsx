import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import FreshnessLab, { freshnessPlotData, freshnessSnapshotValid, type FreshnessSnapshot } from './FreshnessLab';
import fixture from './FreshnessLab.fixture.json';
import { api } from './api';
import { downloadCaptured } from './CommandRouteReview';

vi.mock('./api',()=>({api:vi.fn()}));
vi.mock('./CommandRouteReview',()=>({downloadCaptured:vi.fn()}));
vi.mock('./MapViewport',()=>({default:()=>null}));
vi.mock('react-leaflet',()=>({MapContainer:({children}:any)=><div>{children}</div>,CircleMarker:({children}:any)=><div>{children}</div>,Popup:({children}:any)=><div>{children}</div>,Polyline:()=>null,TileLayer:()=>null}));
vi.mock('recharts',()=>{const Wrapper=({children}:any)=><div>{children}</div>;return {LineChart:Wrapper,ResponsiveContainer:Wrapper,Line:()=>null,CartesianGrid:()=>null,Tooltip:()=>null,XAxis:()=>null,YAxis:()=>null};});

type CaptureName='initial'|'heated'|'delayed'|'prepared';
function capture(name:CaptureName='heated'):FreshnessSnapshot {
  const value:unknown=structuredClone(fixture[name]);
  if(!freshnessSnapshotValid(value))throw new Error('Actual helper fixture no longer matches the UI contract');
  return value;
}
const initial=capture('initial');
const context={network_revision:0,simulation:true,demo_shipment_id:'SH05',shipments:[{id:'SH01',origin_name:'Other test origin',destination_name:'Other test stop',lot_id:'L01',truck_id:'T01'},{id:initial.shipment.id,origin_name:initial.shipment.origin_name,destination_name:initial.shipment.destination_name,lot_id:initial.shipment.lot_id,truck_id:initial.shipment.truck_id}],sessions:[],gateway:{configured:false,endpoint:'/api/freshness/telemetry',notice:'A server-side bearer token and explicit device/lot binding are required. No physical hardware verified.'},limitations:['Explicit simulated unit-test transport context.']};
let server:FreshnessSnapshot;
let createName:CaptureName;
function approved():FreshnessSnapshot {
  const value=capture('heated');value.version=3;value.status='approved';value.current_network_revision=1;
  value.approval={actor:'Dispatcher Taylor',reason:'Quality, recipient and route conditions separately reviewed',approved_at:'2026-10-30T14:00:00+00:00',network_revision:1,assignments_count:value.rescue.proposed_assignments.length,selected_destination_id:value.rescue.proposed_destination_id!};
  return value;
}
beforeEach(()=>{
  createName='heated';server=capture('heated');vi.mocked(api).mockReset();vi.mocked(downloadCaptured).mockReset();
  vi.mocked(api).mockImplementation(async(path,body)=>{
    if(path==='/freshness/context')return structuredClone(context) as any;
    if(path==='/freshness/sessions'){server=capture(createName);return structuredClone(server) as any;}
    if(path===`/freshness/sessions/${server.id}`)return structuredClone(server) as any;
    if(path.endsWith('/replay')){server=capture((body as any).event==='heat_excursion'?'heated':'delayed');return structuredClone(server) as any;}
    if(path.endsWith('/proposal')){server=capture('prepared');return structuredClone(server) as any;}
    if(path.endsWith('/routes'))return structuredClone(server) as any;
    if(path.endsWith('/approve')){server=approved();return {snapshot:structuredClone(server),receipt:structuredClone(server.approval)} as any;}
    if(path.endsWith('/rebase')){const value=capture('heated');value.version=server.version+1;value.network_revision=server.current_network_revision;value.current_network_revision=server.current_network_revision;server=value;return structuredClone(server) as any;}
    throw new Error('Unexpected UI request '+path);
  });
});
afterEach(()=>{if(vi.isFakeTimers())vi.clearAllTimers();vi.useRealTimers();});
async function start(props:Parameters<typeof FreshnessLab>[0]={}) {
  render(<FreshnessLab {...props}/>);
  await screen.findByRole('combobox',{name:'Candidate to explore'});
  fireEvent.click(screen.getByRole('button',{name:'Start rescue experiment'}));
  await screen.findByText('Point quality-window estimate');
}
async function startWithFakeTimers() {
  vi.useFakeTimers();render(<FreshnessLab/>);await act(async()=>{});
  await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'Start rescue experiment'}));});
  expect(screen.getByText('Point quality-window estimate')).toBeInTheDocument();
}
function metric(label:string){return within(screen.getByText(label).closest('article')!);}
function selectedName(){return server.rescue.options.find(row=>row.destination_id===server.rescue.proposed_destination_id)!.destination_name;}
function openReview(){fireEvent.click(screen.getByRole('button',{name:`Review ${selectedName()}`}));}
function confirmReview(){
  fireEvent.change(screen.getByRole('textbox',{name:'Reviewing dispatcher'}),{target:{value:'Dispatcher Taylor'}});
  fireEvent.change(screen.getByRole('textbox',{name:'Reason for rescue approval'}),{target:{value:'Quality, recipient and route conditions separately reviewed'}});
  fireEvent.click(screen.getByRole('checkbox',{name:/I reviewed quality and food-safety disposition/}));
  fireEvent.click(screen.getByRole('checkbox',{name:/I confirm the receiving capacity/}));
  fireEvent.click(screen.getByRole('checkbox',{name:/I reviewed the route and vehicle limitations/}));
}
function chooseOption(destinationId:string){
  const option=server.rescue.options.find(row=>row.destination_id===destinationId)!;
  const buttons=screen.getByRole('group',{name:'Calculated rescue destinations'}).querySelectorAll('button');
  const button=[...buttons].find(row=>row.textContent?.startsWith(option.destination_name));
  if(!button)throw new Error('No option button');fireEvent.click(button);
}

describe('Save the Load UI transport and science boundaries',()=>{
  it('continues a reviewed lot history instead of creating a fresh quality budget',async()=>{
    const normal=vi.mocked(api).getMockImplementation()!;
    vi.mocked(api).mockImplementation(async(path,body)=>path==='/freshness/context'?{...structuredClone(context),shipments:context.shipments.map(row=>({...row,freshness_session_id:row.id==='SH05'?server.id:undefined}))} as any:normal(path,body));
    render(<FreshnessLab/>);
    fireEvent.click(await screen.findByRole('button',{name:'Continue lot’s exposure history'}));
    await screen.findByText('Point quality-window estimate');
    expect(vi.mocked(api).mock.calls.some(([path])=>path==='/freshness/sessions')).toBe(false);
    expect(api).toHaveBeenCalledWith('/freshness/sessions/'+server.id);
  });
  it('plots sensor changes at original observation times and reference budgets at interval endpoints',()=>{
    const value=capture('heated');value.freshness.profile.started_at=value.readings[0].observed_at;
    const plots=freshnessPlotData(value);const warm=value.readings.find(row=>row.temperature_c===16)!;
    expect(plots.temperature.find(row=>row.elapsedMs===Date.parse(warm.observed_at))?.temperature_c).toBe(16);
    expect(plots.temperature.map(row=>row.elapsedMs)).toEqual(value.readings.map(row=>Date.parse(row.observed_at)));
    expect(plots.remaining[0]).toMatchObject({elapsedMs:Date.parse(value.readings[0].observed_at),remaining_reference_hours:10});
    expect(plots.remaining.at(-1)?.remaining_reference_hours).toBeCloseTo(value.freshness.remaining_reference_hours!,8);
    expect(plots.temperature.at(-1)?.temperature_c).toBe(4);
  });
  it('does not invent a baseline timestamp when a partial transport capture lacks it',()=>{
    const value=capture('heated');delete value.freshness.profile.started_at;
    expect(freshnessPlotData(value).remaining).toHaveLength(value.freshness.timeline.length);
  });
  it.each(['initial','heated','delayed','prepared'] as const)('accepts actual %s kinetic/planning helper capture',name=>{
    expect(freshnessSnapshotValid(fixture[name])).toBe(true);
  });
  it('loads context without creating an experiment or publishing an assignment',async()=>{
    render(<FreshnessLab/>);await screen.findByRole('button',{name:'Start rescue experiment'});
    expect(api).toHaveBeenCalledTimes(1);expect(api).toHaveBeenCalledWith('/freshness/context');
    expect(screen.getByRole('combobox',{name:'Candidate to explore'})).toHaveValue('SH05');
    expect(screen.queryByRole('button',{name:'Approve simulated rescue plan'})).not.toBeInTheDocument();
  });
  it('uses the actual requested candidate and revision when explicitly starting',async()=>{
    await start({initialShipmentId:'SH05'});
    expect(api).toHaveBeenCalledWith('/freshness/sessions',{expected_network_revision:0,shipment_id:'SH05',scenario:'poultry_demo'});
    expect(screen.getByText('Simulated sensor replay')).toBeInTheDocument();
    expect(screen.getByText(/Physical IoT hardware has not been verified/)).toBeInTheDocument();
  });
  it('separates actual point and conservative helper outputs instead of displaying the same estimate twice',async()=>{
    await start();
    expect(metric('Point quality-window estimate').getByText('4.4')).toBeInTheDocument();
    expect(metric('Conservative sensitivity window').getByText('1.5')).toBeInTheDocument();
    expect(metric('Conservative sensitivity window').getByText(/not a statistical confidence interval/)).toBeInTheDocument();
    expect(metric('Point quality-window estimate').getByText(/Starting reference budget: 10.0 h/)).toBeInTheDocument();
  });
  it('retains all channel units while identifying the auxiliary channels as contextual',async()=>{
    await start();
    expect(screen.getByText('Model temperature input')).toBeInTheDocument();
    expect(screen.getByText('Ambient temperature')).toBeInTheDocument();
    expect(screen.getByText('Relative humidity')).toBeInTheDocument();
    expect(screen.getByText('Vibration')).toBeInTheDocument();expect(screen.getByText('Ethylene')).toBeInTheDocument();
    expect(screen.getByText(/not a poultry freshness proxy/)).toBeInTheDocument();
    expect(screen.getByText(/measurement definition and damage coefficient unverified/)).toBeInTheDocument();
    expect(screen.getByText(/Observed .* received .*recent readings shown/)).toBeInTheDocument();
  });
  it('renders real FIFO versus FEFO pick-order differences and calls expiry stock exposure rather than waste',async()=>{
    await start();
    const panel=screen.getByRole('heading',{name:'Warehouse picking: arrival order or predicted expiry?'}).closest('section')!;
    expect(within(panel).getAllByRole('row')[1]).toHaveTextContent('L05');
    fireEvent.click(within(panel).getByRole('button',{name:'Show FIFO pick order'}));
    expect(within(panel).getAllByRole('row')[1]).toHaveTextContent('L12');
    expect(within(panel).getAllByText(/stock exposed to modeled expiry/)).toHaveLength(2);
    expect(within(panel).queryByText(/modeled expiry waste/)).not.toBeInTheDocument();
    expect(vi.mocked(api).mock.calls.filter(([,body])=>body!==undefined)).toHaveLength(1);
  });
  it('shows all concrete proposed assignments before enabling the separate approval',async()=>{
    await start();openReview();
    const form=screen.getByRole('region',{name:'Human rescue approval'});
    expect(within(form).getByText(/replaces the current simulated driver-assignment list/)).toBeInTheDocument();
    expect(within(form).getByText('Inspect all 12 proposed assignments')).toBeInTheDocument();
    expect(within(form).getAllByRole('row')).toHaveLength(13);
    expect(within(form).getByRole('button',{name:'Approve simulated rescue plan'})).toBeDisabled();
    expect(api).not.toHaveBeenCalledWith(expect.stringContaining('/approve'),expect.anything());
  });
  it('requires identity, rationale and all three separate human confirmations',async()=>{
    await start();openReview();
    const approve=screen.getByRole('button',{name:'Approve simulated rescue plan'});
    fireEvent.change(screen.getByRole('textbox',{name:'Reviewing dispatcher'}),{target:{value:'  '}});
    fireEvent.change(screen.getByRole('textbox',{name:'Reason for rescue approval'}),{target:{value:'Reviewed conditions'}});
    expect(approve).toBeDisabled();
    confirmReview();expect(approve).toBeEnabled();
    fireEvent.click(screen.getByRole('checkbox',{name:/I confirm the receiving capacity/}));expect(approve).toBeDisabled();
    expect(vi.mocked(api).mock.calls.some(([path])=>path.endsWith('/approve'))).toBe(false);
  });
  it('publishes only the exact captured proposal after an identified human action',async()=>{
    const onNetworkChanged=vi.fn().mockResolvedValue(undefined);const onOpenDrive=vi.fn();
    await start({onNetworkChanged,onOpenDrive});const before=structuredClone(server);openReview();confirmReview();
    fireEvent.click(screen.getByRole('button',{name:'Approve simulated rescue plan'}));
    await screen.findByRole('region',{name:'Confirmed rescue receipt'});
    expect(api).toHaveBeenCalledWith(`/freshness/sessions/${before.id}/approve`,{expected_version:before.version,expected_network_revision:before.network_revision,proposal_hash:before.rescue.proposal_hash,destination_id:before.rescue.proposed_destination_id,actor:'Dispatcher Taylor',reason:'Quality, recipient and route conditions separately reviewed',quality_review_confirmed:true,recipient_confirmed:true,routing_review_confirmed:true});
    expect(onNetworkChanged).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button',{name:'Open approved driver assignments'}));expect(onOpenDrive).toHaveBeenCalledWith({truckId:before.shipment.truck_id,shipmentId:before.shipment.id});
  });
  it('preserves the confirmed receipt when the global application refresh fails',async()=>{
    await start({onNetworkChanged:vi.fn().mockRejectedValue(new Error('Reload failed'))});openReview();confirmReview();
    fireEvent.click(screen.getByRole('button',{name:'Approve simulated rescue plan'}));
    expect(await screen.findByRole('region',{name:'Confirmed rescue receipt'})).toHaveTextContent('Rescue approval recorded');
    expect(await screen.findByRole('alert')).toHaveTextContent('rescue approval was recorded');
    expect(screen.queryByRole('button',{name:'Approve simulated rescue plan'})).not.toBeInTheDocument();
    expect(vi.mocked(api).mock.calls.filter(([path])=>path.endsWith('/approve'))).toHaveLength(1);
  });
  it('exports the captured server state without turning unsent form text into an approved decision',async()=>{
    await start();const before=structuredClone(server);openReview();
    fireEvent.change(screen.getByRole('textbox',{name:'Reviewing dispatcher'}),{target:{value:'Unsent reviewer'}});
    fireEvent.click(screen.getByRole('button',{name:'Export captured freshness experiment'}));
    expect(downloadCaptured).toHaveBeenCalledWith(expect.stringContaining(`-v${before.version}.json`),expect.objectContaining({...before,approval:null,captured_export:true}));
    expect(JSON.stringify(vi.mocked(downloadCaptured).mock.calls[0][1])).not.toContain('Unsent reviewer');
  });
  it('requires preparing a different destination before a concrete review can open',async()=>{
    await start();const prepared=capture('prepared');chooseOption(prepared.rescue.proposed_destination_id!);
    expect(screen.queryByRole('button',{name:`Review ${prepared.rescue.options.find(row=>row.destination_id===prepared.rescue.proposed_destination_id)!.destination_name}`})).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Prepare selected rescue'}));
    await waitFor(()=>expect(api).toHaveBeenCalledWith(`/freshness/sessions/${prepared.id}/proposal`,{expected_version:2,destination_id:prepared.rescue.proposed_destination_id}));
    await screen.findByRole('button',{name:`Review ${prepared.rescue.options.find(row=>row.destination_id===prepared.rescue.proposed_destination_id)!.destination_name}`});
    expect(vi.mocked(api).mock.calls.some(([path])=>path.endsWith('/approve'))).toBe(false);
  });
  it('invalidates an opened review when the person changes the selected destination',async()=>{
    await start();openReview();confirmReview();
    expect(screen.getByRole('button',{name:'Approve simulated rescue plan'})).toBeEnabled();
    chooseOption(capture('prepared').rescue.proposed_destination_id!);
    expect(screen.getByRole('button',{name:'Approve simulated rescue plan'})).toBeDisabled();
    expect(screen.getByText(/selection or calculation changed after this review opened/)).toBeInTheDocument();
  });
  it('requests optional road refinement with the exact selected destination and captured version',async()=>{
    await start();const before=structuredClone(server);
    fireEvent.click(screen.getByRole('button',{name:'Check road route'}));
    await waitFor(()=>expect(api).toHaveBeenCalledWith(`/freshness/sessions/${before.id}/routes`,{expected_version:before.version,destination_id:before.rescue.proposed_destination_id,routing:'osrm'}));
    expect(screen.getAllByText(/Estimated connection/).length).toBeGreaterThan(0);
    expect(vi.mocked(api).mock.calls.some(([path])=>path.endsWith('/approve'))).toBe(false);
  });
  it('starts with a short priority list and expands the captured exclusions on demand',async()=>{
    await start();
    const options=screen.getByRole('group',{name:'Calculated rescue destinations'});
    expect(within(options).getAllByRole('button').length).toBeLessThanOrEqual(4);
    fireEvent.click(screen.getByRole('button',{name:`Show all ${server.rescue.options.length} candidates and exclusions`}));
    expect(within(options).getAllByRole('button')).toHaveLength(server.rescue.options.length);
    fireEvent.click(screen.getByRole('button',{name:'Show priority destinations'}));
    expect(within(options).getAllByRole('button').length).toBeLessThanOrEqual(4);
    expect(vi.mocked(api).mock.calls.filter(([,body])=>body!==undefined)).toHaveLength(1);
  });
  it('keeps an existing but quality-ineligible buyer inspectable without enabling preparation or review',async()=>{
    await start();
    const excluded=server.rescue.options.find(option=>!option.eligible&&option.dispatchable)!;
    expect(excluded).toBeDefined();
    fireEvent.click(screen.getByRole('button',{name:`Show all ${server.rescue.options.length} candidates and exclusions`}));
    chooseOption(excluded.destination_id);
    expect(screen.getAllByText('Not eligible under current inputs').length).toBeGreaterThan(0);
    expect(screen.getByRole('button',{name:'Prepare selected rescue'})).toBeDisabled();
    expect(screen.getByRole('button',{name:'Check road route'})).toBeEnabled();
    expect(screen.queryByRole('button',{name:`Review ${excluded.destination_name}`})).not.toBeInTheDocument();
    expect(screen.getByText(/Road inspection can refine travel estimates/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Prepare selected rescue'}));
    expect(vi.mocked(api).mock.calls.some(([path])=>path.endsWith('/proposal')||path.endsWith('/approve'))).toBe(false);
  });
  it('reports zero eligible buyers when dispatchable destinations fail their modeled quality window',async()=>{
    const normal=vi.mocked(api).getMockImplementation()!;
    vi.mocked(api).mockImplementation(async(path,body)=>{const value=await normal(path,body);if(path==='/freshness/sessions'){server.rescue.options.forEach(option=>{option.eligible=false;option.dispatchable=true;});return structuredClone(server) as any;}return value;});
    await start();
    expect(screen.getByText(/0 destinations pass both the modeled quality and dispatch checks/)).toBeInTheDocument();
    expect(screen.queryByText('Eligible buyer for human review')).not.toBeInTheDocument();
    expect(screen.getAllByText('Not eligible under current inputs').length).toBeGreaterThan(0);
    screen.getAllByRole('button',{name:/^(Review |Prepare selected rescue)/}).forEach(button=>expect(button).toBeDisabled());
  });
  it('labels an otherwise eligible distribution hub as inspection-only while receiving remains unconfirmed',async()=>{
    const normal=vi.mocked(api).getMockImplementation()!;
    vi.mocked(api).mockImplementation(async(path,body)=>{const value=await normal(path,body);if(path==='/freshness/sessions'){const hub=server.rescue.options.find(option=>option.kind==='dc')!;hub.eligible=true;hub.dispatchable=false;server.rescue.options=[hub];server.rescue.proposal_hash=null;server.rescue.proposal_id=null;server.rescue.proposed_destination_id=null;server.rescue.plan_summary=null;server.rescue.proposed_assignments=[];return structuredClone(server) as any;}return value;});
    await start();
    expect(screen.getByText('Hub inspection only; receiving review required')).toBeInTheDocument();
    expect(screen.getByText(/0 destinations pass both the modeled quality and dispatch checks/)).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Prepare selected rescue'})).toBeDisabled();
    expect(screen.getByRole('button',{name:'Check road route'})).toBeEnabled();
  });
  it('pauses an explicitly started replay when an actual captured rescue proposal is ready',async()=>{
    createName='initial';
    const normal=vi.mocked(api).getMockImplementation()!;
    // Version increments here test transport sequencing; numerical values remain
    // unchanged actual helper captures, not newly asserted model outcomes.
    vi.mocked(api).mockImplementation(async(path,body)=>{
      if(path.endsWith('/replay')){
        const version=server.version+1;server=capture((body as any).event==='normal'?'initial':'heated');server.version=version;return structuredClone(server) as any;
      }
      return normal(path,body);
    });
    await startWithFakeTimers();fireEvent.click(screen.getByRole('checkbox',{name:'Follow incoming readings every 5s'}));
    fireEvent.click(screen.getByRole('button',{name:'Play sensor replay'}));
    await act(async()=>{await vi.advanceTimersByTimeAsync(3000);});
    await act(async()=>{await vi.advanceTimersByTimeAsync(3000);});
    expect(vi.mocked(api).mock.calls.filter(([path])=>path.endsWith('/replay')).map(([,body])=>(body as any).event)).toEqual(['normal','heat_excursion']);
    expect(screen.getByRole('button',{name:'Play sensor replay'})).toBeInTheDocument();
    expect(screen.getByRole('button',{name:`Review ${selectedName()}`})).toBeEnabled();
    await act(async()=>{await vi.advanceTimersByTimeAsync(12000);});
    expect(vi.mocked(api).mock.calls.filter(([path])=>path.endsWith('/replay'))).toHaveLength(2);
  });
  it('waits for an incoming poll before the next replay frame without silently skipping heat',async()=>{
    createName='initial';let resolveRead!:(value:unknown)=>void;
    const normal=vi.mocked(api).getMockImplementation()!;
    vi.mocked(api).mockImplementation(async(path,body)=>{
      if(path.endsWith('/replay')){const version=server.version+1;server=capture((body as any).event==='normal'?'initial':'heated');server.version=version;return structuredClone(server) as any;}
      if(path===`/freshness/sessions/${server.id}`)return new Promise(done=>{resolveRead=done;});
      return normal(path,body);
    });
    await startWithFakeTimers();fireEvent.click(screen.getByRole('button',{name:'Play sensor replay'}));
    await act(async()=>{await vi.advanceTimersByTimeAsync(3000);});
    await act(async()=>{await vi.advanceTimersByTimeAsync(2000);});
    expect(screen.getByRole('button',{name:'Replay heat excursion'})).toBeDisabled();
    expect(screen.getByText('Reading stored sensor capture…')).toBeInTheDocument();
    await act(async()=>{await vi.advanceTimersByTimeAsync(6000);});
    expect(vi.mocked(api).mock.calls.filter(([path])=>path.endsWith('/replay'))).toHaveLength(1);
    await act(async()=>resolveRead(structuredClone(server)));
    await act(async()=>{await vi.advanceTimersByTimeAsync(3000);});
    expect(vi.mocked(api).mock.calls.filter(([path])=>path.endsWith('/replay')).map(([,body])=>(body as any).event)).toEqual(['normal','heat_excursion']);
  });
});

describe('Save the Load failure and stream guards',()=>{
  it.each([
    ['simulation provenance',(value:any)=>{value.simulation=false;}],
    ['model provenance',(value:any)=>{delete value.provenance.model_kind;}],
    ['unbounded route geometry',(value:any)=>{value.rescue.options[0].geometry.coordinates=[[181,40],[1,2]];}],
    ['missing estimated quality',(value:any)=>{value.freshness.remaining_quality_hours=null;}],
    ['timezone missing',(value:any)=>{value.sensor.observed_at='2026-10-30T12:00:00';}],
    ['assignment-count mismatch',(value:any)=>{value.rescue.plan_summary.assignments_count=999;}],
  ])('rejects malformed %s instead of inventing a usable result',async(_name,change)=>{
    const normal=vi.mocked(api).getMockImplementation()!;
    vi.mocked(api).mockImplementation(async(path,body)=>{const value=await normal(path,body);if(path==='/freshness/sessions'){const altered=structuredClone(value);change(altered);return altered;}return value;});
    render(<FreshnessLab/>);await screen.findByRole('button',{name:'Start rescue experiment'});fireEvent.click(screen.getByRole('button',{name:'Start rescue experiment'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('could not be verified');
    expect(screen.queryByText('Point quality-window estimate')).not.toBeInTheDocument();
  });
  it('does not create duplicate experiments while the first request is pending',async()=>{
    let resolve!:(value:unknown)=>void;const normal=vi.mocked(api).getMockImplementation()!;
    vi.mocked(api).mockImplementation((path,body)=>path==='/freshness/sessions'?new Promise(done=>{resolve=done;}):normal(path,body));
    render(<FreshnessLab/>);const start=await screen.findByRole('button',{name:'Start rescue experiment'});fireEvent.click(start);fireEvent.click(start);
    expect(vi.mocked(api).mock.calls.filter(([path])=>path==='/freshness/sessions')).toHaveLength(1);
    await act(async()=>resolve(capture('heated')));await screen.findByText('Point quality-window estimate');
  });
  it('keeps failed approval outcomes uncertain until the experiment is reloaded',async()=>{
    const normal=vi.mocked(api).getMockImplementation()!;
    vi.mocked(api).mockImplementation(async(path,body)=>{if(path.endsWith('/approve'))throw new Error('Connection ended before receipt');return normal(path,body);});
    await start();openReview();confirmReview();fireEvent.click(screen.getByRole('button',{name:'Approve simulated rescue plan'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('Connection ended before receipt');
    expect(screen.getByRole('button',{name:'Approve simulated rescue plan'})).toBeDisabled();
    expect(screen.getByText(/action’s outcome needs confirmation/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Reload this experiment'}));
    await waitFor(()=>expect(screen.queryByText(/action’s outcome needs confirmation/)).not.toBeInTheDocument());
    expect(vi.mocked(api).mock.calls.filter(([path])=>path.endsWith('/approve'))).toHaveLength(1);
  });
  it('treats an explicit stale-approval conflict as a failed decision and preserves the form',async()=>{
    const normal=vi.mocked(api).getMockImplementation()!;
    vi.mocked(api).mockImplementation(async(path,body)=>{if(path.endsWith('/approve'))throw Object.assign(new Error('stale'),{status:409});return normal(path,body);});
    await start();openReview();confirmReview();fireEvent.click(screen.getByRole('button',{name:'Approve simulated rescue plan'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('Approval did not complete');
    expect(screen.getByRole('region',{name:'Human rescue approval'})).toBeInTheDocument();
    expect(screen.queryByRole('region',{name:'Confirmed rescue receipt'})).not.toBeInTheDocument();
  });
  it('refreshes stale network context without changing the stored quality history',async()=>{
    createName='heated';const normal=vi.mocked(api).getMockImplementation()!;
    vi.mocked(api).mockImplementation(async(path,body)=>{const value=await normal(path,body);if(path==='/freshness/sessions'){server.status='stale';server.current_network_revision=1;return structuredClone(server) as any;}return value;});
    await start();const history=structuredClone(server.readings);const age=server.freshness.equivalent_age_hours;
    expect(screen.getByText(/uses network revision 0; current inputs are at revision 1/)).toBeInTheDocument();
    expect(screen.getByRole('button',{name:`Review ${selectedName()}`})).toBeDisabled();
    fireEvent.click(screen.getByRole('button',{name:'Refresh plan for new review'}));
    await waitFor(()=>expect(api).toHaveBeenCalledWith(`/freshness/sessions/${server.id}/rebase`,{expected_version:2,expected_network_revision:1}));
    await waitFor(()=>expect(screen.queryByText(/uses network revision 0; current inputs/)).not.toBeInTheDocument());
    expect(server.readings).toEqual(history);expect(server.freshness.equivalent_age_hours).toBe(age);
  });
  it('displays a prior approved decision as historical when new sensor frames need review',async()=>{
    const normal=vi.mocked(api).getMockImplementation()!;
    vi.mocked(api).mockImplementation(async(path,body)=>{if(path==='/freshness/sessions'){server=approved();server.status='review_required';server.version=4;return structuredClone(server) as any;}return normal(path,body);});
    await start();
    expect(screen.getByRole('region',{name:'Confirmed rescue receipt'})).toHaveTextContent('Previously recorded rescue decision');
    expect(screen.getByText(/no automatic reassignment occurred/)).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Refresh plan for new review'})).toBeEnabled();
    expect(screen.getByRole('button',{name:'Replay heat excursion'})).toBeEnabled();
    expect(screen.getByRole('button',{name:`Review ${selectedName()}`})).toBeDisabled();
  });
  it('opens the captured truck and shipment as an inspection context when a receipt is historical',async()=>{
    const onOpenDrive=vi.fn();const normal=vi.mocked(api).getMockImplementation()!;
    vi.mocked(api).mockImplementation(async(path,body)=>{if(path==='/freshness/sessions'){server=approved();server.current_network_revision=2;return structuredClone(server) as any;}return normal(path,body);});
    await start({onOpenDrive});
    expect(screen.getByRole('region',{name:'Confirmed rescue receipt'})).toHaveTextContent('Previously recorded rescue decision');
    expect(screen.getByText(/current operation has changed since this receipt/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Inspect driver assignment context'}));
    expect(onOpenDrive).toHaveBeenCalledWith({truckId:server.shipment.truck_id,shipmentId:server.shipment.id});
  });
  it('handles a gateway experiment awaiting product readings without inventing zero sensor values',async()=>{
    const normal=vi.mocked(api).getMockImplementation()!;
    vi.mocked(api).mockImplementation(async(path,body)=>{const value=await normal(path,body);if(path==='/freshness/sessions'){
      server.sensor=null;server.readings=[];server.provenance.telemetry='gateway_reported';server.freshness.status='unscored';server.freshness.coverage={complete:false,warnings:['Waiting for the first product-temperature reading']};server.freshness.timeline=[];
      server.freshness.remaining_quality_hours=null;server.freshness.remaining_reference_hours=null;server.freshness.remaining_hours_at_forecast_temperature=null;server.freshness.equivalent_age_hours=null;server.freshness.consumed_fraction=null;server.freshness.sensitivity={lower_hours:null,upper_hours:null};
      server.rescue.proposal_hash=null;server.rescue.proposal_id=null;server.rescue.proposed_destination_id=null;server.rescue.plan_summary=null;server.rescue.proposed_assignments=[];server.rescue.options=[];return structuredClone(server) as any;}return value;});
    await start();expect(screen.getByText('Gateway-reported readings')).toBeInTheDocument();
    expect(screen.getAllByText('Not supplied')).toHaveLength(5);
    expect(metric('Point quality-window estimate').getByText('Not scored')).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Replay heat excursion'})).toBeDisabled();
    expect(screen.getByText('Waiting for the first product-temperature reading')).toBeInTheDocument();
  });
  it('polls newer stored readings and disables an older captured approval form',async()=>{
    await startWithFakeTimers();openReview();confirmReview();server=capture('delayed');
    await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});
    expect(screen.getByRole('button',{name:'Approve simulated rescue plan'})).toBeDisabled();
    expect(screen.getByText(/selection or calculation changed after this review opened/)).toBeInTheDocument();
    expect(vi.mocked(api).mock.calls.some(([path,body])=>path.endsWith('/approve')&&body!==undefined)).toBe(false);
  });
  it('preserves a newer capture when polling returns an older version',async()=>{
    await startWithFakeTimers();const newer=structuredClone(server);server=capture('initial');
    await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});
    expect(screen.getByRole('alert')).toHaveTextContent('older experiment version');
    fireEvent.click(screen.getByRole('button',{name:'Export captured freshness experiment'}));
    expect(downloadCaptured).toHaveBeenCalledWith(expect.any(String),expect.objectContaining({version:newer.version,freshness:newer.freshness}));
  });
  it('supports turning observation polling off and cleans up its timer on unmount',async()=>{
    vi.useFakeTimers();const view=render(<FreshnessLab/>);await act(async()=>{});await act(async()=>fireEvent.click(screen.getByRole('button',{name:'Start rescue experiment'})));
    fireEvent.click(screen.getByRole('checkbox',{name:'Follow incoming readings every 5s'}));
    const before=vi.mocked(api).mock.calls.length;await act(async()=>{await vi.advanceTimersByTimeAsync(10000);});expect(api).toHaveBeenCalledTimes(before);
    view.unmount();expect(vi.getTimerCount()).toBe(0);
  });
});
