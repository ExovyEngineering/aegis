import { useState } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import CustomOperationEditor, { CoordinateInput, customOperationErrors, newPlanningOperation, operationFromPreset } from './CustomOperationEditor';

it('normalizes a preset without posting solver output or unrelated metadata', () => {
  const draft = newPlanningOperation();
  const normalized = operationFromPreset({ ...draft, id: 'farm', seed: 123, nodes: [], simulation: true, origins: [{ ...draft.origins[0], capacity_kg: 9999 }], stops: [{ ...draft.stops[0], kind: 'destination' }] });
  expect(customOperationErrors(normalized)).toEqual([]);
  expect(Object.keys(normalized).sort()).toEqual(['name', 'origins', 'stops', 'trucks']);
  expect(normalized.origins[0]).not.toHaveProperty('capacity_kg');
  expect(normalized.stops[0]).not.toHaveProperty('kind');
  expect(normalized.stops[0].lot_id).toBe('LOT1');
});
it('rejects repeated IDs, invalid coordinates and shared planning lots before sending', () => {
  const draft = newPlanningOperation();
  draft.stops.push({ ...draft.stops[0], coordinates: [181, 91] });
  expect(customOperationErrors(draft).join(' ')).toContain('IDs must be unique');
  expect(customOperationErrors(draft).join(' ')).toContain('longitude and latitude');
  expect(customOperationErrors(draft).join(' ')).toContain('distinct planning lot');
});
it('keeps truck references valid when an origin ID changes or an origin is removed', () => {
  function Editor() { const [draft, setDraft] = useState(newPlanningOperation); return <CustomOperationEditor value={draft} onChange={setDraft} templates={[]} />; }
  render(<Editor />);
  fireEvent.change(screen.getByLabelText('Origin 1 ID'), { target: { value: 'MY_FARM' } });
  expect(screen.getByLabelText('Truck 1 origin')).toHaveValue('MY_FARM');
  fireEvent.click(screen.getByRole('button', { name: 'Add origin' }));
  fireEvent.click(screen.getByRole('button', { name: 'Remove origin 1' }));
  expect(screen.getByLabelText('Truck 1 origin')).toHaveValue('ORIGIN1');
  expect(screen.getByRole('button', { name: 'Remove origin 1' })).toBeDisabled();
});
it('preserves a typed minus sign and reports incomplete coordinates as invalid instead of zero', () => {
  function Coordinate() { const [longitude, setLongitude] = useState(-92.4); return <><CoordinateInput label="Planning longitude" value={longitude} onChange={setLongitude} /><span>{Number.isFinite(longitude) ? longitude : 'Incomplete coordinate'}</span></>; }
  render(<Coordinate />);
  fireEvent.change(screen.getByLabelText('Planning longitude'), { target: { value: '-' } });
  expect(screen.getByLabelText('Planning longitude')).toHaveValue('-');
  expect(screen.getByText('Incomplete coordinate')).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Planning longitude'), { target: { value: '-92.5' } });
  expect(screen.getByLabelText('Planning longitude')).toHaveValue('-92.5');
  expect(screen.getByText('-92.5')).toBeInTheDocument();
});
it('enforces the backend lot-id pattern and length while allowing optional generated planning keys', () => {
  const draft = newPlanningOperation();
  for (const invalid of ['LOT A', '1LOT', 'LOT/1', 'A'.repeat(49), '']) {
    draft.stops[0].lot_id = invalid;
    expect(customOperationErrors(draft).join(' ')).toContain('48 characters maximum');
  }
  draft.stops[0].lot_id = '  LOT_1-with-hyphens  ';
  expect(customOperationErrors(draft)).toEqual([]);
  draft.stops[0].lot_id = 'A'.repeat(48);
  expect(customOperationErrors(draft)).toEqual([]);
  draft.stops[0].lot_id = null;
  draft.stops.push({ ...draft.stops[0], id: 'STOP2', lot_id: null });
  expect(customOperationErrors(draft)).toEqual([]);
  draft.stops[1].lot_id = 'PLAN-STOP1';
  expect(customOperationErrors(draft).join(' ')).toContain('distinct planning lot');
});
it('sends a cleared optional lot as null and labels the generated key as fictional', () => {
  function Editor() { const [draft, setDraft] = useState(newPlanningOperation); return <><CustomOperationEditor value={draft} onChange={setDraft} templates={[]} /><output aria-label="Lot input model">{JSON.stringify(draft.stops[0].lot_id)}</output></>; }
  render(<Editor />);
  fireEvent.change(screen.getByLabelText('Stop 1 lot ID'), { target: { value: '' } });
  expect(screen.getByLabelText('Stop 1 lot ID')).toHaveValue('');
  expect(screen.getByLabelText('Lot input model')).toHaveTextContent('null');
  expect(screen.getByText(/A blank planning lot uses a fictional PLAN-prefixed key/)).toBeInTheDocument();
});
