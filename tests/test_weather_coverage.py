import pytest
from backend.weather_coverage import profile_station,coverage_report,requested_dates

STATION={'city':'Columbia','station_id':'USW00003945','coordinates':[-92.3341,38.9517]}
def observation(day='2025-01-01',**kwargs):
    return {'DATE':day,'STATION':STATION['station_id'],'NAME':'Official station','LATITUDE':'38.81704','LONGITUDE':'-92.21475','TMAX':'4.4','TMAX_ATTRIBUTES':',,W','TMIN':'-3.2','TMIN_ATTRIBUTES':',,W','PRCP':'0.0','PRCP_ATTRIBUTES':',,W,2400',**kwargs}

def test_weather_keeps_metric_units_and_original_reporting_period():
    result=profile_station([observation()],STATION,'2025-01-01','2025-01-01','2026-10-26T06:00:00+00:00')
    assert result['status']=='complete bounded extract'
    assert result['metric_coverage']['TMAX']['units']=='degrees C'
    assert result['metric_coverage']['PRCP']['units']=='mm'
    assert result['date_start']=='2025-01-01'
    assert 'Not converted to local midnight' in result['original_date_semantics']

def test_missing_precipitation_is_not_invented_from_present_date_row():
    station=profile_station([observation(PRCP=None)],STATION,'2025-01-01','2025-01-01','2026-10-26T06:00:00+00:00')
    report=coverage_report([station],'2025-01-01','2025-01-01')
    assert report['coverage_fraction']==1
    assert report['metric_coverage_fraction']==pytest.approx(2/3)
    assert report['missing_metric_values']==1 and report['status']=='partial'

def test_flagged_numeric_observation_is_not_quality_passed():
    station=profile_station([observation(TMAX_ATTRIBUTES=',X,W')],STATION,'2025-01-01','2025-01-01','2026-10-26T06:00:00+00:00')
    assert station['metric_coverage']['TMAX']['numeric_days']==1
    assert station['metric_coverage']['TMAX']['quality_pass_days']==0
    assert station['metric_coverage']['TMAX']['flagged_days']==1
    assert station['status']=='partial'

def test_missing_attributes_are_unknown_quality_not_implicitly_good():
    station=profile_station([observation(TMAX_ATTRIBUTES=None)],STATION,'2025-01-01','2025-01-01','2026-10-26T06:00:00+00:00')
    assert station['metric_coverage']['TMAX']['quality_unknown_days']==1
    assert station['metric_coverage']['TMAX']['quality_pass_days']==0

@pytest.mark.parametrize('rows,match',[
    ([observation(),observation()],'Duplicate'),
    ([observation(STATION='wrong')],'identity mismatch'),
    ([observation(LONGITUDE='-120')],'60 km'),
    ([observation(day='2024-12-31')],'outside'),
    ([observation(day='not a date')],'Unexpected'),
    ([], 'no observation'),
])
def test_weather_rejects_unverifiable_rows(rows,match):
    with pytest.raises(ValueError,match=match):profile_station(rows,STATION,'2025-01-01','2025-01-01','2026-10-26T06:00:00+00:00')

def test_weather_does_not_fill_a_missing_day():
    station=profile_station([observation()],STATION,'2025-01-01','2025-01-02','2026-10-26T06:00:00+00:00')
    assert station['missing_days']==1 and station['missing_date_sample']==['2025-01-02']
    assert station['metric_coverage']['TMAX']['missing_days']==1

def test_acquisition_bound_and_order_are_enforced():
    with pytest.raises(ValueError):requested_dates('2025-02-01','2025-01-01')
    with pytest.raises(ValueError):requested_dates('2020-01-01','2026-06-30')
