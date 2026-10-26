import random
from backend.adapters import distance

SEED=20261026
def seed_network(seed=SEED):
    rng=random.Random(seed)
    cities=[('Columbia',-92.3341,38.9517),('Kansas City',-94.5786,39.0997),('Jefferson City',-92.1735,38.5767),('Springfield',-93.2923,37.2090),('St. Louis',-90.1994,38.6270)]
    nodes=[{'id':'DC1','name':'Columbia DC (simulated)','kind':'dc','coordinates':[-92.3341,38.9517],'capacity_kg':12000},{'id':'DC2','name':'Springfield DC (simulated)','kind':'dc','coordinates':[-93.2923,37.2090],'capacity_kg':10000}]
    for i,(name,x,y) in enumerate(cities[:3]): nodes.append({'id':f'SUP{i+1}','name':name+' supplier (simulated)','kind':'supplier','coordinates':[x-.08,y+.06],'capacity_kg':6000})
    for i in range(15):
        name,x,y=cities[i%5]; nodes.append({'id':f'D{i+1:02}','name':f'{name} destination {i+1} (simulated)','kind':'destination','coordinates':[x+rng.uniform(-.12,.12),y+rng.uniform(-.09,.09)],'demand_kg':500})
    trucks=[{'id':f'T{i+1:02}','capacity_kg':1500,'refrigerated':True,'eligible':True} for i in range(8)]
    lots=[{'id':f'L{i+1:02}','supplier_id':f'SUP{i%3+1}','inventory_kg':1500,'held':i==0,'recalled':False,'eligible':True,'shelf_life_hours':72} for i in range(12)]
    shipments=[]
    for i in range(24):
        dest=nodes[5+i%15]; origin=nodes[i%2]; meters=distance(origin['coordinates'],dest['coordinates'])*1.25
        shipments.append({'id':f'SH{i+1:02}','origin':origin['id'],'destination':dest['id'],'lot_id':lots[i%12]['id'],'truck_id':trucks[i%8]['id'],'quantity_kg':400,'deadline_hours':6,'estimated_hours':round(meters/65000,3),'estimated_distance_km':round(meters/1000,2),'routing_provenance':'haversine x 1.25 at 65 km/h; not road geometry','temperature_c':8.5 if i in (2,7) else round(rng.uniform(1,3.8),1),'review_priority':'high' if i in (2,7) else 'routine','status':'pending dispatcher approval'})
    telemetry=[{'shipment_id':s['id'],'timestamp':f'2026-10-26T{8+j//6:02}:{j%6*10:02}:00-05:00','temperature_c':s['temperature_c'] if j>6 else 2.5,'provenance':'simulated cargo temperature'} for s in shipments for j in range(12)]
    return {'seed':seed,'provenance':'DETERMINISTIC SIMULATION — entities, contracts, shipments and telemetry are fictional','nodes':nodes,'trucks':trucks,'lots':lots,'shipments':shipments,'telemetry':telemetry,'events':[]}

EVENTS={'road_closure','severe_weather','delivery_delay','refrigeration_fault','temperature_excursion','inventory_shortage'}
def apply_event(network,event,shipment_id):
    if event not in EVENTS: raise ValueError('Unsupported event; verified recall requires real traceability and is not simulated as official')
    s=next((s for s in network['shipments'] if s['id']==shipment_id),None)
    if not s: raise ValueError('Unknown shipment')
    if event in {'road_closure','severe_weather','delivery_delay'}: s['estimated_hours']+=2
    if event in {'refrigeration_fault','temperature_excursion'}: s['temperature_c']=9; s['review_priority']='high'
    if event=='refrigeration_fault': next(t for t in network['trucks'] if t['id']==s['truck_id'])['eligible']=False
    if event=='inventory_shortage': next(l for l in network['lots'] if l['id']==s['lot_id'])['inventory_kg']=0
    network['events'].append({'type':event,'shipment_id':shipment_id,'provenance':'simulated operational event'})
    return network
