"""Explainable cargo-temperature scenario projection; no learned failure probability."""
import math

def project_temperature(duration_minutes, initial_c=2.5, ambient_c=30, refrigeration_fault=False, threshold_c=4):
    if not all(math.isfinite(float(v)) for v in [duration_minutes,initial_c,ambient_c,threshold_c]) or not 0<=duration_minutes<=1440:
        raise ValueError('Finite values and a projection horizon of 0–1440 minutes required')
    # Assumed lumped first-order response. These coefficients have not been calibrated.
    equilibrium=ambient_c if refrigeration_fault else 2+max(0,ambient_c-30)*.03
    tau=120 if refrigeration_fault else 20
    def temperature(t,eq=equilibrium,response=tau):return eq+(initial_c-eq)*math.exp(-t/response)
    times=list(range(0,int(duration_minutes)+1,10))
    if not times or times[-1]!=duration_minutes:times.append(duration_minutes)
    points=[]
    for t in times:
        variants=[temperature(t,equilibrium+offset,tau*factor) for offset in (-3,3) for factor in (.75,1.25)] if refrigeration_fault else [temperature(t,equilibrium+offset,tau*factor) for offset in (-.5,.5) for factor in (.75,1.25)]
        points.append({'elapsed_minutes':round(t,2),'temperature_c':round(temperature(t),3),'lower_c':round(min(variants+[temperature(t)]),3),'upper_c':round(max(variants+[temperature(t)]),3)})
    if initial_c>threshold_c and equilibrium>=threshold_c:above=duration_minutes
    elif initial_c<=threshold_c and equilibrium<=threshold_c:above=0
    elif equilibrium==initial_c:above=duration_minutes if initial_c>threshold_c else 0
    else:
        crossing=-tau*math.log((threshold_c-equilibrium)/(initial_c-equilibrium))
        above=max(0,duration_minutes-crossing) if equilibrium>threshold_c else min(duration_minutes,crossing)
    maximum=max(initial_c,temperature(duration_minutes))
    return {'status':'review' if maximum>threshold_c else 'within_assumed_target','max_temperature_c':round(maximum,3),'time_above_threshold_minutes':round(above,2),'threshold_c':threshold_c,'projection':points,'refrigeration_fault':refrigeration_fault,'ambient_temperature_c':ambient_c,'provenance':'simulated cargo-temperature scenario projection; not observed sensor data or a validated failure-risk model','assumptions':['First-order thermal response; fault time constant 120 minutes, normal control 20 minutes','Normal assumed control equilibrium 2°C, with a small uncalibrated ambient penalty above 30°C','4°C is a conservative demonstration review threshold, not a lot disposition rule','Bands are parameter-sensitivity ranges, not statistical confidence intervals','No pathogen growth, consumer illness probability or automatic hold decision']}
