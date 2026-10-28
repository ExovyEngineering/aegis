import { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowDownToLine, Check, Clipboard, Clock3, Play, RefreshCw, ShieldCheck, TriangleAlert } from 'lucide-react';
import { api } from './api';
import type { RuntimeContext } from './types';

interface Stage {id:string;title:string;planned_seconds:number;description:string;requires_evidence?:string[]}
interface Milestone {stage_id:string;outcome:'covered'|'skipped';notes:string;recorded_at:string;elapsed_seconds:number}
interface Run {id:string;version:number;status:'active'|'completed'|'aborted';presenter:string;purpose:string;run_kind:'practice'|'automated_check';started_at:string;finished_at?:string;elapsed_seconds:number;server_time:string;milestones:Milestone[];next_stage_id?:string;notes?:string}
type RunSummary = Pick<Run,'id'|'version'|'status'|'presenter'|'purpose'|'run_kind'|'started_at'|'finished_at'|'elapsed_seconds'>;
interface Snapshot {runtime:RuntimeContext;stages:Stage[];active:Run|null;runs:RunSummary[]}
type Destination = 'command'|'evidence'|'science'|'drive';
const clock = (seconds:number) => `${Math.floor(Math.max(0,seconds)/60).toString().padStart(2,'0')}:${Math.floor(Math.max(0,seconds)%60).toString().padStart(2,'0')}`;
const finiteSeconds = (value:unknown):value is number => typeof value==='number'&&Number.isFinite(value)&&value>=0;
function validRun(value:unknown):value is Run {
  if(!value||typeof value!=='object')return false;
  const run=value as Partial<Run>;
  return typeof run.id==='string'&&run.id.length>0&&typeof run.version==='number'&&Number.isInteger(run.version)&&run.version>=1
    &&['active','completed','aborted'].includes(run.status??'')&&typeof run.presenter==='string'&&typeof run.purpose==='string'
    &&['practice','automated_check'].includes(run.run_kind??'')&&typeof run.started_at==='string'&&typeof run.server_time==='string'
    &&finiteSeconds(run.elapsed_seconds)&&Array.isArray(run.milestones)&&run.milestones.every(mark=>mark&&typeof mark.stage_id==='string'
      &&['covered','skipped'].includes(mark.outcome)&&typeof mark.notes==='string'&&finiteSeconds(mark.elapsed_seconds));
}

export default function RehearsalWorkspace({onNavigate}:{onNavigate?:(view:Destination)=>void}) {
  const [snapshot,setSnapshot]=useState<Snapshot>();
  const [error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false);
  const [presenter,setPresenter]=useState(''),[purpose,setPurpose]=useState('');
  const [kind,setKind]=useState<'practice'|'automated_check'>('practice');
  const [stageNotes,setStageNotes]=useState(''),[finishNotes,setFinishNotes]=useState('');
  const [historyId,setHistoryId]=useState(''),[viewed,setViewed]=useState<Run>();
  const [now,setNow]=useState(performance.now()),[receivedAt,setReceivedAt]=useState(performance.now());
  const epoch=useRef(0),mutation=useRef(false);
  const load=useCallback(async()=>{
    const request=++epoch.current;
    try {
      const result=await api<Snapshot>('/rehearsal');
      if(request!==epoch.current)return;
      if(!result?.runtime || !['operator','isolated_rehearsal','misconfigured'].includes(result.runtime.mode)
        ||typeof result.runtime.isolated!=='boolean'||typeof result.runtime.offline!=='boolean'
        ||!Array.isArray(result.stages)||!result.stages.every(stage=>stage&&typeof stage.id==='string'&&typeof stage.title==='string'&&finiteSeconds(stage.planned_seconds))
        ||!Array.isArray(result.runs)||!result.runs.every(item=>item&&typeof item.id==='string'&&typeof item.presenter==='string'&&typeof item.started_at==='string')
        ||(result.active!==null&&(!validRun(result.active)||result.active.status!=='active')))throw new Error('Rehearsal context is unavailable. Refresh before recording anything.');
      setSnapshot(result);setReceivedAt(performance.now());setError('');
    } catch(e) {if(request===epoch.current){setSnapshot(undefined);setViewed(undefined);setError(e instanceof Error?e.message:String(e));}throw e;}
  },[]);
  useEffect(()=>{load().catch(()=>{});const poll=window.setInterval(()=>load().catch(()=>{}),15000);const timer=window.setInterval(()=>setNow(performance.now()),1000);return()=>{epoch.current++;window.clearInterval(poll);window.clearInterval(timer);};},[load]);
  const runtime=snapshot?.runtime;
  const isolated=runtime?.mode==='isolated_rehearsal' && runtime.isolated;
  const run=viewed??snapshot?.active;
  const elapsed=run?run.elapsed_seconds+(run.status==='active'?Math.max(0,now-receivedAt)/1000:0):0;
  const next=run?.status==='active'?snapshot?.stages.find(s=>s.id===(run.next_stage_id??snapshot.stages[run.milestones.length]?.id)):undefined;
  useEffect(()=>{setStageNotes('');setFinishNotes('');},[snapshot?.active?.id,snapshot?.active?.version,snapshot?.active?.next_stage_id]);
  const finished=snapshot?.runs.filter(item=>item.status!=='active')??[];
  const stageLinks:Record<string,Destination[]>={overview:['command'],evidence_science:['evidence','science'],disruption:['command'],approval:['command'],driver:['drive'],closing:[]};
  async function act(path:string,body:unknown,message:string) {
    if(mutation.current)return;mutation.current=true;setBusy(true);setError('');setNotice('');
    let recorded=false;
    try {const result=await api<Run>(path,body);if(!validRun(result)||(path!=='/rehearsal/start'&&result.id!==path.split('/')[2]))throw new Error('The rehearsal action returned an incomplete or different record. Refresh before recording another action.');recorded=true;await load();setViewed(result.status==='active'?undefined:result);setStageNotes('');setFinishNotes('');setNotice(message);}
    catch(e){await load().catch(()=>{});setStageNotes('');setFinishNotes('');setError(`${recorded?'The action was recorded, but its current state could not be refreshed. Retry rehearsal context before recording another action. ':''}${e instanceof Error?e.message:String(e)}`);}
    finally{mutation.current=false;setBusy(false);}
  }
  async function openHistory() {
    if(!historyId||mutation.current)return;mutation.current=true;setBusy(true);setError('');
    try{const result=await api<Run>(`/rehearsal/${historyId}`);if(!validRun(result)||result.id!==historyId)throw new Error('The saved rehearsal response does not match the selected record. Refresh before reviewing it.');if(result.status==='active')throw new Error('That rehearsal is still active. Return to its current timer.');setViewed(result);}
    catch(e){setViewed(undefined);setError(e instanceof Error?e.message:String(e));}finally{mutation.current=false;setBusy(false);}
  }
  const command='.venv/Scripts/python scripts/start_rehearsal.py --port 8001';
  async function copyCommand() {
    try {await navigator.clipboard.writeText(command);setNotice('Launch command copied. Run it in a separate terminal; it prints the isolated workspace URL.');}
    catch{setError('Clipboard access was unavailable. Select and copy the displayed command manually.');}
  }
  return <section className="panel rehearsal-workspace" aria-label="Guided presentation rehearsal">
    <div className="panel-heading"><div><h2>Practice the five-minute story</h2><span>Six guided stages, a measured timer and a retained evidence record</span></div><Clock3 size={23}/></div>
    <div className="padded">
      {error&&<p role="alert" className="feedback error"><TriangleAlert size={17}/>{error}</p>}
      {notice&&<p role="status" className="feedback success">{notice}</p>}
      {!snapshot&&<button className="secondary" disabled={busy} onClick={()=>load().catch(()=>{})}><RefreshCw size={15}/>Retry rehearsal context</button>}
      {runtime&&!isolated&&<div className="rehearsal-launch"><h3>{runtime.mode==='misconfigured'?'Rehearsal configuration needs correction':'Open a separate practice workspace'}</h3><p>{runtime.warning} This page alone does not isolate the server. Rehearsal recording is unavailable in the operator workspace.</p><p>From the project folder, run this in a separate terminal. The launcher chooses a new database, refuses port 8000 and prints its verified URL. Keep that terminal running during practice.</p><pre><code>{command}</code></pre><button className="secondary" onClick={copyCommand}><Clipboard size={15}/>Copy rehearsal launch command</button><p className="source-note">The default rehearsal uses dated evidence fixtures and estimated route fallbacks. Base-map tiles may still need internet. It does not refresh shared public-source caches.</p></div>}
      {isolated&&snapshot&&<>
        <div className="coverage-warning"><ShieldCheck size={17}/><span><strong>Verified isolated rehearsal</strong> · {runtime.rehearsal_id?.slice(0,8)} · {runtime.offline?'Dated fixtures; provider requests disabled':'Network-enabled rehearsal; source freshness remains separate'}. Operational changes stay in this rehearsal database.</span></div>
        {!snapshot.active&&!viewed&&<div className="rehearsal-start"><label className="field">Rehearsal presenter<input disabled={busy} value={presenter} maxLength={100} onChange={e=>setPresenter(e.target.value)} placeholder="Presenter or team name"/></label><label className="field">Rehearsal purpose<textarea disabled={busy} value={purpose} maxLength={1000} onChange={e=>setPurpose(e.target.value)} placeholder="What the team wants to practice" rows={2}/></label><label className="field">Rehearsal record type<select aria-label="Rehearsal record type" disabled={busy} value={kind} onChange={e=>setKind(e.target.value as typeof kind)}><option value="practice">Self-reported team practice</option><option value="automated_check">Automated workflow check</option></select></label><button disabled={busy||presenter.trim().length<2||purpose.trim().length<5} onClick={()=>act('/rehearsal/start',{presenter,purpose,run_kind:kind},'Rehearsal timer started. Practice actions remain isolated.')}><Play size={16}/>Start rehearsal timer</button><p className="source-note">Starting the timer does not reset the scenario. Reset deliberately in Command if desired. Use the same workspace for all six stages.</p></div>}
        {run&&<>
          <div className="rehearsal-timer"><div><span>{run.status==='active'?'SERVER-BASED ELAPSED TIME':'RECORDED ELAPSED TIME'}</span><strong aria-label="Rehearsal elapsed time">{clock(elapsed)}</strong></div><div><strong>{run.status==='active'?(elapsed>300?`${clock(elapsed-300)} over target`:`${clock(300-elapsed)} to target`):run.status}</strong><p>Planned budget 05:00 · {run.run_kind==='automated_check'?'Automated check':'Self-reported practice'}</p><small>{run.presenter} · {run.purpose}</small></div></div>
          <p className="source-note">The server stores elapsed wall-clock time and operation evidence. This is not proof of presentation quality, human attendance, Kiro execution or author approval. Navigating between views keeps the timer running.</p>
          <ol className="rehearsal-stages">{snapshot.stages.map((stage,index)=>{const mark=run.milestones.find(m=>m.stage_id===stage.id);return <li key={stage.id} className={mark?'recorded':next?.id===stage.id?'current':''}><span className="rehearsal-stage-number">{mark?<Check size={15}/>:index+1}</span><div><strong>{stage.title}</strong><span className="source-stamp">{clock(stage.planned_seconds)} planned{mark?` · ${mark.outcome} at ${clock(mark.elapsed_seconds)}`:''}</span><p>{stage.description}</p>{mark&&<p className="source-note">Recorded note: {mark.notes}</p>}</div></li>;})}</ol>
          {next&&<div className="rehearsal-checkpoint"><h3>Now: {next.title}</h3><p>Perform the stage in this workspace, then return here to record it. Operational stages require matching actions in this run's audit history; a note cannot substitute for those actions.</p>{onNavigate&&<div className="planning-actions">{stageLinks[next.id]?.map(view=><button key={view} className="secondary" onClick={()=>onNavigate(view)}>Open {view==='command'?'Command':view==='evidence'?'Sources & evidence':view==='science'?'Model evaluation':'AEGIS Drive'}</button>)}</div>}<label className="field">Current stage notes<textarea rows={2} maxLength={2000} disabled={busy} value={stageNotes} onChange={e=>setStageNotes(e.target.value)} placeholder="What was covered, or why this stage was skipped"/></label><div className="planning-actions"><button disabled={busy||stageNotes.trim().length<5} onClick={()=>act(`/rehearsal/${run.id}/checkpoint`,{expected_version:run.version,stage_id:next.id,outcome:'covered',notes:stageNotes},'Stage recorded with its evidence.')}><Check size={15}/>Record stage covered</button><button className="secondary" disabled={busy||stageNotes.trim().length<5} onClick={()=>act(`/rehearsal/${run.id}/checkpoint`,{expected_version:run.version,stage_id:next.id,outcome:'skipped',notes:stageNotes},'Stage recorded as skipped, with its reason.')}>Record stage skipped</button></div></div>}
          {run.status==='active'&&<div className="rehearsal-finish"><label className="field">Rehearsal closing notes<textarea rows={2} maxLength={2000} disabled={busy} value={finishNotes} onChange={e=>setFinishNotes(e.target.value)} placeholder="What to improve before the team presents"/></label><div className="planning-actions"><button disabled={busy||!!next||finishNotes.trim().length<5} onClick={()=>act(`/rehearsal/${run.id}/finish`,{expected_version:run.version,outcome:'completed',notes:finishNotes},'Completed rehearsal saved. Duration and skipped stages remain explicit.')}>Finish and save rehearsal</button><button className="secondary" disabled={busy||finishNotes.trim().length<5} onClick={()=>act(`/rehearsal/${run.id}/finish`,{expected_version:run.version,outcome:'aborted',notes:finishNotes},'Rehearsal aborted; its existing record was retained.')}>Abort and save record</button></div></div>}
          {run.status!=='active'&&<div className="planning-actions"><a className="button-link secondary" href={`/api/rehearsal/${run.id}/export`} download><ArrowDownToLine size={15}/>Download rehearsal evidence JSON</a><button className="secondary" onClick={()=>{setViewed(undefined);setNotice('');}}>Return to current rehearsal</button></div>}
        </>}
        {finished.length>0&&<div className="rehearsal-history"><label className="field">Saved rehearsal<select aria-label="Saved rehearsal" disabled={busy} value={historyId} onChange={e=>setHistoryId(e.target.value)}><option value="">Choose a saved record</option>{finished.map(item=><option key={item.id} value={item.id}>{item.presenter} · {item.status} · {new Date(item.started_at).toLocaleString('en-US',{timeZone:'America/Chicago'})} CT</option>)}</select></label><button className="secondary" disabled={busy||!historyId} onClick={openHistory}>Open saved rehearsal</button></div>}
        <p className="source-note">State path: {runtime.database_relative_path}. A completed record is retained as a snapshot; later scenario resets or refreshed reports do not rewrite its exported evidence.</p>
      </>}
    </div>
  </section>;
}
