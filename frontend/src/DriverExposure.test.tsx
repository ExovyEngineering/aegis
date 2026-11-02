import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import DriverExposure from './DriverExposure';
import { api } from './api';
import type { Network, Shipment } from './types';

vi.mock('./api', async () => ({ ...await vi.importActual('./api'), api: vi.fn() }));
vi.mock('./RouteLabMap', () => ({ default: ({ routes }: { routes: { distance_m: number }[] }) => <div data-testid="driver-route-map">{routes[0]?.distance_m}</div> }));

const first = { id: 'SH01', truck_id: 'T01', origin: 'DC1', destination: 'D1', quantity_kg: 400, temperature_c: 2.5 } as Shipment;
const second = { ...first, id: 'SH02', destination: 'D2' } as Shipment;
const network = { revision: 3, nodes: [{ id: 'DC1', name: 'Simulated origin', kind: 'dc', coordinates: [-92, 38] }, { id: 'D1', name: 'First simulated destination', kind: 'destination', coordinates: [-93, 39] }, { id: 'D2', name: 'Second simulated destination', kind: 'destination', coordinates: [-91, 37] }] } as unknown as Network;
const projection = (shipment = first, revision = 3, maximum = 4.2) => ({ shipment_id: shipment.id, network_revision: revision, max_temperature_c: maximum, status: 'review', provenance: 'simulated cargo projection' });
const route = (meters: number) => ({ fallback: true, payload: { routes: [{ distance: meters, duration: 600, geometry: { type: 'LineString', coordinates: [[-92, 38], [-93, 39]] } }] } });
function deferred<T>() { let resolve!: (value: T) => void; let reject!: (value: unknown) => void; const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; }
beforeEach(() => { vi.mocked(api).mockReset(); });

it('ignores late exposure responses from a previously selected shipment', async () => {
  const old = deferred<any>(); const current = deferred<any>();
  vi.mocked(api).mockImplementation(path => path.includes('SH01') ? old.promise : current.promise);
  const { rerender } = render(<DriverExposure shipment={first} network={network} />);
  rerender(<DriverExposure shipment={second} network={network} />);
  await act(async () => current.resolve(projection(second, 3, 7.6)));
  expect(screen.getByText('7.6°C')).toBeInTheDocument();
  await act(async () => old.resolve(projection(first, 3, 19.9)));
  expect(screen.queryByText('19.9°C')).not.toBeInTheDocument();
  expect(screen.getByText('7.6°C')).toBeInTheDocument();
  expect(vi.mocked(api).mock.calls.filter(([path]) => path === '/route')).toHaveLength(0);
});

it('clears old routes on trip changes and ignores a slower earlier route response', async () => {
  const old = deferred<any>(); const current = deferred<any>(); let routeRequests = 0;
  vi.mocked(api).mockImplementation(path => path === '/route' ? (++routeRequests === 1 ? old.promise : current.promise) : Promise.resolve(projection(path.includes('SH02') ? second : first)));
  const { rerender } = render(<DriverExposure shipment={first} network={network} />);
  const request = screen.getByRole('button', { name: 'Review trip route while parked' });
  fireEvent.click(request);
  expect(screen.getByRole('button', { name: 'Requesting route…' })).toBeDisabled();
  rerender(<DriverExposure shipment={second} network={network} />);
  fireEvent.click(await screen.findByRole('button', { name: 'Review trip route while parked' }));
  await act(async () => current.resolve(route(22000)));
  expect(screen.getByTestId('driver-route-map')).toHaveTextContent('22000');
  await act(async () => old.resolve(route(999000)));
  expect(screen.getByTestId('driver-route-map')).toHaveTextContent('22000');
  expect(routeRequests).toBe(2);
  rerender(<DriverExposure shipment={first} network={network} />);
  expect(screen.queryByTestId('driver-route-map')).not.toBeInTheDocument();
});

it('rejects an exposure from another network revision and shows the recovery action', async () => {
  vi.mocked(api).mockResolvedValue(projection(first, 4));
  const { rerender } = render(<DriverExposure shipment={first} network={network} />);
  expect(await screen.findByRole('alert')).toHaveTextContent('Trip or network changed while loading');
  expect(screen.queryByText('4.2°C')).not.toBeInTheDocument();
  rerender(<DriverExposure shipment={first} network={{ ...network, revision: 4 }} />);
  expect(await screen.findByText('4.2°C')).toBeInTheDocument();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

it('locks route requests in driving focus and discards a request begun before locking', async () => {
  const pending = deferred<any>();
  vi.mocked(api).mockImplementation(path => path === '/route' ? pending.promise : Promise.resolve(projection()));
  const { rerender } = render(<DriverExposure shipment={first} network={network} />);
  fireEvent.click(screen.getByRole('button', { name: 'Review trip route while parked' }));
  rerender(<DriverExposure shipment={first} network={network} disabled />);
  const locked = screen.getByRole('button', { name: 'Review trip route while parked' });
  expect(locked).toBeDisabled();fireEvent.click(locked);
  await act(async () => pending.resolve(route(12000)));
  expect(screen.queryByTestId('driver-route-map')).not.toBeInTheDocument();
  expect(vi.mocked(api).mock.calls.filter(([path]) => path === '/route')).toHaveLength(1);
  expect(screen.getByText(/Route requests are locked in driving focus/)).toBeInTheDocument();
});

it('shows route failures and allows a deliberate retry while parked', async () => {
  vi.mocked(api).mockImplementation(path => path === '/route' ? Promise.reject(new Error('Routing service unavailable')) : Promise.resolve(projection()));
  render(<DriverExposure shipment={first} network={network} />);
  fireEvent.click(screen.getByRole('button', { name: 'Review trip route while parked' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Routing service unavailable');
  await waitFor(() => expect(screen.getByRole('button', { name: 'Review trip route while parked' })).toBeEnabled());
});
