import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { api } from './api';
vi.mock('./DataExplorer', () => ({default: () => <div>Bounded data explorer</div>}));
vi.mock('./NetworkMap', () => ({ default: ({planOverlay,selectedAlternative}:any) => <div>Missouri logistics map<span data-testid="map-scope">{planOverlay?.label}</span><span data-testid="map-alternative">{selectedAlternative}</span></div> }));
vi.mock('./api', async importOriginal => ({ ...await importOriginal<object>(), api: vi.fn() }));
vi.mock('recharts', () => {
  const Wrapper = ({ children }: { children?: React.ReactNode }) => <div>{children}</div>;
  const Chart = ({ children }: { children?: React.ReactNode }) => <svg>{children}</svg>;
  return { AreaChart: Chart, LineChart: Chart, ResponsiveContainer: Wrapper, Area: () => null, CartesianGrid: () => null, Line: () => null, Tooltip: () => null, XAxis: () => null, YAxis: () => null };
});
const network = { seed: 20261026, revision: 0, provenance: 'SIMULATION', nodes: [{ id: 'DC1', name: 'Columbia DC', kind: 'dc', coordinates: [-92.3, 38.9] }, { id: 'D01', name: 'Simulated destination', kind: 'destination', coordinates: [-90.2, 38.6] }], trucks: [{ id: 'T01', eligible: true, capacity_kg: 1500 }], lots: [{ id: 'L01', held: true, recalled: false, inventory_kg: 1500 }], shipments: [{ id: 'SH01', origin: 'DC1', destination: 'D01', lot_id: 'L02', truck_id: 'T01', quantity_kg: 400, temperature_c: 2, estimated_hours: 2, estimated_distance_km: 130, deadline_hours: 6 }], telemetry: [], events: [] };
const scenario = { id: 'proposal-1', scenario: 'A', name: 'Baseline distribution', solver_status: 'OPTIMAL', feasible: true, total_logistics_cost: 200, unmet_demand_kg: 100, delayed_shipments: 0, affected_shipments: 0, review_priority_count: 0, food_waste_kg: 0, constraint_violations: 0, proposed_hold_lots: [], shipments: network.shipments, limitations: 'Simulated allocation' };
const roadRoute = {fallback:true,payload:{routes:[{distance:130000,duration:7200,geometry:{type:'LineString',coordinates:[[-92.3,38.9],[-90.2,38.6]]}},{distance:140000,duration:7800,geometry:{type:'LineString',coordinates:[[-92.3,38.9],[-91.8,38.1],[-90.2,38.6]]}}]}};
describe('AEGIS workflow', () => {
  beforeEach(() => {
    window.history.replaceState(null,'','/');
    vi.mocked(api).mockClear();
    vi.mocked(api).mockImplementation(async (path: string) => {
      if (path === '/drive/T01') return {truck_id:'T01',network_revision:0,focus:{mode:'locked',version:0,parked_until:null,interaction_allowed:false},assignments:[],vehicle:{fuel_percent:60,fuel_liters:108,tank_capacity_liters:180,estimated_range_km:380,coordinates:[-92.3,38.9],observed_at:'2026-10-26T08:00:00-05:00',position_label:'Simulated origin'},events:[]} as any;
      if (path === '/network') return network as any;
      if (path === '/scenarios') return [scenario] as any;
      if (path === '/model') return { status: 'Retrospective feasibility only' } as any;
      if (path === '/proposals/A') return scenario as any;
      if (path === '/proposals/proposal-1/approve') return { status: 'approved' } as any;
      if (path.startsWith('/evidence/')) return { status: 'unavailable' } as any;
      if (path === '/inventory') return { files: [] } as any;
      return [] as any;
    });
  });
  it('labels simulation and requires an identified reason before approval', async () => {
    render(<App />);
    expect(await screen.findByText('Missouri logistics map')).toBeInTheDocument();
    expect(screen.getByText('SIMULATED OPERATIONS')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Review scenario A' }));
    await screen.findByRole('dialog');
    const approve = screen.getByRole('button', { name: 'Approve simulated plan' });
    expect(approve).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Dispatcher name'), { target: { value: 'Test dispatcher' } });
    fireEvent.change(screen.getByLabelText('Reason for approval'), { target: { value: 'Safety and capacity reviewed' } });
    expect(approve).toBeEnabled();
    fireEvent.click(approve);
    await waitFor(() => expect(api).toHaveBeenCalledWith('/proposals/proposal-1/approve', { actor: 'Test dispatcher', reason: 'Safety and capacity reviewed' }));
    await screen.findByText('Scenario approved. Driver assignments updated and audit recorded.');
  });
  it('shows no driver trip before approval', async () => {
    render(<App />);
    await screen.findByText('Missouri logistics map');
    fireEvent.click(screen.getByRole('button', { name: /AEGIS Drive/ }));
    expect(await screen.findByText('No approved assignments')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Report an issue/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Confirm safely parked' })).toBeEnabled();
  });
  it('clears old driver assignments and scenario rows when a partial refresh fails', async () => {
    const normal = vi.mocked(api).getMockImplementation()!;
    let failed = false;
    vi.mocked(api).mockImplementation(async (path,body) => {
      if (failed && (path === '/driver' || path === '/scenarios')) throw new Error('temporarily unavailable');
      if (path === '/driver') return network.shipments as any;
      return normal(path,body);
    });
    render(<App />);await screen.findByText('Missouri logistics map');
    expect(screen.getByText('APPROVED ASSIGNMENTS').closest('.stat')).toHaveTextContent('1');
    failed = true;fireEvent.click(screen.getByRole('button',{name:'Reload application data'}));
    await screen.findByText(/Some application data is unavailable/);
    expect(screen.getByText('APPROVED ASSIGNMENTS').closest('.stat')).toHaveTextContent('0');
    expect(screen.queryByRole('button',{name:'Review scenario A'})).not.toBeInTheDocument();
  });
  it('reports stale fallback as a failed refresh rather than new source success', async () => {
    const normal = vi.mocked(api).getMockImplementation()!;
    vi.mocked(api).mockImplementation(async (path,body) => path.startsWith('/refresh/openmeteo') ? {stale:true,refresh_error:'provider timeout',payload:{}} as any : normal(path,body));
    render(<App />);await screen.findByText('Missouri logistics map');
    fireEvent.click(screen.getByRole('button',{name:'Sources & evidence'}));
    fireEvent.click(screen.getAllByRole('button',{name:'Refresh'})[0]);
    await screen.findByText(/refresh unavailable; showing the dated cached response/);
    expect(screen.queryByText('Open-Meteo forecast refreshed.')).not.toBeInTheDocument();
  });
  it('preserves a requested shipment route across application reloads', async () => {
    const normal = vi.mocked(api).getMockImplementation()!;
    vi.mocked(api).mockImplementation(async (path,body) => {
      if (path === '/route') return roadRoute as any;
      if (path === '/evidence/osrm_route') return {fallback:false,payload:{routes:[]}} as any;
      return normal(path,body);
    });
    render(<App />);await screen.findByText('Missouri logistics map');
    fireEvent.click(screen.getByRole('button',{name:'Request road route'}));
    await screen.findByText(/Requested route for SH01/);
    fireEvent.click(screen.getByRole('button',{name:'Reload application data'}));
    await waitFor(() => expect(vi.mocked(api).mock.calls.filter(([p]) => p === '/network').length).toBeGreaterThan(1));
    expect(screen.getByText(/Requested route for SH01/)).toBeInTheDocument();
  });
  it('shows actual ingestion outcomes without calling unrecognized or duplicate inputs accepted', async () => {
    const normal=vi.mocked(api).getMockImplementation()!;
    vi.mocked(api).mockImplementation(async(path,body)=>path==='/evidence-summary' ? [
      {file:'unrecognized.csv',status:'unrecognized'},
      {file:'duplicate.csv',source:'beam',status:'duplicate',duplicate_of:'original.csv',rows:12},
      {file:'conflict.csv',source:'beam',status:'conflict'},
      {file:'accepted.csv',source:'beam',status:'ingested',rows:12},
      {file:'legacy.csv',source:'beam',rows:12},
    ] as any : normal(path,body));
    render(<App/>);await screen.findByText('Missouri logistics map');
    fireEvent.click(screen.getByRole('button',{name:'Sources & evidence'}));
    await screen.findByText('unrecognized.csv');
    const row=(name:string)=>within(screen.getByText(name).closest('tr')!);
    expect(row('unrecognized.csv').getByText(/not ingested or merged/)).toBeInTheDocument();
    expect(row('duplicate.csv').getByText(/no additional observations/)).toBeInTheDocument();
    expect(row('conflict.csv').getByText(/Conflicting exports/)).toBeInTheDocument();
    expect(row('legacy.csv').getByText(/acceptance has not been established/)).toBeInTheDocument();
    expect(row('accepted.csv').getByText(/Source schema accepted/)).toBeInTheDocument();
    expect(screen.getAllByText(/Source schema accepted/)).toHaveLength(1);
  });
  it('dedicated Drive avoids fetching bulk recall, inventory and model evidence', async () => {
    window.history.replaceState(null,'','/?mode=drive');
    render(<App />);await screen.findByText('No approved assignments');
    expect(screen.queryByRole('navigation',{name:'Main navigation'})).not.toBeInTheDocument();
    expect(vi.mocked(api).mock.calls.every(([path]) => path === '/network' || path.startsWith('/drive/'))).toBe(true);
    window.history.replaceState(null,'','/');
  });
  it('shows an approval rejection inside the still-open dialog and clears prior success', async () => {
    const normal=vi.mocked(api).getMockImplementation()!;
    vi.mocked(api).mockImplementation(async(path,body)=>{
      if(path==='/proposals/proposal-1/approve') throw new Error('Network changed; generate a fresh proposal');
      return normal(path,body);
    });
    render(<App/>);await screen.findByText('Missouri logistics map');
    fireEvent.click(screen.getByRole('button',{name:'Review scenario A'}));
    const dialog=await screen.findByRole('dialog');
    fireEvent.change(within(dialog).getByLabelText('Dispatcher name'),{target:{value:'Reviewer'}});
    fireEvent.change(within(dialog).getByLabelText('Reason for approval'),{target:{value:'Review constraints'}});
    fireEvent.click(within(dialog).getByRole('button',{name:'Approve simulated plan'}));
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Approval did not complete: Network changed');
    expect(screen.queryByText('Proposal prepared for review.')).not.toBeInTheDocument();
    expect(screen.queryByText('Scenario approved. Driver assignments updated and audit recorded.')).not.toBeInTheDocument();
    expect(within(dialog).getByRole('button',{name:'Keep under review'})).toBeEnabled();
  });
  it('produces a visible recompute receipt even when deterministic results are identical', async () => {
    render(<App/>);await screen.findByText('Missouri logistics map');
    fireEvent.click(screen.getByRole('button',{name:'Recompute'}));
    expect(await screen.findByText(/Last computation.*revision 0.*1 response plans/)).toHaveTextContent('Totals and selected trips match the previous run');
    expect(vi.mocked(api).mock.calls.some(([path])=>path.startsWith('/proposals/'))).toBe(false);
  });
  it('shows failed recomputation near the results and removes a stale successful receipt', async () => {
    const normal=vi.mocked(api).getMockImplementation()!;let fail=false;
    vi.mocked(api).mockImplementation(async(path,body)=>{if(fail && path==='/scenarios')throw new Error('Solver unavailable');return normal(path,body);});
    render(<App/>);await screen.findByText('Missouri logistics map');
    fireEvent.click(screen.getByRole('button',{name:'Recompute'}));await screen.findByText(/Recomputed 1 response plans/);
    fail=true;fireEvent.click(screen.getByRole('button',{name:'Recompute'}));
    expect(await screen.findByText(/The full comparison could not be recomputed/)).toBeInTheDocument();
    expect(screen.queryByText(/Recomputed 1 response plans/)).not.toBeInTheDocument();
  });
  it('changes only the map overlay when inspecting a scenario allocation', async () => {
    render(<App/>);await screen.findByText('Missouri logistics map');
    fireEvent.click(screen.getByRole('button',{name:'Show scenario A allocation on map'}));
    expect(screen.getByLabelText('Map allocation')).toHaveValue('A');
    expect(screen.getByTestId('map-scope')).toHaveTextContent('Scenario A: proposed allocation');
    expect(document.activeElement?.id).toBe('command-network-map');
    expect(vi.mocked(api).mock.calls.some(([path])=>path.startsWith('/proposals/'))).toBe(false);
    fireEvent.change(screen.getByLabelText('Map allocation'),{target:{value:'approved'}});
    expect(screen.getByTestId('map-scope')).toHaveTextContent('Current approved assignments');
  });
  it('selects a road alternative without writing a new assignment or changing planning inputs', async () => {
    const normal=vi.mocked(api).getMockImplementation()!;
    vi.mocked(api).mockImplementation(async(path,body)=>path==='/route'?roadRoute as any:normal(path,body));
    render(<App/>);await screen.findByText('Missouri logistics map');
    expect(screen.getByText(/No road route has been requested/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Request road route'}));
    await screen.findByText(/Requested route for SH01/);
    await waitFor(()=>expect(document.activeElement?.id).toBe('command-route-result'));
    fireEvent.click(screen.getByRole('button',{name:'Highlight alternative 2'}));
    expect(screen.getByTestId('map-alternative')).toHaveTextContent('1');
    expect(screen.getByRole('button',{name:'Highlight alternative 2'})).toHaveAttribute('aria-pressed','true');
    expect(screen.getByText(/does not replace the candidate's fixed planning estimate/)).toBeInTheDocument();
    expect(vi.mocked(api).mock.calls.filter(([,body])=>body!==undefined).map(([path])=>path)).toEqual(['/delivery-outlook','/route']);
  });
  it('makes a malformed route response visibly fail instead of showing an empty result', async () => {
    const normal=vi.mocked(api).getMockImplementation()!;
    vi.mocked(api).mockImplementation(async(path,body)=>path==='/route'?{payload:{routes:[]}} as any:normal(path,body));
    render(<App/>);await screen.findByText('Missouri logistics map');
    fireEvent.click(screen.getByRole('button',{name:'Request road route'}));
    await waitFor(()=>expect(screen.getAllByText(/No usable route geometry was returned/).length).toBeGreaterThan(0));
    expect(screen.queryByRole('heading',{name:'Route alternatives & road review'})).not.toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Request road route'})).toBeEnabled();
  });
  it('opens the review queue from the bell and distinguishes a candidate from an approved trip', async () => {
    render(<App/>);await screen.findByText('Missouri logistics map');
    fireEvent.click(screen.getByRole('button',{name:'Open review queue'}));
    expect(document.activeElement?.id).toBe('command-review-queue');
    expect(screen.getByText('CANDIDATE TRUCK')).toBeInTheDocument();
    expect(screen.getByText(/has no current approved driver assignment/)).toBeInTheDocument();
    expect(screen.getByText(/Chart: seeded historical simulation trace/)).toBeInTheDocument();
  });
  it('requires reset confirmation and keeps reset errors visible in its dialog', async () => {
    const normal=vi.mocked(api).getMockImplementation()!;
    vi.mocked(api).mockImplementation(async(path,body)=>{if(path==='/demo/reset')throw new Error('Database busy');return normal(path,body);});
    render(<App/>);await screen.findByText('Missouri logistics map');
    fireEvent.click(screen.getByRole('button',{name:'Reset demo'}));
    const dialog=screen.getByRole('dialog');
    expect(vi.mocked(api).mock.calls.some(([path])=>path==='/demo/reset')).toBe(false);
    fireEvent.click(within(dialog).getByRole('button',{name:'Confirm reset simulation'}));
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Reset did not complete: Database busy');
  });
  it('preserves an actual confirmed event receipt when a total network reload failure unmounts the simulator', async () => {
    const normal=vi.mocked(api).getMockImplementation()!;let unavailable=false;
    const totals={total_logistics_cost:200,unmet_demand_kg:100,selected_shipments:1,solver_status:'OPTIMAL',constraint_violations:0};
    const preview={simulation:true,read_only:true,operational_state_modified:false,event:'temperature_excursion',event_label:'Simulated cargo temperature excursion',shipment_id:'SH01',network_revision:0,preview_id:'a'.repeat(64),shipment:{id:'SH01',changes:[]},scenarios:['A','B','C','D'].map(id=>({scenario:id,name:id,before:totals,after:totals,delta:{total_logistics_cost:0,unmet_demand_kg:0,selected_shipments:0},added_shipments:[],removed_shipments:[],lot_changes:[],proposed_hold_lots_added:[],proposed_hold_lots_removed:[]})),assignments:{would_be_invalidated:0},route_effects:{geometry_changed:false,stop_order_changed:false,explanation:'Geometry stays unchanged'},resource_effects:[],limitations:[]};
    vi.mocked(api).mockImplementation(async(path,body)=>{
      if(path==='/events/preview')return preview as any;
      if(path==='/events'){unavailable=true;return {operational_state_modified:true,assignments_invalidated:true,network_revision_before:0,revision:1,preview_id:preview.preview_id,assignments_removed:0} as any;}
      if(path==='/network'&&unavailable)throw new Error('Network disconnected after application');
      return normal(path,body);
    });
    render(<App/>);await screen.findByText('Missouri logistics map');
    fireEvent.click(screen.getByRole('button',{name:'Preview event impact'}));
    await screen.findByText(/Preview produced for SH01/);
    fireEvent.click(screen.getByRole('checkbox',{name:/I intend to change this simulation/}));
    fireEvent.click(screen.getByRole('button',{name:'Apply previewed event'}));
    const receipt=await screen.findByRole('complementary',{name:'Confirmed event receipt'});
    expect(await within(receipt).findByRole('alert')).toHaveTextContent('The event was applied, but the current network is unavailable');
    expect(within(receipt).getByText(/Applied at network revision 1/)).toBeInTheDocument();
    expect(screen.queryByRole('heading',{name:'Preview a disruption before applying it'})).not.toBeInTheDocument();
    expect(vi.mocked(api).mock.calls.filter(([path])=>path==='/events')).toHaveLength(1);
    expect(within(receipt).getByRole('button',{name:'Export confirmed event JSON'})).toBeEnabled();
  });
  it('opens and closes activity inspection without creating an extra workspace or a decision', async () => {
    const normal=vi.mocked(api).getMockImplementation()!;
    vi.mocked(api).mockImplementation(async(path,body)=>path.startsWith('/activity')?{available:true,records:[],actions:[],snapshot_latest_id:0,snapshot_id:'a'.repeat(64),total_matching:0,next_cursor:null,read_only:true,operational_state_modified:false,generated_at:'2026-10-29T20:00:00+00:00',limitations:['Only explicitly recorded local actions appear.']} as any:normal(path,body));
    render(<App/>);await screen.findByText('Missouri logistics map');
    fireEvent.click(screen.getByRole('button',{name:'Open activity history'}));
    expect(await screen.findByRole('heading',{name:'Activity history'})).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Open activity history'})).toHaveAttribute('aria-expanded','true');
    screen.getByRole('button',{name:'Request road route'}).focus();
    fireEvent.click(screen.getByRole('button',{name:'Open activity history'}));
    expect(document.activeElement?.id).toBe('activity-history');
    expect(within(screen.getByRole('navigation',{name:'Main navigation'})).getAllByRole('button')).toHaveLength(10);
    fireEvent.click(screen.getByRole('button',{name:'Close activity history'}));
    expect(screen.queryByRole('heading',{name:'Activity history'})).not.toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Open activity history'})).toHaveFocus();
    expect(vi.mocked(api).mock.calls.filter(([,body])=>body!==undefined).map(([path])=>path)).toEqual(['/delivery-outlook']);
  });
});
