"""Conservative route/event geometry proximity; review only, not a closure-routing engine."""
import math
from backend.adapters import distance
from backend.road_geometry import road_geometry, vertices

def point_segment_meters(point,a,b):
    lat=math.radians(point[1]); scale_x=111320*math.cos(lat); scale_y=111320
    ax=(a[0]-point[0])*scale_x; ay=(a[1]-point[1])*scale_y; bx=(b[0]-point[0])*scale_x; by=(b[1]-point[1])*scale_y
    dx=bx-ax; dy=by-ay; denom=dx*dx+dy*dy
    t=max(0,min(1,-(ax*dx+ay*dy)/denom)) if denom else 0
    return math.hypot(ax+t*dx,ay+t*dy)

def intersects(a,b,c,d):
    def cross(p,q,r): return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    def sign(x): return (x>1e-12)-(x<-1e-12)
    c1,c2,c3,c4=[sign(x) for x in (cross(a,b,c),cross(a,b,d),cross(c,d,a),cross(c,d,b))]
    if c1*c2<0 and c3*c4<0:return True
    def on(p,q,r):return min(p[0],q[0])-1e-10<=r[0]<=max(p[0],q[0])+1e-10 and min(p[1],q[1])-1e-10<=r[1]<=max(p[1],q[1])+1e-10
    return (c1==0 and on(a,b,c)) or (c2==0 and on(a,b,d)) or (c3==0 and on(c,d,a)) or (c4==0 and on(c,d,b))

def proximity(route,geometry):
    validated_route=road_geometry({'type':'LineString','coordinates':route})
    geometry=road_geometry(geometry)
    if validated_route is None or geometry is None:return math.inf
    route=validated_route['coordinates']
    kind=geometry.get('type'); coords=geometry.get('coordinates',[]); route_segments=list(zip(route,route[1:]))
    if not route_segments:return math.inf
    if kind=='Point':return min(point_segment_meters(coords,a,b) for a,b in route_segments)
    if kind=='MultiPoint':return min((proximity(route,{'type':'Point','coordinates':c}) for c in coords),default=math.inf)
    lines=[coords] if kind=='LineString' else coords if kind=='MultiLineString' else []
    best=math.inf
    for line in lines:
        for c,d in zip(line,line[1:]):
            for a,b in route_segments:
                if intersects(a,b,c,d):return 0
                best=min(best,point_segment_meters(c,a,b),point_segment_meters(d,a,b),point_segment_meters(a,c,d),point_segment_meters(b,c,d))
    return best

def review_routes(routing,modot,buffer_m=250):
    import numpy as np
    from datetime import datetime,timezone
    output=[]
    layers=modot.get('incident_layers',[]) if modot else []
    layers=[layer for layer in layers if isinstance(layer,dict)]
    stale=not bool(modot and modot.get('retrieved_at')) or bool(modot and modot.get('stale')) or any(layer.get('stale',False) for layer in layers)
    if modot and modot.get('retrieved_at'):
        try:
            age=(datetime.now(timezone.utc)-datetime.fromisoformat(modot['retrieved_at'])).total_seconds()
            stale=stale or age>600 or age < -60
        except (ValueError,TypeError):stale=True
    unusable_geometry_count=0
    checked_layers=[]
    for layer in layers:
        checked=[]
        payload=layer.get('payload')
        features=payload.get('features',[]) if isinstance(payload,dict) else []
        if not isinstance(features,list):features=[];unusable_geometry_count+=1
        for feature in features:
            geometry=road_geometry(feature.get('geometry')) if isinstance(feature,dict) else None
            if geometry is None:unusable_geometry_count+=1;continue
            checked.append(dict(feature,geometry=geometry))
        checked_layers.append(dict(layer,payload={'features':checked}))
    for index,r in enumerate(routing.get('payload',{}).get('routes',[])):
        geometry=road_geometry(r.get('geometry'))
        route=geometry['coordinates'] if geometry and geometry['type']=='LineString' else []; hits=[]
        points=np.asarray(route,dtype=float)
        segments=np.stack([points[:-1],points[1:]],axis=1) if len(points)>1 else np.empty((0,2,2))
        mins=segments.min(axis=1) if len(segments) else np.empty((0,2)); maxs=segments.max(axis=1) if len(segments) else np.empty((0,2))
        for layer in checked_layers:
            for feature in layer.get('payload',{}).get('features',[]):
                geom=feature.get('geometry') or {}; coords=geom.get('coordinates',[])
                if not coords:continue
                event_vertices=np.asarray(vertices(geom),dtype=float)
                if not len(event_vertices):continue
                # Fast conservative bounding-box pruning before exact segment checks.
                lo=event_vertices.min(axis=0); hi=event_vertices.max(axis=0); margin=np.array([buffer_m/(111000*max(.1,math.cos(math.radians(float(event_vertices[:,1].mean()))))),buffer_m/110000])
                near=(maxs[:,0]>=lo[0]-margin[0]) & (mins[:,0]<=hi[0]+margin[0]) & (maxs[:,1]>=lo[1]-margin[1]) & (mins[:,1]<=hi[1]+margin[1])
                gap=min((proximity(seg.tolist(),geom) for seg in segments[near]),default=math.inf)
                if gap<=buffer_m:hits.append({'layer_id':layer.get('layer_id'),'layer_name':layer.get('layer_name','Road events'),'proximity_m':round(gap,1),'properties':feature.get('properties',{})})
        output.append({'alternative_index':index,'distance_m':r['distance'],'duration_seconds':r['duration'],'nearby_events':hits,'review_required':bool(hits) or not route or not layers or stale or unusable_geometry_count>0 or not modot.get('coverage_complete',False) or routing.get('fallback',False)})
    return {'alternatives':output,'proximity_buffer_m':buffer_m,'modot_retrieved_at':modot.get('retrieved_at') if modot else None,'coverage_complete':bool(modot and modot.get('coverage_complete')) and not unusable_geometry_count,'unusable_geometry_count':unusable_geometry_count,'stale':stale,'geographic_scope':'MoDOT is a Missouri feed; complete route coverage and state-boundary containment are not established.', 'warning':'MoDOT covers Missouri only; out-of-state route portions and state-boundary containment are not verified. Proximity can include nearby parallel roads. Events may duplicate across point/line layers. Missing or invalid point/line geometry is counted and not screened. OSRM ignores current closures and commercial restrictions. Alternatives require dispatcher review and truck-route validation; no truck-safe assertion.'}
