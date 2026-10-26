import { Plus, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';

export interface PlanningOrigin { id: string; name: string; kind: 'farm' | 'dc'; coordinates: [number, number]; inventory_kg: number }
export interface PlanningStop { id: string; name: string; coordinates: [number, number]; demand_kg: number; deadline_hours: number; shelf_life_hours: number; lot_id: string; held: boolean; recalled: boolean; eligible: boolean }
export interface PlanningTruck { id: string; origin_id: string; capacity_kg: number; refrigerated: boolean; eligible: boolean }
export interface CustomOperation { name: string; description?: string; origins: PlanningOrigin[]; stops: PlanningStop[]; trucks: PlanningTruck[] }

function readCoordinate(text: string): number {
  return /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(text.trim()) && Number.isFinite(Number(text)) ? Number(text) : Number.NaN;
}
export function CoordinateInput({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) {
  const [draft, setDraft] = useState(String(value));
  useEffect(() => { setDraft(previous => Number.isFinite(value) && readCoordinate(previous) !== value ? String(value) : previous); }, [value]);
  return <input aria-label={label} type="text" inputMode="decimal" value={draft} onChange={e => { setDraft(e.target.value); onChange(readCoordinate(e.target.value)); }} />;
}

export function operationFromPreset(preset: any): CustomOperation {
  return {
    name: `${preset.name ?? 'Custom operation'} — planning copy`,
    origins: (preset.origins ?? []).map((o: any) => ({ id: o.id, name: o.name, kind: o.kind === 'dc' ? 'dc' : 'farm', coordinates: [...o.coordinates], inventory_kg: o.inventory_kg ?? 3000 })),
    stops: (preset.stops ?? []).map((s: any) => ({ id: s.id, name: s.name, coordinates: [...s.coordinates], demand_kg: s.demand_kg ?? 300, deadline_hours: s.deadline_hours ?? 6, shelf_life_hours: s.shelf_life_hours ?? 72, lot_id: s.lot_id ?? `LOT_${s.id}`, held: !!s.held, recalled: !!s.recalled, eligible: s.eligible !== false })),
    trucks: (preset.trucks ?? []).map((t: any) => ({ id: t.id, origin_id: t.origin_id, capacity_kg: t.capacity_kg ?? 1500, refrigerated: t.refrigerated !== false, eligible: t.eligible !== false })),
  };
}
export function newPlanningOperation(): CustomOperation {
  return { name: 'My planning exercise', origins: [{ id: 'FARM1', name: 'Planning origin', kind: 'farm', coordinates: [-92.4, 39], inventory_kg: 3000 }], stops: [{ id: 'STOP1', name: 'Planning delivery', coordinates: [-92.33, 38.95], demand_kg: 300, deadline_hours: 6, shelf_life_hours: 72, lot_id: 'LOT1', held: false, recalled: false, eligible: true }], trucks: [{ id: 'TRUCK1', origin_id: 'FARM1', capacity_kg: 1500, refrigerated: true, eligible: true }] };
}
export function customOperationErrors(operation: CustomOperation): string[] {
  const errors: string[] = [];
  const ids = [...operation.origins, ...operation.stops, ...operation.trucks].map(x => x.id);
  if (new Set(ids).size !== ids.length) errors.push('Location and truck IDs must be unique.');
  if (ids.some(id => !/^[A-Za-z][A-Za-z0-9_-]{0,31}$/.test(id))) errors.push('IDs must start with a letter and use letters, numbers, underscores or hyphens (32 characters maximum).');
  if (!operation.name.trim()) errors.push('Give this planning exercise a name.');
  if (!operation.origins.length || !operation.stops.length || !operation.trucks.length) errors.push('Keep at least one origin, delivery stop and truck.');
  if (operation.origins.length > 3 || operation.stops.length > 20 || operation.trucks.length > 10) errors.push('Use up to 3 origins, 20 stops and 10 trucks.');
  for (const n of [...operation.origins, ...operation.stops]) {
    if (!n.name.trim()) errors.push(`${n.id}: add a location name.`);
    if (!Number.isFinite(n.coordinates[0]) || n.coordinates[0] < -180 || n.coordinates[0] > 180 || !Number.isFinite(n.coordinates[1]) || n.coordinates[1] < -90 || n.coordinates[1] > 90) errors.push(`${n.id}: enter valid longitude and latitude.`);
  }
  if (operation.origins.some(o => !Number.isInteger(o.inventory_kg) || o.inventory_kg < 0 || o.inventory_kg > 1000000)) errors.push('Origin stock must be a whole number from 0 to 1,000,000 kg.');
  if (operation.stops.some(s => !Number.isInteger(s.demand_kg) || s.demand_kg < 1 || s.demand_kg > 5000 || !Number.isFinite(s.deadline_hours) || s.deadline_hours <= 0 || s.deadline_hours > 16 || !Number.isFinite(s.shelf_life_hours) || s.shelf_life_hours <= 0 || s.shelf_life_hours > 168)) errors.push('Stops require 1–5,000 kg, a deadline up to 16 hours, and remaining shelf life up to 168 hours.');
  if (new Set(operation.stops.map(s => s.lot_id)).size !== operation.stops.length || operation.stops.some(s => !s.lot_id.trim())) errors.push('Use one distinct planning lot ID per delivery stop.');
  if (operation.trucks.some(t => !operation.origins.some(o => o.id === t.origin_id) || !Number.isInteger(t.capacity_kg) || t.capacity_kg < 100 || t.capacity_kg > 5000)) errors.push('Each truck needs an existing origin and 100–5,000 kg capacity.');
  return errors;
}

export default function CustomOperationEditor({ value, onChange, templates }: { value: CustomOperation; onChange: (operation: CustomOperation) => void; templates: any[] }) {
  const updateOrigin = (index: number, update: Partial<PlanningOrigin>) => {
    const previous = value.origins[index].id;
    onChange({ ...value, origins: value.origins.map((o, i) => i === index ? { ...o, ...update } : o), trucks: update.id ? value.trucks.map(t => t.origin_id === previous ? { ...t, origin_id: update.id! } : t) : value.trucks });
  };
  const updateStop = (index: number, update: Partial<PlanningStop>) => onChange({ ...value, stops: value.stops.map((s, i) => i === index ? { ...s, ...update } : s) });
  const updateTruck = (index: number, update: Partial<PlanningTruck>) => onChange({ ...value, trucks: value.trucks.map((t, i) => i === index ? { ...t, ...update } : t) });
  const nextId = (prefix: string) => { const used = new Set([...value.origins, ...value.stops, ...value.trucks].map(x => x.id)); let i = 1; while (used.has(`${prefix}${i}`)) i++; return `${prefix}${i}`; };
  const errors = customOperationErrors(value);
  return <section className="panel custom-operation-editor" aria-label="Custom operation editor">
    <div className="panel-heading"><div><div className="eyebrow">YOUR PLANNING INPUTS</div><h2>Build your operation</h2><span>Locations you enter remain a planning exercise; relationships and cargo are not verified.</span></div><span className="pill amber">NO AUTOMATIC DISPATCH</span></div>
    <div className="editor-body"><label className="field">Planning exercise name<input maxLength={120} value={value.name} onChange={e => onChange({ ...value, name: e.target.value })} /></label>
      <div className="editor-templates"><span>Start with a simulated layout:</span>{templates.map(t => <button className="secondary small" key={t.id} onClick={() => onChange(operationFromPreset(t))}>Copy {t.name}</button>)}</div>
      <p className="source-note">Coordinate order is longitude, then latitude. Use your own locations or edit a copied simulation. No geocoding, customer verification or live dispatch occurs.</p>
    </div>
    <div className="editor-section-heading"><h3>Dispatch origins <small>{value.origins.length}/3</small></h3><button className="secondary small" disabled={value.origins.length >= 3} onClick={() => onChange({ ...value, origins: [...value.origins, { id: nextId('ORIGIN'), name: 'Planning origin', kind: 'farm', coordinates: [-92.4, 39], inventory_kg: 3000 }] })}><Plus size={13} /> Add origin</button></div>
    <div className="table-scroll"><table className="editable-table"><thead><tr><th>ID / name</th><th>Type</th><th>Longitude</th><th>Latitude</th><th>Available stock kg</th><th /></tr></thead><tbody>{value.origins.map((o, i) => <tr key={i}><td><input aria-label={`Origin ${i + 1} ID`} value={o.id} onChange={e => updateOrigin(i, { id: e.target.value })} /><input aria-label={`Origin ${i + 1} name`} value={o.name} onChange={e => updateOrigin(i, { name: e.target.value })} /></td><td><select aria-label={`Origin ${i + 1} type`} value={o.kind} onChange={e => updateOrigin(i, { kind: e.target.value as 'farm' | 'dc' })}><option value="farm">Farm</option><option value="dc">Distribution center</option></select></td><td><CoordinateInput label={`Origin ${i + 1} longitude`} value={o.coordinates[0]} onChange={value => updateOrigin(i, { coordinates: [value, o.coordinates[1]] })} /></td><td><CoordinateInput label={`Origin ${i + 1} latitude`} value={o.coordinates[1]} onChange={value => updateOrigin(i, { coordinates: [o.coordinates[0], value] })} /></td><td><input aria-label={`Origin ${i + 1} stock kg`} type="number" min={0} max={1000000} value={o.inventory_kg} onChange={e => updateOrigin(i, { inventory_kg: Number(e.target.value) })} /></td><td><button className="icon-button" aria-label={`Remove origin ${i + 1}`} disabled={value.origins.length <= 1} onClick={() => { const origins = value.origins.filter((_, j) => j !== i); onChange({ ...value, origins, trucks: value.trucks.map(t => t.origin_id === o.id ? { ...t, origin_id: origins[0].id } : t) }); }}><Trash2 size={15} /></button></td></tr>)}</tbody></table></div>
    <div className="editor-section-heading"><h3>Delivery stops <small>{value.stops.length}/20</small></h3><button className="secondary small" disabled={value.stops.length >= 20} onClick={() => { const id = nextId('STOP'); onChange({ ...value, stops: [...value.stops, { id, name: 'Planning delivery', coordinates: [...value.origins[0].coordinates], demand_kg: 300, deadline_hours: 6, shelf_life_hours: 72, lot_id: `LOT_${id}`, held: false, recalled: false, eligible: true }] }); }}><Plus size={13} /> Add delivery stop</button></div>
    <div className="table-scroll"><table className="editable-table stop-editor-table"><thead><tr><th>ID / name</th><th>Longitude</th><th>Latitude</th><th>Demand kg</th><th>Deadline h</th><th>Shelf life h</th><th>Planning lot</th><th>Eligibility</th><th /></tr></thead><tbody>{value.stops.map((s, i) => <tr key={i}><td><input aria-label={`Stop ${i + 1} ID`} value={s.id} onChange={e => updateStop(i, { id: e.target.value })} /><input aria-label={`Stop ${i + 1} name`} value={s.name} onChange={e => updateStop(i, { name: e.target.value })} /></td><td><CoordinateInput label={`Stop ${i + 1} longitude`} value={s.coordinates[0]} onChange={value => updateStop(i, { coordinates: [value, s.coordinates[1]] })} /></td><td><CoordinateInput label={`Stop ${i + 1} latitude`} value={s.coordinates[1]} onChange={value => updateStop(i, { coordinates: [s.coordinates[0], value] })} /></td><td><input aria-label={`Stop ${i + 1} demand kg`} type="number" min={1} max={5000} value={s.demand_kg} onChange={e => updateStop(i, { demand_kg: Number(e.target.value) })} /></td><td><input aria-label={`Stop ${i + 1} deadline hours`} type="number" step={0.25} min={0.25} max={16} value={s.deadline_hours} onChange={e => updateStop(i, { deadline_hours: Number(e.target.value) })} /></td><td><input aria-label={`Stop ${i + 1} shelf life hours`} type="number" step={0.25} min={0.25} max={168} value={s.shelf_life_hours} onChange={e => updateStop(i, { shelf_life_hours: Number(e.target.value) })} /></td><td><input aria-label={`Stop ${i + 1} lot ID`} value={s.lot_id} onChange={e => updateStop(i, { lot_id: e.target.value })} /></td><td className="editor-checks"><label><input type="checkbox" checked={s.held} onChange={e => updateStop(i, { held: e.target.checked })} />Held</label><label><input type="checkbox" checked={s.recalled} onChange={e => updateStop(i, { recalled: e.target.checked })} />Recalled (scenario)</label><label><input type="checkbox" checked={s.eligible} onChange={e => updateStop(i, { eligible: e.target.checked })} />Eligible</label></td><td><button className="icon-button" aria-label={`Remove stop ${i + 1}`} disabled={value.stops.length <= 1} onClick={() => onChange({ ...value, stops: value.stops.filter((_, j) => j !== i) })}><Trash2 size={15} /></button></td></tr>)}</tbody></table></div>
    <div className="editor-section-heading"><h3>Trucks <small>{value.trucks.length}/10</small></h3><button className="secondary small" disabled={value.trucks.length >= 10} onClick={() => onChange({ ...value, trucks: [...value.trucks, { id: nextId('TRUCK'), origin_id: value.origins[0].id, capacity_kg: 1500, refrigerated: true, eligible: true }] })}><Plus size={13} /> Add truck</button></div>
    <div className="table-scroll"><table className="editable-table"><thead><tr><th>Truck ID</th><th>Dispatch origin</th><th>Capacity kg</th><th>Eligibility</th><th /></tr></thead><tbody>{value.trucks.map((t, i) => <tr key={i}><td><input aria-label={`Truck ${i + 1} ID`} value={t.id} onChange={e => updateTruck(i, { id: e.target.value })} /></td><td><select aria-label={`Truck ${i + 1} origin`} value={t.origin_id} onChange={e => updateTruck(i, { origin_id: e.target.value })}>{value.origins.map(o => <option value={o.id} key={o.id}>{o.id} · {o.name}</option>)}</select></td><td><input aria-label={`Truck ${i + 1} capacity kg`} type="number" min={100} max={5000} value={t.capacity_kg} onChange={e => updateTruck(i, { capacity_kg: Number(e.target.value) })} /></td><td className="editor-checks"><label><input type="checkbox" checked={t.refrigerated} onChange={e => updateTruck(i, { refrigerated: e.target.checked })} />Refrigerated</label><label><input type="checkbox" checked={t.eligible} onChange={e => updateTruck(i, { eligible: e.target.checked })} />Eligible</label></td><td><button className="icon-button" aria-label={`Remove truck ${i + 1}`} disabled={value.trucks.length <= 1} onClick={() => onChange({ ...value, trucks: value.trucks.filter((_, j) => j !== i) })}><Trash2 size={15} /></button></td></tr>)}</tbody></table></div>
    {errors.length > 0 && <div role="alert" className="coverage-warning"><ul>{errors.map(error => <li key={error}>{error}</li>)}</ul></div>}
    <p className="source-note padded">Held, recalled and ineligible deliveries remain excluded even if capacity is available. Recall flags here are scenario inputs, not asserted matches to an official recall.</p>
  </section>;
}
