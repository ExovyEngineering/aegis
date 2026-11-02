import { ShieldCheck, TriangleAlert } from 'lucide-react';
import type { RuntimeContext } from './types';
export default function RuntimeBanner({runtime,requestedRehearsal=false}:{runtime?:RuntimeContext;requestedRehearsal?:boolean}) {
  if(runtime?.mode==='isolated_rehearsal'&&runtime.isolated)return <aside className="runtime-banner" aria-label="Isolated rehearsal runtime"><ShieldCheck size={20}/><div><strong>ISOLATED REHEARSAL · {runtime.rehearsal_id?.slice(0,8)}</strong><span>{runtime.offline?'Dated source fixtures · provider requests disabled · estimated routing available':'Separate simulated state · source freshness remains separate'} · Not the operator database</span></div><a href="/?mode=rehearsal">Timer and guided stages</a></aside>;
  if(runtime?.mode==='misconfigured'||requestedRehearsal)return <aside className="runtime-banner runtime-warning" aria-label="Unverified rehearsal runtime"><TriangleAlert size={20}/><div><strong>THIS SERVER IS NOT A VERIFIED ISOLATED REHEARSAL</strong><span>{runtime?.warning??'Use the rehearsal launcher in a separate terminal. A URL parameter alone does not isolate operational state.'}</span></div></aside>;
  return null;
}
