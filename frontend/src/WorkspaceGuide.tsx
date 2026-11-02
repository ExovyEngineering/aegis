import { ArrowRight, Compass } from 'lucide-react';
import './WorkspaceGuide.css';

export type WorkspaceView = 'command' | 'routes' | 'roads' | 'dispatch' | 'evidence' | 'science' | 'assistant' | 'brief' | 'drive' | 'freshness';
interface Guide {
  title: string;
  summary: string;
  scope: string;
  details: string[];
  next: { view: WorkspaceView; label: string }[];
}

const guides: Record<WorkspaceView, Guide> = {
  freshness: {
    title: 'Give an at-risk load a reviewed second route',
    summary: 'Replay a sensor excursion, watch the estimated quality budget change, and compare closer receiving options and FEFO picks.',
    scope: 'Simulated logistics · uncalibrated quality projection · explicit approval',
    details: [
      'Replay creates stored sensor frames in a separate experiment. Temperature consumes a declared quality budget; humidity, vibration and ethylene remain contextual channels.',
      'A modeled shortfall automatically calculates closer receiving options. Preparing a plan changes no assignments; approval publishes the complete independently checked simulated plan.',
      'FEFO and FIFO use identical demand and safety constraints. The quality model cannot clear pathogen safety, extend a use-by cap, or establish real buyer acceptance.',
    ],
    next: [{view:'command',label:'Review current distribution'},{view:'drive',label:'See approved driver work'}],
  },
  command: {
    title: 'Find delivery problems before choosing a response',
    summary: 'Start with the delivery outlook. Test a delay, inspect the affected trips, then compare and review a response plan.',
    scope: 'Changes simulation only after explicit apply or approval',
    details: [
      'The outlook is a read-only planning estimate over this simulated delivery wave. Chosen delay, ambient and fault assumptions do not apply an event or publish a plan.',
      'A route request draws a travel comparison for the selected shipment. It does not change a truck assignment or automatically avoid a closure.',
      'Applying a simulation event changes the current network and clears approved assignments. Compare the refreshed plans before proposing a new response.',
      'A proposal is a plan awaiting review. Only a separate human approval publishes simulated driver assignments; held and recalled lots remain excluded.',
    ],
    next: [{ view: 'routes', label: 'Design farm or fleet routes' }, { view: 'dispatch', label: 'Review approved work' }],
  },
  routes: {
    title: 'Experiment with a route design',
    summary: 'Build an independent farm or multi-location plan to see which trucks serve which stops and how the journey changes.',
    scope: 'Planning workspace · does not dispatch',
    details: [
      'Run the plan to compute truck allocation, stop order, travel estimates and unserved demand. After editing inputs, run it again to produce a new result.',
      'Capacity and route-time limits can change which stops are served. Delay can consume a stop deadline; ambient temperature and refrigeration settings affect the illustrative cargo projection, not road geometry.',
      'These experiments and saved runs do not replace Command center shipments or approved driver assignments. Return to Command to review the operational response separately.',
    ],
    next: [{ view: 'roads', label: 'Inspect road evidence' }, { view: 'command', label: 'Return to current operation' }],
  },
  roads: {
    title: 'Inspect routes alongside road evidence',
    summary: 'Compare travel alternatives with separately attributed Missouri and Iowa incidents near each route.',
    scope: 'Evidence and comparison · does not dispatch',
    details: [
      'Adding an incident layer shows evidence beside a route. It does not feed closures into OSRM or automatically redesign the journey.',
      'A nearby event prompts review; it may be on a parallel road or outside the trip time. Check source age, geometry and the actual event details.',
      'OSRM supplies ordinary-driving alternatives where available; estimates stay labeled. Neither method establishes commercial-truck eligibility or verified closure avoidance.',
    ],
    next: [{ view: 'routes', label: 'Test a planning design' }, { view: 'command', label: 'Review operational responses' }],
  },
  dispatch: {
    title: 'Turn review into a recorded decision',
    summary: 'Review driver reports, lot holds, verification and instructions for already approved simulated assignments.',
    scope: 'Human decisions · recorded in the audit trail',
    details: [
      'Use an explicit decision form with a reviewer and reason to change a hold, review a report or send an instruction. Reading the desk alone changes no assignments.',
      'A hold removes affected assignments. Releasing it does not recreate them; review and approve a fresh plan in Command.',
      'A driver acknowledgment, targeted verification and dispatch readiness are different records. An instruction does not itself compute or approve a replacement route.',
    ],
    next: [{ view: 'command', label: 'Compare a fresh response plan' }, { view: 'drive', label: 'View the driver handoff' }],
  },
  evidence: {
    title: 'Check what the sources actually provide',
    summary: 'Inspect public evidence, supplied datasets, retrieval times and gaps before using them to support a decision.',
    scope: 'Source evidence · does not change routing',
    details: [
      'A source refresh requests new evidence and reports failure or a dated fallback. It does not silently change a shipment, impose a hold or redraw a route.',
      'Historical observations, forecasts, public warnings and simulated cargo temperatures mean different things. A successful web request does not prove complete data coverage.',
      'CDC human surveillance and outbreaks remain separate from FSIS sampling outcomes. A recall notice is not a verified match to a fictional lot.',
    ],
    next: [{ view: 'science', label: 'Understand measured model results' }, { view: 'command', label: 'Review the current operation' }],
  },
  science: {
    title: 'Read the measured scientific result',
    summary: 'See saved historical model and baseline evaluations, their uncertainty and what the data can support.',
    scope: 'Read-only evaluation · no live shipment risk score',
    details: [
      'Opening this page does not train a model, calculate a new shipment forecast or alter dispatch eligibility.',
      'The measured target is positivity in selected FSIS poultry samples, not consumer illness probability. The saved historical prevalence baseline remains the operational choice where the fitted comparison did not establish improvement.',
      'Use the uncertainty, chronological holdout and feature-availability checks when presenting the result; software test counts are separate from predictive skill.',
    ],
    next: [{ view: 'evidence', label: 'Inspect data coverage' }, { view: 'assistant', label: 'Explain the saved evidence' }],
  },
  assistant: {
    title: 'Ask for an explanation of captured evidence',
    summary: 'Type a word like chicken, describe a delivery problem, or click a question for a cited explanation.',
    scope: 'Read-only explanation · cannot perform an action',
    details: [
      'Guided questions and topic lookup return authored facts from the captured context. The optional model, if configured and explicitly selected, can choose a topic only.',
      'The answer does not approve, dispatch, hold cargo, refresh a source or train a model. Follow its workspace links and use the ordinary explicit forms to make a separate decision.',
      'If the operational state or reports change, reload the evidence context. An exported answer preserves its captured facts rather than updating with the application.',
    ],
    next: [{ view: 'command', label: 'Inspect current responses' }, { view: 'evidence', label: 'Open the source evidence' }],
  },
  brief: {
    title: 'Learn, rehearse and present',
    summary: 'Find the printable handbook, feature status, dated test evidence and guided presentation stages.',
    scope: 'Documentation and rehearsal · check the runtime banner',
    details: [
      'Downloads describe a dated build. Recorded software checks do not prove current provider uptime, model accuracy or a completed human presentation.',
      'The guided timer records rehearsal evidence only on a verified isolated rehearsal server. A rehearsal URL alone does not protect the operator database.',
      'Use the handbook for full walkthroughs, then practice the connected evidence, response, approval and parked-driver workflow.',
    ],
    next: [{ view: 'command', label: 'Begin the operational walkthrough' }, { view: 'evidence', label: 'Inspect source provenance' }],
  },
  drive: {
    title: 'Follow the approved simulated trip',
    summary: 'See the assigned destination, simulated cargo and fuel, advisories and dispatcher-approved instructions.',
    scope: 'Parked use · follows approved assignments',
    details: [
      'Start safely parked and confirm parked use before acknowledging or reporting. The app does not detect actual motion, GPS or physical sensors.',
      'Reports reach the dispatcher for review. They do not automatically reroute the truck or hold a lot.',
      'If no trip is assigned, return to Command to propose and approve a feasible simulated plan. Separate verification and acknowledgment requirements can still remain.',
    ],
    next: [{ view: 'dispatch', label: 'Open dispatcher review' }, { view: 'command', label: 'Review assignment plans' }],
  },
};

export default function WorkspaceGuide({ view, onNavigate }: { view: WorkspaceView; onNavigate: (view: WorkspaceView) => void }) {
  const guide = guides[view];
  return <aside className="workspace-guide" aria-label="Workspace guide">
    <div className="workspace-guide-overview">
      <Compass size={21} aria-hidden="true" />
      <div><span className="workspace-guide-kicker">WHAT YOU ARE LOOKING AT</span><h2>{guide.title}</h2><p>{guide.summary}</p></div>
    </div>
    <div className="workspace-guide-footer"><span className="workspace-guide-scope">{guide.scope}</span><div className="workspace-guide-links" aria-label="Connected workspaces">{guide.next.map(next => <button key={next.view} type="button" className="secondary" onClick={() => onNavigate(next.view)}>{next.label}<ArrowRight size={13} aria-hidden="true" /></button>)}</div></div>
    <details key={view} className="workspace-guide-details"><summary>How this connects</summary><ul>{guide.details.map(detail => <li key={detail}>{detail}</li>)}</ul></details>
  </aside>;
}
