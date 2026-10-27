import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import DispatchReadiness from './DispatchReadiness';
import { api } from './api';
vi.mock('./api',()=>({api:vi.fn()}));
const review = {network_revision:4,checked_at:'2026-10-27T10:00:00Z',summary:{total_assignments:2,blocked:1,review_required:1,ready_for_review:0},assignments:[{shipment_id:'SH03',truck_id:'T03',lot_id:'L03',status:'review_required',checks:[{id:'assignment_ack',label:'Assignment acknowledgment',category:'workflow',status:'review_required',detail:'Driver acknowledgment is outstanding.'}],blockers:[],reviews_required:['assignment_ack']},{shipment_id:'SH04',truck_id:'T04',lot_id:'L04',status:'blocked',checks:[{id:'held',label:'Lot eligibility',category:'hard_constraint',status:'blocked',detail:'The current lot is held.'}],blockers:['held'],reviews_required:[]}],limitations:['Simulation; no dispatch or food-safety certification.']};
beforeEach(()=>{vi.mocked(api).mockReset();vi.mocked(api).mockResolvedValue(review);});
it('inspects each trip and filters constraint blocks separately from workflow review',async()=>{
  render(<DispatchReadiness networkRevision={4}/>);
  expect(await screen.findByText('Driver acknowledgment is outstanding.')).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Readiness status'),{target:{value:'blocked'}});
  expect(screen.getByText('The current lot is held.')).toBeInTheDocument();
  expect(screen.queryByText('Driver acknowledgment is outstanding.')).not.toBeInTheDocument();
  expect(screen.getByText(/This read-only checklist does not dispatch/)).toBeInTheDocument();
  expect(vi.mocked(api).mock.calls.every(call=>call.length===1)).toBe(true);
});
it('clears a failed report instead of keeping earlier passing checks visible',async()=>{
  render(<DispatchReadiness networkRevision={4}/>);await screen.findByText('Driver acknowledgment is outstanding.');
  vi.mocked(api).mockRejectedValueOnce(new Error('Readiness unavailable'));
  fireEvent.click(screen.getByRole('button',{name:'Refresh readiness'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('Readiness unavailable');
  expect(screen.queryByText('Driver acknowledgment is outstanding.')).not.toBeInTheDocument();
});
it('withholds checks from a different network revision',async()=>{
  render(<DispatchReadiness networkRevision={5}/>);
  expect(await screen.findByRole('alert')).toHaveTextContent('Network changed');
  expect(screen.queryByText('The current lot is held.')).not.toBeInTheDocument();
});
it('ignores an obsolete response after the displayed desk context changes',async()=>{
  let resolve!: (value:unknown)=>void; const pending = new Promise(res=>{resolve=res;});
  vi.mocked(api).mockImplementationOnce(()=>pending);
  const view=render(<DispatchReadiness networkRevision={4}/>);
  vi.mocked(api).mockResolvedValue({...review,network_revision:5,assignments:[],summary:{total_assignments:0,blocked:0,review_required:0,ready_for_review:0}});
  view.rerender(<DispatchReadiness networkRevision={5}/>);
  await screen.findByText(/No approved trips to inspect/);
  await act(async()=>resolve(review));
  await waitFor(()=>expect(screen.queryByText('Driver acknowledgment is outstanding.')).not.toBeInTheDocument());
});
