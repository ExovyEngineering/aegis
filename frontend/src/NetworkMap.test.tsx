import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';
import NetworkMap from './NetworkMap';
import type { Network } from './types';

const captured = vi.hoisted(() => ({ viewport: vi.fn(), popups: [] as HTMLElement[] }));
vi.mock('./MapViewport', () => ({ default: ({ coordinates }: { coordinates: unknown }) => { captured.viewport(coordinates); return null; } }));
vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
  TileLayer: () => null,
  CircleMarker: ({ children, eventHandlers }: { children?: ReactNode; eventHandlers?: { click(): void } }) => <div data-testid="marker" onClick={eventHandlers?.click}>{children}</div>,
  Popup: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
  Polyline: ({ children, pathOptions, eventHandlers, positions }: { children?: ReactNode; pathOptions: any; positions: any; eventHandlers?: { click(): void } }) => <div data-testid="line" data-weight={pathOptions.weight} data-opacity={pathOptions.opacity} data-positions={JSON.stringify(positions)} onClick={eventHandlers?.click}>{children}</div>,
  GeoJSON: ({ data, onEachFeature }: { data: any; onEachFeature: (feature: any, layer: any) => void }) => { onEachFeature(data, { bindPopup: (content: HTMLElement) => { captured.popups.push(content); } }); return null; },
}));

const network: Network = {
  seed: 1, revision: 0, provenance: 'simulated',
  nodes: [{ id: 'DC1', kind: 'dc', name: 'Fictional DC', coordinates: [-92.3, 38.9] }, { id: 'D01', kind: 'destination', name: 'Fictional stop', coordinates: [-90.2, 38.6] }],
  shipments: [1, 2].map(index => ({ id: `SH0${index}`, origin: 'DC1', destination: 'D01', truck_id: `T0${index}`, lot_id: 'L01', quantity_kg: 400, temperature_c: 2, deadline_hours: 6, estimated_hours: 2, estimated_distance_km: 130, review_priority: 'routine' })),
  trucks: [{ id: 'T01', eligible: true, capacity_kg: 1000 }, { id: 'T02', eligible: true, capacity_kg: 1000 }], lots: [], telemetry: [], events: [],
};
const paths = [[[-92.3, 38.9], [-90.2, 38.6]], [[-92.3, 38.9], [-91.7, 39], [-90.2, 38.6]]];
const route = { shipmentId: 'SH01', displayLabel: 'Requested route for SH01', fallback: false, payload: { routes: paths.map(coordinates => ({ distance: 140000, duration: 7500, geometry: { type: 'LineString', coordinates } })) } };

describe('Command map presentation and read-only controls', () => {
  beforeEach(() => { captured.viewport.mockClear(); captured.popups.length = 0; });

  it('focuses selected road geometry and highlights it after subdued alternatives', () => {
    render(<NetworkMap network={network} facilities={[]} selected={network.shipments[0]} route={route} selectedAlternative={1} onSelect={vi.fn()} />);
    expect(captured.viewport.mock.calls.at(-1)?.[0]).toEqual(paths[1]);
    const lines = screen.getAllByTestId('line');
    expect(lines.at(-1)).toHaveAttribute('data-weight', '5');
    expect(lines.at(-2)).toHaveAttribute('data-opacity', '0.4');
    expect(screen.getByText(/Road comparison for SH01 · alternative 2/)).toBeInTheDocument();
    expect(screen.getByText(/does not change shipment ETAs/)).toBeInTheDocument();
  });

  it('keeps viewport coordinates stable when layers and overlay visibility change', () => {
    const onSelect = vi.fn();
    const { rerender } = render(<NetworkMap network={network} facilities={[]} selected={network.shipments[0]} route={route} selectedAlternative={1} onSelect={onSelect} />);
    const coordinates = captured.viewport.mock.calls.at(-1)?.[0];
    fireEvent.click(screen.getByRole('checkbox', { name: 'Requested route' }));
    expect(captured.viewport.mock.calls.at(-1)?.[0]).toBe(coordinates);
    rerender(<NetworkMap network={network} facilities={[]} selected={network.shipments[0]} route={route} selectedAlternative={1} planOverlay={{ label: 'Scenario A', scope: 'scenario', shipments: [network.shipments[1]] }} onSelect={onSelect} />);
    expect(captured.viewport.mock.calls.at(-1)?.[0]).toBe(coordinates);
    expect(onSelect).not.toHaveBeenCalled();
  });

  it('renders only the chosen plan connections and preserves selectable simulated trips', () => {
    const onSelect = vi.fn();
    render(<NetworkMap network={network} facilities={[]} selected={network.shipments[0]} planOverlay={{ label: 'Scenario D', scope: 'scenario', shipments: [{ ...network.shipments[1], lot_id: 'L02' }] }} onSelect={onSelect} />);
    expect(screen.getAllByTestId('line')).toHaveLength(1);
    expect(screen.getByText(/SH02 · proposed scenario connection/)).toBeInTheDocument();
    expect(screen.getByText(/Lot L02 · truck T02/)).toBeInTheDocument();
    expect(screen.getByText(/SH01 is outside this overlay/)).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('line'));
    expect(onSelect).toHaveBeenCalledWith('SH02');
    expect(captured.viewport.mock.calls.at(-1)?.[0]).toEqual(paths[0]);
  });

  it('shows an empty approved overlay without candidate lines or fictional movement', () => {
    render(<NetworkMap network={network} facilities={[]} selected={network.shipments[0]} planOverlay={{ label: 'Approved assignments', scope: 'approved', shipments: [] }} onSelect={vi.fn()} />);
    expect(screen.queryByTestId('line')).not.toBeInTheDocument();
    expect(screen.getByText(/0 approved assignment connections shown/)).toBeInTheDocument();
    expect(screen.getByText(/not moving vehicles or physical departures/)).toBeInTheDocument();
  });

  it('labels independent reference geometry and unavailable alternatives explicitly', () => {
    render(<NetworkMap network={network} facilities={[]} route={{ fallback: true, payload: { routes: [{}, route.payload.routes[0]] } }} selectedAlternative={0} onSelect={vi.fn()} />);
    expect(screen.getByText(/Independent cached reference route · alternative 2/)).toBeInTheDocument();
    expect(screen.getByText(/requested alternative has no usable geometry/)).toBeInTheDocument();
    expect(screen.getByText(/1 route geometry was not drawn/)).toBeInTheDocument();
  });

  it('renders external source popup text without interpreting provider HTML', () => {
    const source = '<img src=x onerror=alert(1)>Not markup';
    render(<NetworkMap network={network} facilities={[]} weather={{ payload: { features: [{ type: 'Feature', geometry: { type: 'Point', coordinates: [-92.3, 38.9] }, properties: { headline: source } }] } }} onSelect={vi.fn()} />);
    fireEvent.click(screen.getByRole('button',{name:'Check weather'}));
    expect(captured.popups[0].textContent).toBe(source);
    expect(captured.popups[0].querySelector('img')).toBeNull();
  });

  it('starts with a simple deliveries view and explains how to produce a route', () => {
    render(<NetworkMap network={network} facilities={[]} selected={network.shipments[0]} onSelect={vi.fn()} />);
    expect(screen.getByRole('button',{name:'Plan deliveries'})).toHaveAttribute('aria-pressed','true');
    expect(screen.getByRole('checkbox',{name:'Simulated deliveries'})).toBeChecked();
    expect(screen.getByRole('checkbox',{name:'Weather warnings'})).not.toBeChecked();
    expect(screen.getByRole('checkbox',{name:'Road incidents'})).not.toBeChecked();
    expect(screen.getByText('No route result yet · request one in trip detail')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Explain requested route'}));
    const explanation=screen.getByRole('region',{name:'Layer explanation'});
    expect(explanation).toHaveTextContent('Select a shipment, click Request road route');
    expect(explanation).toHaveTextContent('A switch cannot generate a route');
  });

  it('changes only visibility when choosing task-based views, retaining route focus and source inputs', () => {
    const onSelect=vi.fn();
    const weather={payload:{features:[{type:'Feature',geometry:{type:'Point',coordinates:[-92.3,38.9]},properties:{event:'Test warning'}}]},retrieved_at:'2026-10-29T10:00:00+00:00',fixture:true,stale:true};
    const roads={payload:{features:[{type:'Feature',geometry:{type:'Point',coordinates:[-92.3,38.9]},properties:{Description:'Test road record'}}]},retrieved_at:'2026-10-29T10:00:00+00:00',stale:true};
    const before=JSON.stringify({network,route,weather,roads});
    render(<NetworkMap network={network} facilities={[]} route={route} selectedAlternative={1} weather={weather} roads={roads} selected={network.shipments[0]} onSelect={onSelect} />);
    const focused=captured.viewport.mock.calls.at(-1)?.[0];
    fireEvent.click(screen.getByRole('button',{name:'Check weather'}));
    expect(screen.getByRole('checkbox',{name:'Weather warnings'})).toBeChecked();
    expect(screen.getByRole('checkbox',{name:'Road incidents'})).not.toBeChecked();
    expect(screen.getByRole('region',{name:'Layer explanation'})).toHaveTextContent('not add a delay');
    expect(screen.getByRole('region',{name:'Layer explanation'})).toHaveTextContent('Dated fixture · source age needs review');
    fireEvent.click(screen.getByRole('button',{name:'Review roads'}));
    expect(screen.getByRole('checkbox',{name:'Road incidents'})).toBeChecked();
    expect(screen.getByRole('checkbox',{name:'Weather warnings'})).not.toBeChecked();
    expect(screen.getByRole('region',{name:'Layer explanation'})).toHaveTextContent('OSRM does not automatically avoid these incidents');
    expect(screen.getByRole('region',{name:'Layer explanation'})).toHaveTextContent('Stale saved response');
    fireEvent.click(screen.getByRole('button',{name:'View facilities'}));
    expect(screen.getByRole('checkbox',{name:'FSIS facilities'})).toBeChecked();
    expect(screen.getByRole('checkbox',{name:'Requested route'})).not.toBeChecked();
    fireEvent.click(screen.getByRole('button',{name:'Plan deliveries'}));
    expect(screen.getByRole('checkbox',{name:'Requested route'})).toBeChecked();
    expect(captured.viewport.mock.calls.at(-1)?.[0]).toBe(focused);
    expect(JSON.stringify({network,route,weather,roads})).toBe(before);
    expect(onSelect).not.toHaveBeenCalled();
  });

  it('shows real feature availability without turning empty or missing evidence into clearance', () => {
    render(<NetworkMap network={network} facilities={[]} weather={{payload:{features:[]},retrieved_at:'2026-10-29T20:00:00'}} roads={{payload:{features:'not a feature array'}}} onSelect={vi.fn()} />);
    expect(screen.getByText('No drawable warning geometry in this response')).toBeInTheDocument();
    expect(screen.getByText('No drawable incident geometry in this response')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Check weather'}));
    expect(screen.getByRole('region',{name:'Layer explanation'})).toHaveTextContent('Retrieval time is missing or unverified');
    expect(screen.getByRole('region',{name:'Layer explanation'})).toHaveTextContent('separate from cargo temperature');
  });

  it('keeps missing sources explicit instead of suggesting a live refresh happened', () => {
    render(<NetworkMap network={network} facilities={[]} onSelect={vi.fn()} />);
    expect(screen.getByText('No weather response loaded')).toBeInTheDocument();
    expect(screen.getByText('No road response loaded')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Review roads'}));
    expect(screen.getByRole('region',{name:'Layer explanation'})).toHaveTextContent('No source response is loaded');
  });

  it('counts only usable facility coordinates and explains their separation from the supply network', () => {
    const facilities=[{establishment_id:'M1',establishment_name:'Official location',latitude:38.9,longitude:-92.3,activities:'Poultry'},{establishment_id:'M2',establishment_name:'Unusable coordinate',latitude:200,longitude:-92.3,activities:'Poultry'}];
    render(<NetworkMap network={network} facilities={facilities} onSelect={vi.fn()} />);
    expect(screen.getByText('1 usable directory location')).toBeInTheDocument();
    expect(screen.getAllByTestId('marker')).toHaveLength(4);
    fireEvent.click(screen.getByRole('button',{name:'View facilities'}));
    expect(screen.getAllByTestId('marker')).toHaveLength(5);
    expect(screen.getByRole('region',{name:'Layer explanation'})).toHaveTextContent('does not establish a supply contract');
    expect(screen.getByRole('region',{name:'Layer explanation'})).toHaveTextContent('retrieval time is not available in these map rows');
  });

  it('reports hidden connections honestly while retaining the chosen overlay', () => {
    render(<NetworkMap network={network} facilities={[]} onSelect={vi.fn()} />);
    fireEvent.click(screen.getByRole('checkbox',{name:'Simulated deliveries'}));
    expect(screen.queryByTestId('line')).not.toBeInTheDocument();
    expect(screen.getByText(/0 candidate connections shown/)).toHaveTextContent('2 remain in the selected overlay');
    expect(screen.getByText('Custom view')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Explain simulated deliveries'}));
    expect(screen.getByRole('region',{name:'Layer explanation'})).toHaveTextContent('not GPS positions');
  });

  it('keeps one layer explanation open at a time and puts the map symbol key behind a concise control', () => {
    render(<NetworkMap network={network} facilities={[]} onSelect={vi.fn()} />);
    fireEvent.click(screen.getByRole('button',{name:'Explain weather warnings'}));
    expect(screen.getByRole('button',{name:'Explain weather warnings'})).toHaveAttribute('aria-expanded','true');
    fireEvent.click(screen.getByRole('button',{name:'Explain fsis facilities'}));
    expect(screen.getAllByRole('region',{name:'Layer explanation'})).toHaveLength(1);
    expect(screen.getByRole('button',{name:'Explain weather warnings'})).toHaveAttribute('aria-expanded','false');
    expect(within(screen.getByRole('region',{name:'Layer explanation'})).getByText('FSIS facilities')).toBeInTheDocument();
    const key=screen.getByText('Read the map symbols and comparison limits');
    fireEvent.click(key);
    expect(key.closest('details')).toHaveAttribute('open');
    expect(screen.getByText(/Dark circles are fictional distribution centers/)).toBeInTheDocument();
  });
});
