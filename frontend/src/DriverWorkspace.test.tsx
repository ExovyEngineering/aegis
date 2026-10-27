import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import DriverWorkspace from './DriverWorkspace';
import { api } from './api';
vi.mock('./api', async () => ({...await vi.importActual('./api'),api:vi.fn()}));
vi.mock('./DriverExposure', () => ({default: () => <div>Parked route review</div>}));
const network:any={revision:0,nodes:[{id:'DC1',name:'Simulated Columbia origin'},{id:'D01',name:'Simulated next destination'}],trucks:[{id:'T01'},{id:'T02'}]};
const shipment={id:'SH01',truck_id:'T01',lot_id:'L02',origin:'DC1',destination:'D01',quantity_kg:400,temperature_c:2.5,estimated_hours:1.5,estimated_distance_km:100,acknowledged:false,instruction:'Reviewed simulated assignment'};
const vehicle={fuel_percent:62,fuel_liters:111.6,tank_capacity_liters:180,estimated_range_km:398.6,consumption_l_per_100km:28,coordinates:[-92.33,38.95],position_label:'Simulated dispatch-origin reference',observed_at:'2026-10-26T08:00:00-05:00',provenance:'simulation',simulation:true};
let mode='locked',version=0;
function snapshot(truck_id='T01') { return {truck_id,network_revision:0,focus:{mode,version,interaction_allowed:mode==='parked',parked_until:mode==='parked'?new Date(Date.now()+600000).toISOString():null},assignments:[shipment],vehicle,events:[]}; }
beforeEach(() => { mode='locked';version=0;vi.mocked(api).mockReset();vi.mocked(api).mockImplementation(async (path,body:any) => {
  if(path.endsWith('/focus')) {mode=body.mode;version++;return snapshot().focus as any;}
  if(path.startsWith('/drive/'))return snapshot() as any;
  return {} as any;
}); });
it('shows visual simulated trip data with typing and acknowledgment locked by default', async () => {
  render(<DriverWorkspace network={network} onChanged={vi.fn()} />);
  await screen.findByRole('heading',{name:'Simulated next destination'});
  expect(screen.getByText('62')).toBeInTheDocument();
  expect(screen.getByText('FUEL SCENARIO')).toBeInTheDocument();
  expect(screen.getByRole('button',{name:/Report an issue/})).toBeDisabled();
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  expect(screen.queryByText('Acknowledge assignment')).not.toBeInTheDocument();
  expect(screen.getByText(/does not detect actual motion/)).toBeInTheDocument();
});
it('requires parked attestation before reporting and hides the form again when locked', async () => {
  const changed=vi.fn().mockResolvedValue(undefined);render(<DriverWorkspace network={network} onChanged={changed} />);
  await screen.findByRole('heading',{name:'Simulated next destination'});
  fireEvent.click(screen.getByRole('button',{name:'Confirm safely parked'}));
  await waitFor(() => expect(api).toHaveBeenCalledWith('/drive/T01/focus',{mode:'parked',expected_version:0,parked_confirmation:true}));
  await screen.findByRole('button',{name:'Lock for driving'});
  fireEvent.click(screen.getByRole('button',{name:/Report an issue/}));
  fireEvent.change(screen.getByLabelText('Report a driver incident'),{target:{value:'Parked to review simulated issue'}});
  fireEvent.click(screen.getByRole('button',{name:'Send to dispatcher'}));
  await waitFor(() => expect(api).toHaveBeenCalledWith('/driver/incident',{shipment_id:'SH01',description:'Parked to review simulated issue',expected_network_revision:0}));
  await screen.findByText('Incident submitted for dispatcher review.');
  fireEvent.click(screen.getByRole('button',{name:'Lock for driving'}));
  await screen.findByRole('button',{name:'Confirm safely parked'});
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  expect(screen.getByRole('button',{name:/Report an issue/})).toBeDisabled();
});
it('quick reports use the selected approved trip and cannot silently reroute it', async () => {
  mode='parked';render(<DriverWorkspace network={network} onChanged={vi.fn().mockResolvedValue(undefined)} />);
  await screen.findByRole('button',{name:'Lock for driving'});
  fireEvent.click(screen.getByRole('button',{name:/Report an issue/}));
  fireEvent.click(screen.getByRole('button',{name:'Refrigeration concern'}));
  await waitFor(() => expect(api).toHaveBeenCalledWith('/drive/T01/quick-report',{shipment_id:'SH01',kind:'refrigeration',expected_network_revision:0}));
  expect(vi.mocked(api).mock.calls.some(([path]) => path.startsWith('/proposals/'))).toBe(false);
});
it('expired or failed driver snapshots never leave interaction controls enabled', async () => {
  mode='parked';vi.mocked(api).mockImplementation(async () => ({...snapshot(),focus:{mode:'parked',version:1,interaction_allowed:true,parked_until:'2020-01-01T00:00:00Z'}} as any));
  render(<DriverWorkspace network={network} onChanged={vi.fn()} />);
  await screen.findByRole('heading',{name:'Simulated next destination'});
  expect(screen.getByRole('button',{name:/Trip route/})).toBeDisabled();
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
});

it('a rejected stale-trip acknowledgment never creates optimistic success', async () => {
  mode='parked';const changed=vi.fn();
  vi.mocked(api).mockImplementation(async path => {
    if(path.startsWith('/driver/')) throw new Error('Network changed; review the current trip');
    return snapshot() as any;
  });
  render(<DriverWorkspace network={network} onChanged={changed} />);
  await screen.findByRole('button',{name:'Lock for driving'});
  fireEvent.click(screen.getByRole('button',{name:/Dispatch instructions/}));
  fireEvent.click(screen.getByRole('button',{name:'Acknowledge assignment'}));
  await screen.findByText(/Network changed; review the current trip/);
  expect(changed).not.toHaveBeenCalled();
  expect(api).toHaveBeenCalledWith('/driver/SH01/acknowledge',{expected_network_revision:0});
  expect(screen.getByRole('button',{name:'Acknowledge assignment'})).toBeEnabled();
});
