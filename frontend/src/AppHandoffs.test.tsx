import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import App from './App';
import { api } from './api';
import type { Network } from './types';

vi.mock('./api', async original => ({ ...await original<object>(), api:vi.fn() }));
vi.mock('./NetworkMap',()=>({default:()=> <div>Test network map</div>}));
vi.mock('./MapViewport',()=>({default:()=>null}));
vi.mock('./DispatchReadiness',()=>({default:()=>null}));
// The real Outlook tests validate its captured data and button guards. Here its
// callback contract exercises App, real Road inputs and real Dispatcher links.
vi.mock('./DeliveryOutlook',()=>({default:({network,onCompareShipmentRoad,onReviewPlans}:any)=><section aria-label="Test outlook callback harness"><button onClick={onReviewPlans}>Review current response plans</button>{network.shipments.map((row:any)=><button key={row.id} onClick={()=>onCompareShipmentRoad(row.id)}>Compare roads for {row.id}</button>)}</section>}));
vi.mock('react-leaflet',()=>({MapContainer:({children}:any)=><div>{children}</div>,CircleMarker:({children}:any)=><div>{children}</div>,Popup:({children}:any)=><div>{children}</div>,Polyline:()=>null,TileLayer:()=>null}));
vi.mock('recharts',()=>{const Wrapper=({children}:any)=><div>{children}</div>;const Chart=({children}:any)=><svg>{children}</svg>;return {AreaChart:Chart,LineChart:Chart,ResponsiveContainer:Wrapper,Area:()=>null,CartesianGrid:()=>null,Line:()=>null,Tooltip:()=>null,XAxis:()=>null,YAxis:()=>null};});

const network=():Network=>({seed:20261026,revision:7,provenance:'Explicit handoff unit simulation',nodes:[
  {id:'DC1',name:'Columbia test origin',kind:'dc',coordinates:[-92.3341,38.9517]},
  {id:'DC2',name:'Kansas City test origin',kind:'dc',coordinates:[-94.58,39.1]},
  {id:'D01',name:'Jefferson City test stop',kind:'destination',coordinates:[-92.17,38.57]},
  {id:'D02',name:'St. Louis test stop',kind:'destination',coordinates:[-90.21,38.62]},
],trucks:[{id:'T01',eligible:true,capacity_kg:1000},{id:'T02',eligible:true,capacity_kg:1000}],lots:[],shipments:[
  {id:'SH01',origin:'DC1',destination:'D01',lot_id:'L01',truck_id:'T01',quantity_kg:100,temperature_c:2,deadline_hours:6,estimated_hours:1,estimated_distance_km:60,review_priority:'routine'},
  {id:'SH02',origin:'DC2',destination:'D02',lot_id:'L02',truck_id:'T02',quantity_kg:200,temperature_c:2,deadline_hours:6,estimated_hours:4,estimated_distance_km:350,review_priority:'routine'},
],telemetry:[],events:[]});
let current:Network;
const roadSnapshot={generated_at:'2026-10-30T12:00:00Z',offline:true,sources:[],examples:[{id:'cross-state',name:'Columbia to Des Moines test example',origin:[-92.3341,38.9517],destination:[-93.625,41.5868]}],limitations:['Explicit unit-test fixture, no real road evidence']};
beforeEach(()=>{
  current=network();window.history.replaceState(null,'','/');vi.mocked(api).mockReset();
  vi.mocked(api).mockImplementation(async(path,body)=>{
    if(path==='/network')return current as any;
    if(path==='/inventory')return {files:[]} as any;
    if(path==='/model')return {status:'No evaluation in this UI fixture'} as any;
    if(path.startsWith('/evidence/'))return {status:'unavailable'} as any;
    if(path==='/dispatch')return {network_revision:current.revision,assignments:[],incidents:[],lots:[]} as any;
    if(path==='/road-intelligence')return roadSnapshot as any;
    if(path==='/road-intelligence/compare')return {compared_at:'2026-10-30T12:01:00Z',request:body,sources:[],alternatives:[{index:0,distance_m:350000,duration_seconds:14400,geometry:{type:'LineString',coordinates:[(body as any).origin,(body as any).destination]},fallback:true,review_required:true,reviews:[]}],limitations:['Explicit estimated unit-test route; no dispatch']} as any;
    return [] as any;
  });
});
const nav=()=>screen.getByRole('navigation',{name:'Main navigation'});
async function begin(){render(<App/>);await screen.findByText('Test network map');}

it('carries a non-first, different-origin candidate into the actual road comparison request',async()=>{
  await begin();fireEvent.click(screen.getByRole('button',{name:'Compare roads for SH02'}));
  const road=await screen.findByRole('region',{name:'Road intelligence workspace'});
  await waitFor(()=>expect(within(road).getByLabelText('Origin longitude')).toHaveValue(-94.58));
  expect(within(road).getByLabelText('Origin latitude')).toHaveValue(39.1);
  expect(within(road).getByLabelText('Destination longitude')).toHaveValue(-90.21);
  expect(within(road).getByLabelText('Destination latitude')).toHaveValue(38.62);
  fireEvent.click(within(road).getByRole('button',{name:'Compare this journey'}));
  await waitFor(()=>expect(api).toHaveBeenCalledWith('/road-intelligence/compare',{origin:[-94.58,39.1],destination:[-90.21,38.62],routing:'estimated',buffer_m:250}));
  expect(vi.mocked(api).mock.calls.filter(([,body])=>body!==undefined).map(([path])=>path)).toEqual(['/road-intelligence/compare']);
});

it('takes the empty Dispatcher shortcut directly to the response comparison',async()=>{
  await begin();fireEvent.click(within(nav()).getByRole('button',{name:'Dispatcher desk'}));
  fireEvent.click(await screen.findByRole('button',{name:'Choose a response plan'}));
  await waitFor(()=>expect(document.activeElement?.id).toBe('command-scenarios'));
  expect(screen.getByRole('heading',{name:'Compare operational scenarios'})).toBeInTheDocument();
  expect(vi.mocked(api).mock.calls.filter(([,body])=>body!==undefined)).toHaveLength(0);
});

it('takes the outlook review shortcut to the same current-plan comparison without proposing',async()=>{
  await begin();fireEvent.click(screen.getByRole('button',{name:'Review current response plans'}));
  await waitFor(()=>expect(document.activeElement?.id).toBe('command-scenarios'));
  expect(vi.mocked(api).mock.calls.some(([path])=>path.startsWith('/proposals/'))).toBe(false);
});

it('opens a fresh named example when generic Road navigation follows a candidate handoff',async()=>{
  await begin();fireEvent.click(screen.getByRole('button',{name:'Compare roads for SH02'}));
  await waitFor(()=>expect(screen.getByLabelText('Origin longitude')).toHaveValue(-94.58));
  fireEvent.click(within(nav()).getByRole('button',{name:'Command center'}));
  fireEvent.click(within(nav()).getByRole('button',{name:'Road intelligence'}));
  await waitFor(()=>expect(screen.getByLabelText('Origin longitude')).toHaveValue(-92.3341));
  expect(screen.getByLabelText('Destination latitude')).toHaveValue(41.5868);
  expect(screen.queryByText(/Selected candidate SH02:/)).not.toBeInTheDocument();
});

it('rejects an unusable candidate coordinate before navigation or a route request',async()=>{
  current.nodes.find(row=>row.id==='DC2')!.coordinates=[181,39.1];
  await begin();fireEvent.click(screen.getByRole('button',{name:'Compare roads for SH02'}));
  expect(await screen.findByText(/This candidate has no usable journey/)).toBeInTheDocument();
  expect(screen.queryByRole('region',{name:'Road intelligence workspace'})).not.toBeInTheDocument();
  expect(vi.mocked(api).mock.calls.some(([path])=>path==='/road-intelligence'||path==='/road-intelligence/compare')).toBe(false);
});
