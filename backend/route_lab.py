"""Isolated, deterministic farm and multi-depot capacitated routing laboratory."""
import copy,json,math,random
from ortools.constraint_solver import pywrapcp,routing_enums_pb2
from backend.adapters import distance,OSRMRoutingAdapter
from backend.paths import ROOT,read_json
from backend.cold_chain import project_temperature
from backend.simulation import seed_network,SEED
from backend.route_review import review_routes

def operation_preset(preset='farm',truck_count=None,truck_capacity_kg=None):
    if preset not in ('farm','regional'):raise ValueError('Unknown operational preset')
    if truck_count is not None and not 1<=truck_count<=10:raise ValueError('Truck count must be 1–10')
    if truck_capacity_kg is not None and not 100<=truck_capacity_kg<=5000:raise ValueError('Truck capacity must be 100–5000 kg')
    base=seed_network();rng=random.Random(SEED)
    if preset=='farm':
        origins=[{'id':'FARM1','name':'Columbia-area farm (simulated)','kind':'farm','coordinates':[-92.40,39.0],'inventory_kg':3000}]
        stops=[{'id':f'FD{i+1:02}','name':f'Farm delivery {i+1} (simulated)','kind':'destination','coordinates':[-92.40+rng.uniform(-.22,.22),39.0+rng.uniform(-.18,.18)],'demand_kg':300,'deadline_hours':6,'lot_id':f'FL{i+1:02}','held':i==7,'recalled':False,'eligible':True} for i in range(8)]
        count=truck_count or 3;name='Single-farm dispatch';description='One simulated farm dispatching refrigerated trucks to eight delivery stops.'
    else:
        origins=[dict(n,inventory_kg=4000) for n in base['nodes'] if n['kind']=='dc']
        stops=[dict(n,deadline_hours=6,lot_id=f'RL{i+1:02}',held=i==0,recalled=False,eligible=True) for i,n in enumerate(n for n in base['nodes'] if n['kind']=='destination')]
        count=truck_count or 8;name='Multi-location fleet';description='Two simulated distribution locations coordinating a regional refrigerated fleet.'
    capacity=truck_capacity_kg or 1500
    trucks=[{'id':f'{"F" if preset=="farm" else "R"}T{i+1:02}','origin_id':origins[i%len(origins)]['id'],'capacity_kg':capacity,'refrigerated':True,'eligible':True} for i in range(count)]
    return {'id':preset,'name':name,'description':description,'origins':origins,'stops':stops,'nodes':origins+stops,'trucks':trucks,'seed':SEED,'simulation':True}

def estimated_matrix(coordinates):
    distances=[[round(distance(a,b)*1.25) for b in coordinates] for a in coordinates]
    return {'fallback':True,'provenance':'estimated haversine x 1.25 at 65 km/h; no road geometry','payload':{'distances':distances,'durations':[[d/(65000/3600) for d in row] for row in distances]}}

def plan_routes(preset='farm',routing='estimated',truck_count=None,truck_capacity_kg=None,max_route_hours=8,refrigeration_fault=False,ambient_temperature_c=30,delay_minutes=0,operation=None):
    if routing not in ('estimated','osrm'):raise ValueError('Unknown routing mode')
    if not .25<=max_route_hours<=16 or not 0<=delay_minutes<=360 or not -30<=ambient_temperature_c<=55:raise ValueError('Invalid route duration, delay or ambient assumption')
    data=copy.deepcopy(operation or operation_preset(preset,truck_count,truck_capacity_kg));nodes=data['nodes'];trucks=data['trucks'];origins=data['origins'];stops=data['stops'];byid={n['id']:i for i,n in enumerate(nodes)}
    coordinates=[n['coordinates'] for n in nodes]
    matrix=OSRMRoutingAdapter().matrix(coordinates) if routing=='osrm' else estimated_matrix(coordinates)
    durations=matrix['payload']['durations'];distances=matrix['payload'].get('distances')
    travel_time_fallback=bool(matrix.get('fallback',False));distance_fallback=travel_time_fallback or distances is None
    if distances is None:distances=estimated_matrix(coordinates)['payload']['distances']
    # Missing/unreachable OD cells remain forbidden arcs; never replace with zero.
    horizon=int(max_route_hours*3600);unreachable=horizon+86400
    travel=[[int(math.ceil(v)) if v is not None and math.isfinite(v) and v>=0 else unreachable for v in row] for row in durations]
    meters=[[int(math.ceil(v)) if v is not None and math.isfinite(v) and v>=0 else 100000000 for v in row] for row in distances]
    starts=[byid[t['origin_id']] for t in trucks];manager=pywrapcp.RoutingIndexManager(len(nodes),len(trucks),starts,starts);model=pywrapcp.RoutingModel(manager)
    stop_index={byid[s['id']] for s in stops};service_seconds=600
    transit=model.RegisterTransitCallback(lambda a,b:travel[manager.IndexToNode(a)][manager.IndexToNode(b)]+(service_seconds if manager.IndexToNode(a) in stop_index else 0))
    cost_cb=model.RegisterTransitCallback(lambda a,b:meters[manager.IndexToNode(a)][manager.IndexToNode(b)])
    model.SetArcCostEvaluatorOfAllVehicles(cost_cb)
    model.AddDimension(transit,0,horizon,False,'Time');time_dim=model.GetDimensionOrDie('Time')
    demand=model.RegisterUnaryTransitCallback(lambda i:int(nodes[manager.IndexToNode(i)].get('demand_kg',0)))
    model.AddDimensionWithVehicleCapacity(demand,0,[int(t['capacity_kg']) for t in trucks],True,'Load');loads=model.GetDimensionOrDie('Load')
    solver=model.solver()
    for v,t in enumerate(trucks):
        time_dim.CumulVar(model.Start(v)).SetRange(min(horizon,int(delay_minutes*60)),min(horizon,int(delay_minutes*60)))
        if not t.get('eligible',True) or not t.get('refrigerated',False):solver.Add(model.NextVar(model.Start(v))==model.End(v))
        model.SetFixedCostOfVehicle(15000,v)
    for origin in origins:
        solver.Add(sum(loads.CumulVar(model.End(v)) for v,t in enumerate(trucks) if t['origin_id']==origin['id'])<=int(origin.get('inventory_kg',0)))
    for stop in stops:
        index=manager.NodeToIndex(byid[stop['id']]);deadline=min(horizon,int(stop.get('deadline_hours',max_route_hours)*3600),int(stop.get('shelf_life_hours',max_route_hours)*3600))
        time_dim.CumulVar(index).SetRange(0,max(0,deadline-service_seconds))
        model.AddDisjunction([index],100000000)
        if deadline<service_seconds or stop.get('held') or stop.get('recalled') or not stop.get('eligible',True):solver.Add(model.ActiveVar(index)==0)
    search=pywrapcp.DefaultRoutingSearchParameters();search.first_solution_strategy=routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    # Fixed descent strategy gives reproducible plans, unlike a wall-clock metaheuristic.
    search.local_search_metaheuristic=routing_enums_pb2.LocalSearchMetaheuristic.GREEDY_DESCENT;search.time_limit.seconds=3
    solution=model.SolveWithParameters(search)
    status={0:'NOT_SOLVED',1:'FEASIBLE',2:'PARTIAL_SUCCESS',3:'INFEASIBLE',4:'TIME_LIMIT',5:'INVALID',6:'INFEASIBLE',7:'OPTIMAL'}.get(model.status(),str(model.status()))
    routes=[];served=set();violations=[];modot_path=ROOT/'data/cache/probe_modot.json'
    if not modot_path.exists():modot_path=ROOT/'data/fixtures/modot.json'
    modot=json.loads(modot_path.read_text(encoding='utf-8')) if modot_path.exists() else None
    for v,t in enumerate(trucks):
        if not solution:break
        index=model.Start(v);order=[manager.IndexToNode(index)];arrivals=[]
        while not model.IsEnd(index):
            index=solution.Value(model.NextVar(index));n=manager.IndexToNode(index);order.append(n)
            if n in stop_index:
                served.add(nodes[n]['id']);arrivals.append({'stop_id':nodes[n]['id'],'arrival_minutes':round(solution.Value(time_dim.CumulVar(index))/60,2),'service_minutes':10})
        if not arrivals:continue
        load=sum(nodes[i].get('demand_kg',0) for i in order);path=[coordinates[i] for i in order]
        duration=solution.Value(time_dim.CumulVar(model.End(v)));travel_distance=sum(meters[a][b] for a,b in zip(order,order[1:]))
        geometry_result=OSRMRoutingAdapter().route(path) if routing=='osrm' else {'fallback':True,'provenance':matrix['provenance'],'payload':{'routes':[{'distance':travel_distance,'duration':sum(travel[a][b] for a,b in zip(order,order[1:])),'geometry':{'type':'LineString','coordinates':path}}]}}
        geometry=geometry_result['payload']['routes'][0]
        if load>t['capacity_kg'] or duration>horizon:violations.append(t['id'])
        chain=project_temperature(duration/60,ambient_c=ambient_temperature_c,refrigeration_fault=refrigeration_fault)
        road_review=review_routes(geometry_result,modot)
        geometry_fallback=bool(geometry_result.get('fallback',False))
        routes.append({'truck_id':t['id'],'origin_id':t['origin_id'],'stop_ids':[a['stop_id'] for a in arrivals],'arrivals':arrivals,'distance_m':travel_distance,'duration_seconds':duration,'driving_seconds':sum(travel[a][b] for a,b in zip(order,order[1:])),'load_kg':load,'capacity_kg':t['capacity_kg'],'geometry':geometry['geometry'],'geometry_distance_m':geometry['distance'],'geometry_duration_seconds':geometry['duration'],'travel_time_fallback':travel_time_fallback,'distance_fallback':distance_fallback,'geometry_fallback':geometry_fallback,'fallback':travel_time_fallback or distance_fallback or geometry_fallback,'routing_provenance':geometry_result.get('provenance','OSRM driving geometry'),'matrix_provenance':matrix.get('provenance','OSRM OD matrix'),'cold_chain':chain,'road_review':road_review})
    unserved=[s['id'] for s in stops if s['id'] not in served]
    return {'preset':data,'routes':routes,'solver_status':status,'feasible':solution is not None,'matrix_fallback':matrix.get('fallback',False),'matrix_provenance':matrix.get('provenance','OSRM OD matrix'),'summary':{'total_distance_m':sum(r['distance_m'] for r in routes),'total_duration_seconds':sum(r['duration_seconds'] for r in routes),'total_cost':round(sum(50+r['distance_m']/1000*1.4 for r in routes),2),'unserved_stops':unserved,'unmet_demand_kg':sum(s['demand_kg'] for s in stops if s['id'] in unserved),'constraint_violations':len(violations),'review_routes':sum(r['cold_chain']['status']=='review' or any(a['review_required'] for a in r['road_review']['alternatives']) for r in routes)},'simulation':True,'mutates_assignments':False,'provenance':data.get('provenance','Deterministic simulated operational preset; OR-Tools capacitated multi-depot routes with service times, return to origin, inventory and deadline constraints'),'assumptions':{'max_route_hours':max_route_hours,'delay_minutes':delay_minutes,'ambient_temperature_c':ambient_temperature_c,'service_minutes':10},'limitations':['Route laboratory does not dispatch or modify approved assignments','Heuristic feasible route plan; no claim of global optimality unless solver status is OPTIMAL','Cargo-temperature projections are uncalibrated scenario calculations, not predicted failure probabilities','MoDOT geometry proximity is an independent review layer, not closure-aware routing','OSRM ordinary driving profile does not validate commercial-truck restrictions','Forecast ambient inputs are user-specified scenario assumptions here, not measured cargo temperature','All inventory is interchangeable within each simulated origin; no real supply contracts are implied']+data.get('limitations',[])}
