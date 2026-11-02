import { ArrowRight, CheckCircle2 } from 'lucide-react';
import './JourneySteps.css';

export interface JourneyStep {
  id: string;
  title: string;
  detail: string;
  state: 'complete' | 'current' | 'waiting';
  actionLabel: string;
  onAction: () => void;
  disabled?: boolean;
}

/** Navigation and existing-control shortcuts; it never performs an implicit action. */
export default function JourneySteps({ title, summary, steps }: { title: string; summary: string; steps: JourneyStep[] }) {
  return <section className="journey-steps" aria-label={title}>
    <div className="journey-heading"><div className="eyebrow">YOUR NEXT STEPS</div><h2>{title}</h2><p>{summary}</p></div>
    <ol>{steps.map((step, index) => <li key={step.id} className={`journey-step ${step.state}`} aria-current={step.state === 'current' ? 'step' : undefined}>
      <span className="journey-number" aria-hidden="true">{step.state === 'complete' ? <CheckCircle2 size={19} /> : index + 1}</span>
      <div><h3>{step.title}</h3><p>{step.detail}</p><button type="button" className="text-button" disabled={step.disabled} onClick={step.onAction}>{step.actionLabel}<ArrowRight size={13} /></button></div>
    </li>)}</ol>
  </section>;
}

export function focusJourneyControl(id: string) {
  const target = document.getElementById(id);
  target?.scrollIntoView?.({ behavior: 'auto', block: 'center' });
  target?.focus({ preventScroll: true });
}
