import { act, render } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import MapViewport from './MapViewport';

const state = vi.hoisted(() => ({ map: {} as any }));
vi.mock('react-leaflet', () => ({ useMap: () => state.map }));
let resize: ResizeObserverCallback;
let unload: () => void;
let pane: HTMLElement | undefined;
let container: HTMLDivElement;
const disconnect = vi.fn();
describe('Leaflet map lifecycle', () => {
  beforeEach(() => {
    container = document.createElement('div'); pane = document.createElement('div'); container.append(pane); document.body.append(container);
    vi.stubGlobal('ResizeObserver', class { constructor(callback: ResizeObserverCallback) { resize = callback; } observe() {} disconnect = disconnect; });
    state.map = { getContainer: () => container, getPane: () => pane, invalidateSize: vi.fn(), fitBounds: vi.fn(), stop: vi.fn(), on: vi.fn((_event: string, callback: () => void) => { unload = callback; }), off: vi.fn() };
  });
  it('fits without animation and ignores queued resize after map unload', () => {
    const { unmount } = render(<MapViewport coordinates={[[-92.4, 39], [-92.3, 39.1]]} />);
    expect(state.map.fitBounds).toHaveBeenCalledWith([[39, -92.4], [39.1, -92.3]], expect.objectContaining({ animate: false }));
    act(() => resize([], {} as ResizeObserver));
    expect(state.map.invalidateSize).toHaveBeenCalledTimes(1);
    unload(); pane?.remove(); pane = undefined;
    act(() => resize([], {} as ResizeObserver));
    expect(state.map.invalidateSize).toHaveBeenCalledTimes(1);
    expect(() => unmount()).not.toThrow();
    expect(state.map.stop).not.toHaveBeenCalled();
    container.remove();
  });
  it('disconnects and stops remaining motion while a mounted map is cleaned up', () => {
    const { unmount } = render(<MapViewport />);
    unmount();
    expect(state.map.stop).toHaveBeenCalledTimes(1);
    act(() => resize([], {} as ResizeObserver));
    expect(state.map.invalidateSize).not.toHaveBeenCalled();
    expect(disconnect).toHaveBeenCalled();
    container.remove();
  });
});
