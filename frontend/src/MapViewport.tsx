import { useEffect } from 'react';
import { useMap } from 'react-leaflet';

/** A queued ResizeObserver must never invalidate a detached Leaflet map. */
export default function MapViewport({ coordinates }: { coordinates?: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    let active = true;
    const container = map.getContainer();
    const usable = () => active && container.isConnected && !!map.getPane('mapPane')?.isConnected;
    const observer = new ResizeObserver(() => {
      if (usable()) map.invalidateSize({ animate: false, pan: false });
    });
    const onUnload = () => { active = false; observer.disconnect(); };
    map.on('unload', onUnload);
    if (usable() && coordinates?.length) map.fitBounds(coordinates.map(([longitude, latitude]): [number, number] => [latitude, longitude]), { padding: [45, 45], maxZoom: 10, animate: false });
    observer.observe(container);
    return () => {
      active = false;
      observer.disconnect();
      map.off('unload', onUnload);
      // React-Leaflet may remove the parent map before this child's cleanup.
      if (map.getPane('mapPane')?.isConnected) map.stop();
    };
  }, [map, coordinates]);
  return null;
}
