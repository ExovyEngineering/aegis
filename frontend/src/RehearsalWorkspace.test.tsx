import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import RehearsalWorkspace from './RehearsalWorkspace';
import { api } from './api';

vi.mock('./api',()=>({api:vi.fn()}));
const stages=[
  {id:'overview',title:'Actor, map and simulation',planned_seconds:40,description:'Explain the simulated actor.'},
  {id:'evidence_science',title:'Sources and measured science',planned_seconds:80,description:'Keep the sources distinct.'},
  {id:'disruption',title:'Simulated disruption',planned_seconds:60,description:'Record a simulated event.'},
  {id:'approval',title:'Dispatcher decision',planned_seconds:60,description:'Record a human approval.'},
  {id:'driver',title:'Parked driver workflow',planned_seconds:40,description:'Acknowledge and report while parked.'},
  {id:'closing',title:'Honest limitations',planned_seconds:20,description:'Explain what remains unverified.'},
];
const runtime={mode:'isolated_rehearsal',isolated:true,offline:true,rehearsal_id:'89fae623-1399-4b59-936f-7736b115f024',database_relative_path:'data/rehearsals/89fae623-1399-4b59-936f-7736b115f024.sqlite',warning:'Isolated simulated rehearsal.'};
const clone=(value:any)=>structuredClone(value);
function run(overrides:any={}) {return {id:'run-one',version:1,status:'active',presenter:'Team Taylor',purpose:'Practice the traceable response',run_kind:'automated_check',started_at:'2026-10-28T12:00:00Z',server_time:'2026-10-28T12:01:23Z',elapsed_seconds:83,milestones:[],next_stage_id:'overview',...overrides};}
let state:any;
function reply(path:string,body:any) {
  if(path==='/rehearsal')return clone(state);
  if(path==='/rehearsal/start'){state.active=run({...body});return clone(state.active);}
  if(path.endsWith('/checkpoint')){
    const active=state.active;
    active.milestones.push({stage_id:body.stage_id,outcome:body.outcome,notes:body.notes,recorded_at:'2026-10-28T12:02:00Z',elapsed_seconds:active.elapsed_seconds+5});
    active.version++;active.elapsed_seconds+=5;active.next_stage_id=stages[active.milestones.length]?.id??null;
    return clone(active);
  }
  if(path.endsWith('/finish')){
    const finished={...state.active,status:body.outcome,version:state.active.version+1,notes:body.notes,finished_at:'2026-10-28T12:04:00Z',next_stage_id:null};
    state.active=null;state.runs=[finished,...state.runs];return clone(finished);
  }
  return clone(state.runs.find((item:any)=>path===`/rehearsal/${item.id}`));
}
beforeEach(()=>{
  state={runtime:clone(runtime),stages:clone(stages),active:null,runs:[]};
  vi.mocked(api).mockReset();vi.mocked(api).mockImplementation(async(path,body:any)=>reply(path,body));
  Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:vi.fn().mockResolvedValue(undefined)}});
});
afterEach(()=>vi.useRealTimers());
function enterStageNotes(value='Explained the current stage evidence') {fireEvent.change(screen.getByLabelText('Current stage notes'),{target:{value}});}
function completedRun(overrides:any={}) {return run({status:'completed',version:7,next_stage_id:null,milestones:stages.map((stage,index)=>({stage_id:stage.id,outcome:'covered',notes:`Recorded ${stage.id} evidence`,recorded_at:'2026-10-28T12:04:00Z',elapsed_seconds:index*30})),...overrides});}

it('keeps operator mode read-only and copies a real isolated-launch command',async()=>{
  state.runtime={mode:'operator',isolated:false,offline:false,warning:'Operator workspace.'};
  render(<RehearsalWorkspace/>);
  expect(await screen.findByText('Open a separate practice workspace')).toBeInTheDocument();
  expect(screen.queryByRole('button',{name:'Start rehearsal timer'})).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Copy rehearsal launch command'}));
  await waitFor(()=>expect(navigator.clipboard.writeText).toHaveBeenCalledWith('.venv/Scripts/python scripts/start_rehearsal.py --port 8001'));
  expect(vi.mocked(api).mock.calls.every(call=>call.length===1)).toBe(true);
});

it('does not offer recording controls for a misconfigured runtime',async()=>{
  state.runtime={mode:'misconfigured',isolated:false,offline:true,warning:'Rehearsal path does not match its session.'};
  render(<RehearsalWorkspace/>);
  expect(await screen.findByText('Rehearsal configuration needs correction')).toBeInTheDocument();
  expect(screen.queryByLabelText('Rehearsal presenter')).not.toBeInTheDocument();
});

it('rejects an incomplete context and can retry without inventing isolation',async()=>{
  vi.mocked(api).mockResolvedValueOnce({runtime:{mode:'isolated_rehearsal'},stages,runs:[],active:null});
  render(<RehearsalWorkspace/>);
  expect(await screen.findByRole('alert')).toHaveTextContent('Rehearsal context is unavailable');
  expect(screen.queryByText('Verified isolated rehearsal')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Retry rehearsal context'}));
  expect(await screen.findByLabelText('Rehearsal presenter')).toBeInTheDocument();
});

it('requires identity and purpose and submits the explicitly chosen record type',async()=>{
  render(<RehearsalWorkspace/>);
  const start=await screen.findByRole('button',{name:'Start rehearsal timer'});
  expect(start).toBeDisabled();
  fireEvent.change(screen.getByLabelText('Rehearsal presenter'),{target:{value:'Team Taylor'}});
  fireEvent.change(screen.getByLabelText('Rehearsal purpose'),{target:{value:'  '}});
  expect(start).toBeDisabled();
  fireEvent.change(screen.getByLabelText('Rehearsal purpose'),{target:{value:'Verify the source and driver workflow'}});
  fireEvent.change(screen.getByLabelText('Rehearsal record type'),{target:{value:'automated_check'}});
  fireEvent.click(start);
  expect(await screen.findByText('Rehearsal timer started. Practice actions remain isolated.')).toBeInTheDocument();
  expect(api).toHaveBeenCalledWith('/rehearsal/start',{presenter:'Team Taylor',purpose:'Verify the source and driver workflow',run_kind:'automated_check'});
  expect(screen.getByText(/Automated check/)).toBeInTheDocument();
});

it('uses the server elapsed value rather than inferring duration from a browser date',async()=>{
  state.active=run({started_at:'2020-01-01T00:00:00Z',elapsed_seconds:83});
  render(<RehearsalWorkspace/>);
  await screen.findByText('Now: Actor, map and simulation');
  expect(screen.getByLabelText('Rehearsal elapsed time')).toHaveTextContent('01:23');
  expect(screen.getByText(/not proof of presentation quality/)).toBeInTheDocument();
});

it('requires a skip reason, keeps completion disabled before all stages, and navigates only on request',async()=>{
  state.active=run();const navigate=vi.fn();
  render(<RehearsalWorkspace onNavigate={navigate}/>);
  await screen.findByText('Now: Actor, map and simulation');
  expect(screen.getByRole('button',{name:'Record stage skipped'})).toBeDisabled();
  fireEvent.change(screen.getByLabelText('Rehearsal closing notes'),{target:{value:'Notes for later presentation review'}});
  expect(screen.getByRole('button',{name:'Finish and save rehearsal'})).toBeDisabled();
  expect(navigate).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Open Command'}));expect(navigate).toHaveBeenCalledWith('command');
  enterStageNotes('Skipped this part to rehearse the driver flow');
  fireEvent.click(screen.getByRole('button',{name:'Record stage skipped'}));
  await screen.findByText('Now: Sources and measured science');
  expect(api).toHaveBeenCalledWith('/rehearsal/run-one/checkpoint',{expected_version:1,stage_id:'overview',outcome:'skipped',notes:'Skipped this part to rehearse the driver flow'});
  expect(screen.getByText(/skipped at/)).toBeInTheDocument();
});

it('reloads a rejected stale checkpoint without optimistic success or retaining its obsolete note',async()=>{
  state.active=run();let reject=true;
  vi.mocked(api).mockImplementation(async(path,body:any)=>{
    if(path.endsWith('/checkpoint')&&reject){reject=false;state.active={...run(),version:2,next_stage_id:'evidence_science',milestones:[{stage_id:'overview',outcome:'covered',notes:'Covered by another reviewer',recorded_at:'2026-10-28T12:01:30Z',elapsed_seconds:80}]};throw new Error('Rehearsal changed; reload before recording another step');}
    return reply(path,body);
  });
  render(<RehearsalWorkspace/>);await screen.findByText('Now: Actor, map and simulation');enterStageNotes();
  fireEvent.change(screen.getByLabelText('Rehearsal closing notes'),{target:{value:'Closing note for the previous run version'}});
  fireEvent.click(screen.getByRole('button',{name:'Record stage covered'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('Rehearsal changed');
  expect(screen.queryByText('Stage recorded with its evidence.')).not.toBeInTheDocument();
  expect(screen.getByLabelText('Current stage notes')).toHaveValue('');
  expect(screen.getByLabelText('Rehearsal closing notes')).toHaveValue('');
  expect(screen.getByRole('button',{name:'Record stage covered'})).toBeDisabled();
  enterStageNotes('Reviewed the current evidence and measured model');fireEvent.click(screen.getByRole('button',{name:'Record stage covered'}));
  await screen.findByText('Now: Simulated disruption');
  expect(api).toHaveBeenLastCalledWith('/rehearsal');
  expect(vi.mocked(api).mock.calls.filter(([path])=>path.endsWith('/checkpoint'))[1][1]).toMatchObject({expected_version:2,stage_id:'evidence_science'});
});

it('clears a typed stage draft when polling discovers another client advanced the run',async()=>{
  vi.useFakeTimers();state.active=run();render(<RehearsalWorkspace/>);
  await act(async()=>{});enterStageNotes('This note belongs only to the overview');
  state.active=run({version:2,next_stage_id:'evidence_science',milestones:[{stage_id:'overview',outcome:'covered',notes:'Another presenter recorded it',recorded_at:'2026-10-28T12:01:30Z',elapsed_seconds:80}]});
  await act(async()=>{vi.advanceTimersByTime(15000);});
  expect(screen.getByText('Now: Sources and measured science')).toBeInTheDocument();
  expect(screen.getByLabelText('Current stage notes')).toHaveValue('');
});

it('prevents duplicate writes and locks the submitted note while a checkpoint is pending',async()=>{
  state.active=run();let resolve!:(value:any)=>void;const pending=new Promise(res=>{resolve=res;});
  vi.mocked(api).mockImplementation(async(path,body:any)=>path.endsWith('/checkpoint')?pending:reply(path,body));
  render(<RehearsalWorkspace/>);await screen.findByText('Now: Actor, map and simulation');enterStageNotes();
  const record=screen.getByRole('button',{name:'Record stage covered'});
  act(()=>{fireEvent.click(record);fireEvent.click(record);});
  expect(vi.mocked(api).mock.calls.filter(([path])=>path.endsWith('/checkpoint'))).toHaveLength(1);
  expect(screen.getByLabelText('Current stage notes')).toBeDisabled();
  const response=reply('/rehearsal/run-one/checkpoint',{stage_id:'overview',outcome:'covered',notes:'Explained the current stage evidence'});
  await act(async()=>resolve(response));
  expect(await screen.findByText('Stage recorded with its evidence.')).toBeInTheDocument();
});

it('shows the completed export immediately, and reloads the saved immutable record from history',async()=>{
  state.active=completedRun({status:'active',next_stage_id:null});
  const view=render(<RehearsalWorkspace/>);await screen.findByLabelText('Rehearsal closing notes');
  fireEvent.change(screen.getByLabelText('Rehearsal closing notes'),{target:{value:'Improve transitions before the team presentation'}});
  fireEvent.click(screen.getByRole('button',{name:'Finish and save rehearsal'}));
  const download=await screen.findByRole('link',{name:'Download rehearsal evidence JSON'});
  expect(download).toHaveAttribute('href','/api/rehearsal/run-one/export');
  expect(screen.queryByLabelText('Rehearsal presenter')).not.toBeInTheDocument();
  view.unmount();render(<RehearsalWorkspace/>);await screen.findByLabelText('Saved rehearsal');
  fireEvent.change(screen.getByLabelText('Saved rehearsal'),{target:{value:'run-one'}});
  fireEvent.click(screen.getByRole('button',{name:'Open saved rehearsal'}));
  expect(await screen.findByRole('link',{name:'Download rehearsal evidence JSON'})).toHaveAttribute('href','/api/rehearsal/run-one/export');
});

it('can abort an incomplete run only with a reason and preserves its export',async()=>{
  state.active=run();render(<RehearsalWorkspace/>);await screen.findByLabelText('Rehearsal closing notes');
  expect(screen.getByRole('button',{name:'Abort and save record'})).toBeDisabled();
  fireEvent.change(screen.getByLabelText('Rehearsal closing notes'),{target:{value:'Pause practice to resolve the presentation outline'}});
  fireEvent.click(screen.getByRole('button',{name:'Abort and save record'}));
  expect(await screen.findByRole('link',{name:'Download rehearsal evidence JSON'})).toBeInTheDocument();
  expect(api).toHaveBeenCalledWith('/rehearsal/run-one/finish',{expected_version:1,outcome:'aborted',notes:'Pause practice to resolve the presentation outline'});
});

it('rejects a wrong-record history response instead of presenting its download link',async()=>{
  state.runs=[completedRun()];vi.mocked(api).mockImplementation(async(path,body:any)=>path==='/rehearsal/run-one'?completedRun({id:'wrong-record'}):reply(path,body));
  render(<RehearsalWorkspace/>);await screen.findByLabelText('Saved rehearsal');
  fireEvent.change(screen.getByLabelText('Saved rehearsal'),{target:{value:'run-one'}});fireEvent.click(screen.getByRole('button',{name:'Open saved rehearsal'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('does not match the selected record');
  expect(screen.queryByRole('link',{name:'Download rehearsal evidence JSON'})).not.toBeInTheDocument();
});

it('clears actionable state after a polling failure rather than keeping an old active run',async()=>{
  vi.useFakeTimers();state.active=run();render(<RehearsalWorkspace/>);await act(async()=>{});
  expect(screen.getByRole('button',{name:'Record stage covered'})).toBeInTheDocument();
  vi.mocked(api).mockRejectedValue(new Error('Rehearsal server unavailable'));
  await act(async()=>{vi.advanceTimersByTime(15000);});
  expect(screen.getByRole('alert')).toHaveTextContent('Rehearsal server unavailable');
  expect(screen.queryByRole('button',{name:'Record stage covered'})).not.toBeInTheDocument();
});
