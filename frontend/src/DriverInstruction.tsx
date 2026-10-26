import { useState } from 'react';
import { Check, MessageSquare } from 'lucide-react';
import { api } from './api';
import type { Shipment } from './types';

export default function DriverInstruction({ shipment, onAcknowledged }: { shipment: Shipment; onAcknowledged: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  if (!shipment.instruction_revision) return null;
  async function acknowledge() {
    setBusy(true); setError('');
    try { await api(`/driver/${shipment.id}/instruction-ack`, { instruction_revision: shipment.instruction_revision }); await onAcknowledged(); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }
  return <div className="driver-new-instruction"><div><MessageSquare size={16} /><strong>Dispatcher instruction · version {shipment.instruction_revision}</strong></div><p>{shipment.instruction_acknowledged ? 'You acknowledged this instruction version.' : 'Read the dispatcher instruction above while parked, then acknowledge this version.'}</p>{error && <p role="alert">{error}</p>}<button className="secondary" disabled={busy || shipment.instruction_acknowledged} onClick={acknowledge}><Check size={15} />{shipment.instruction_acknowledged ? 'Instruction acknowledged' : 'Acknowledge new instruction'}</button></div>;
}
