"""Bounded GeoJSON validation for road proximity, without inferring missing geometry."""
import math


def road_geometry(value, max_vertices=20000):
    """Return a finite WGS84 point/line geometry or None, never partially repair it."""
    if not isinstance(value, dict):
        return None
    count = 0

    def point(item):
        nonlocal count
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            raise ValueError('Missing coordinate pair')
        x, y = item[:2]
        if (isinstance(x, bool) or isinstance(y, bool)
                or not isinstance(x, (int, float)) or not isinstance(y, (int, float))
                or not math.isfinite(x) or not math.isfinite(y)
                or not -180 <= x <= 180 or not -90 <= y <= 90):
            raise ValueError('Invalid WGS84 coordinate')
        count += 1
        if count > max_vertices:
            raise ValueError('Geometry exceeds vertex bound')
        return [x, y]

    def sequence(items, minimum):
        if not isinstance(items, (list, tuple)) or len(items) < minimum:
            raise ValueError('Missing geometry vertices')
        return [point(item) for item in items]

    try:
        kind, coordinates = value.get('type'), value.get('coordinates')
        if kind == 'Point':
            result = point(coordinates)
        elif kind == 'MultiPoint':
            result = sequence(coordinates, 1)
        elif kind == 'LineString':
            result = sequence(coordinates, 2)
        elif kind == 'MultiLineString':
            if not isinstance(coordinates, (list, tuple)) or not coordinates:
                return None
            result = [sequence(line, 2) for line in coordinates]
        else:
            return None
    except (ValueError, TypeError, OverflowError):
        return None
    return {'type': kind, 'coordinates': result}


def vertices(geometry):
    """Iterate vertices of an already validated geometry without recursive parsing."""
    kind, coords = geometry['type'], geometry['coordinates']
    if kind == 'Point':
        return [coords]
    if kind == 'MultiLineString':
        return [point for line in coords for point in line]
    return coords
