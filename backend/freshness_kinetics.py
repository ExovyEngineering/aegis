"""Illustrative, temperature-dependent quality budgeting; never safety clearance.

The generic Q10 relationship is integrated over explicitly held temperature
samples. No coefficients here were fitted to AEGIS poultry, packaging or sensors.
"""
from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import datetime, timezone
import math


MODEL_VERSION = 'q10-equivalent-age-quality-v1'
MAX_READINGS = 4096
MAX_HISTORY_HOURS = 366 * 24
DEFAULT_PROFILE = {
    'reference_temperature_c': 4.0,
    'reference_life_hours': 240.0,
    'initial_equivalent_age_hours': 0.0,
    'q10': 2.0,
    'q10_low': 1.5,
    'q10_high': 3.0,
    'forecast_temperature_c': 4.0,
    'max_gap_minutes': 120.0,
    'minimum_temperature_c': 0.0,
    'maximum_temperature_c': 30.0,
    'temperature_basis': 'product',
    'calibration_status': 'illustrative_unvalidated',
}
CHANNEL_BOUNDS = {
    'temperature_c': (-80, 80),
    'ambient_temperature_c': (-80, 80),
    'humidity_percent': (0, 100),
    'vibration_g': (0, 100),
    'ethylene_ppm': (0, 1_000_000),
}
UNMODELED_CHANNELS = ('ambient_temperature_c', 'humidity_percent', 'vibration_g', 'ethylene_ppm')
SOURCES = (
    {'label': 'Q10 and empirical food-quality temperature models',
     'url': 'https://academic.oup.com/fst/article/32/1/38/7818609'},
    {'label': 'Product-specific dynamic packaged-chicken quality research',
     'url': 'https://doi.org/10.3382/ps/pez461'},
    {'label': 'USDA distinction between spoilage and pathogenic bacteria',
     'url': 'https://ask.fsis.usda.gov/article/Can-bacteria-grow-in-the-refrigerator'},
    {'label': 'Commodity-specific humidity and ethylene response example',
     'url': 'https://postharvest.ucdavis.edu/produce-facts-sheets/grape'},
)
LIMITATIONS = (
    'This is an illustrative quality-budget calculation, not a measured molecular freshness, spoilage rate, pathogen-growth or consumer-illness model.',
    'Q10, initial equivalent age, reference life and temperature domain are chosen assumptions; AEGIS has no calibrated production poultry quality profile.',
    'A 240-hour demonstration budget is not a recommended poultry storage life or a validated label date.',
    'The future clock assumes the selected future product temperature persists. It is not an observed future temperature or weather forecast.',
    'Product/packaging, initial microbial load and other quality mechanisms need product-specific validation before operational use.',
    'Each interval uses its preceding temperature observation as an explicit piecewise-constant assumption; unobserved spikes remain possible.',
    'Missing coverage, duplicate/out-of-order times, missing product temperature or temperatures outside the chosen model domain abstain from a remaining-life estimate.',
    'Humidity, vibration, ambient temperature and ethylene are retained contextual channels. No unsupported poultry decay coefficients or ambient-to-core conversion are applied.',
    'Sensitivity limits compare chosen Q10 parameters; they are not confidence intervals, guaranteed bounds or validation evidence.',
    'Cooling does not restore consumed reference-equivalent budget. A changed future temperature assumption can change the forward clock.',
    'This quality estimate cannot extend a manufacturer use-by date, override a hold/recall or replace a qualified food-safety/disposition review.',
)


def _number(value, name, low, high):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{name} must be a finite number from {low} through {high}')
    return float(value)


def _time(value, name):
    original = value.isoformat() if isinstance(value, datetime) else value
    if not isinstance(original, str) or not original.strip() or len(original) > 80:
        raise ValueError(f'{name} requires an explicit timezone-aware ISO timestamp')
    try:
        parsed = datetime.fromisoformat(original.replace('Z', '+00:00'))
    except ValueError as error:
        raise ValueError(f'{name} requires an explicit timezone-aware ISO timestamp') from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f'{name} requires an explicit timezone-aware ISO timestamp')
    return parsed.astimezone(timezone.utc), original


def normalize_profile(profile):
    """Validate declared assumptions without inventing a quality-clock start."""
    if not isinstance(profile, Mapping):
        raise ValueError('profile must be an object containing started_at')
    allowed = set(DEFAULT_PROFILE) | {'started_at', 'profile_id', 'product_category'}
    extra = set(profile) - allowed
    if extra:
        raise ValueError('Unsupported profile fields: ' + ', '.join(sorted(map(str, extra))))
    if 'started_at' not in profile:
        raise ValueError('started_at must explicitly identify the quality-budget baseline')
    _, original_start = _time(profile['started_at'], 'started_at')
    result = {**DEFAULT_PROFILE, **dict(profile), 'started_at': original_start}
    result['reference_temperature_c'] = _number(result['reference_temperature_c'], 'reference_temperature_c', -40, 60)
    result['reference_life_hours'] = _number(result['reference_life_hours'], 'reference_life_hours', 0.01, MAX_HISTORY_HOURS)
    result['initial_equivalent_age_hours'] = _number(result['initial_equivalent_age_hours'], 'initial_equivalent_age_hours', 0, 1_000_000)
    for field in ('q10', 'q10_low', 'q10_high'):
        result[field] = _number(result[field], field, 1, 10)
    if not result['q10_low'] <= result['q10'] <= result['q10_high']:
        raise ValueError('q10_low <= q10 <= q10_high is required')
    result['forecast_temperature_c'] = _number(result['forecast_temperature_c'], 'forecast_temperature_c', -80, 80)
    result['max_gap_minutes'] = _number(result['max_gap_minutes'], 'max_gap_minutes', 0.01, 1440)
    result['minimum_temperature_c'] = _number(result['minimum_temperature_c'], 'minimum_temperature_c', -40, 60)
    result['maximum_temperature_c'] = _number(result['maximum_temperature_c'], 'maximum_temperature_c', -40, 60)
    if not result['minimum_temperature_c'] <= result['reference_temperature_c'] <= result['maximum_temperature_c']:
        raise ValueError('The reference temperature must lie within the chosen model domain')
    if result['minimum_temperature_c'] >= result['maximum_temperature_c']:
        raise ValueError('The model temperature domain must have positive width')
    if result['temperature_basis'] not in ('product', 'container_air_proxy'):
        raise ValueError('temperature_basis must be product or container_air_proxy')
    if result['calibration_status'] != 'illustrative_unvalidated':
        raise ValueError('No calibrated production profile is implemented; use illustrative_unvalidated')
    for field in ('profile_id', 'product_category'):
        if field in result and (not isinstance(result[field], str) or not 1 <= len(result[field].strip()) <= 200):
            raise ValueError(f'{field} requires 1–200 text characters')
    return result


def relative_decay_rate(temperature_c, reference_temperature_c=4, q10=2):
    """Reference-equivalent quality-hours consumed per elapsed hour."""
    temperature = _number(temperature_c, 'temperature_c', -80, 80)
    reference = _number(reference_temperature_c, 'reference_temperature_c', -40, 60)
    coefficient = _number(q10, 'q10', 1, 10)
    return coefficient ** ((temperature - reference) / 10)


def evaluate_freshness(readings, profile, evaluation_at):
    """Pure quality projection over declared, fully covered observation history.

    Missing/unsupported coverage returns status=unscored and null remaining-life
    fields. Malformed types/units raise ValueError; inputs are never mutated.
    """
    parameters = normalize_profile(profile)
    start, _ = _time(parameters['started_at'], 'started_at')
    evaluation, original_evaluation = _time(evaluation_at, 'evaluation_at')
    if evaluation < start:
        raise ValueError('evaluation_at cannot precede started_at')
    if not isinstance(readings, Sequence) or isinstance(readings, (str, bytes)) or len(readings) > MAX_READINGS:
        raise ValueError(f'readings must be a sequence with at most {MAX_READINGS} observations')
    observations = []
    for index, source in enumerate(readings):
        if not isinstance(source, Mapping):
            raise ValueError(f'readings[{index}] must be an object')
        observed, original = _time(source.get('observed_at'), f'readings[{index}].observed_at')
        channels = {}
        for field, bounds in CHANNEL_BOUNDS.items():
            value = source.get(field)
            channels[field] = None if value is None else _number(value, f'readings[{index}].{field}', *bounds)
        source_kind = source.get('source_kind', source.get('provenance', 'unidentified'))
        if not isinstance(source_kind, str) or not 1 <= len(source_kind.strip()) <= 300:
            raise ValueError(f'readings[{index}].source_kind/provenance requires 1–300 text characters')
        observations.append({'time': observed, 'observed_at': original, 'channels': channels,
                             'source_kind': source_kind})
    issues = []
    def issue(code, description, **details):
        issues.append({'code': code, 'description': description, **details})
    window = (evaluation - start).total_seconds() / 3600
    if window > MAX_HISTORY_HOURS:
        issue('history_bound', 'The history window exceeds the bounded demonstration horizon')
    if not observations:
        issue('missing_observations', 'No product-temperature observations cover the quality-budget baseline')
    elif observations[0]['time'] != start:
        issue('baseline_not_covered', 'The first observation must match the explicit quality-budget baseline; no missing age or temperature is invented')
    ordered = True
    for index, observation in enumerate(observations):
        if observation['time'] < start or observation['time'] > evaluation:
            issue('outside_evaluation_window', 'An observation lies outside the declared evaluation window', observation_index=index)
        if index and observation['time'] <= observations[index-1]['time']:
            ordered = False
            issue('nonunique_or_out_of_order', 'Observation timestamps must be strictly increasing; the engine does not silently sort or deduplicate', observation_index=index)
        temperature = observation['channels']['temperature_c']
        if temperature is None:
            issue('missing_product_temperature', 'Ambient or other channels do not substitute for the modeled product-temperature channel', observation_index=index)
        elif not parameters['minimum_temperature_c'] <= temperature <= parameters['maximum_temperature_c']:
            issue('temperature_outside_domain', 'Observed temperature lies outside the explicitly chosen illustrative model domain', observation_index=index)
    if not parameters['minimum_temperature_c'] <= parameters['forecast_temperature_c'] <= parameters['maximum_temperature_c']:
        issue('forecast_outside_domain', 'The chosen future product-temperature assumption is outside the model domain')
    intervals = []
    covered = 0.0
    largest_hold = 0.0
    partial_age = parameters['initial_equivalent_age_hours']
    timeline = []
    cumulative_known = not issues
    if ordered:
        for index, observation in enumerate(observations):
            end = observations[index+1]['time'] if index+1 < len(observations) else evaluation
            duration = (end - observation['time']).total_seconds() / 3600
            temperature = observation['channels']['temperature_c']
            if duration < 0 or observation['time'] < start or end > evaluation:
                continue
            largest_hold = max(largest_hold, duration * 60)
            supported = temperature is not None and parameters['minimum_temperature_c'] <= temperature <= parameters['maximum_temperature_c']
            if duration * 60 > parameters['max_gap_minutes'] + 1e-9:
                issue('coverage_gap', 'The preceding temperature cannot be held beyond max_gap_minutes', observation_index=index, duration_minutes=round(duration*60, 9))
                supported = False
            if supported:
                rate = relative_decay_rate(temperature, parameters['reference_temperature_c'], parameters['q10'])
                increment = duration * rate
                partial_age += increment
                covered += duration
                intervals.append((duration, temperature))
            else:
                rate = increment = None
                cumulative_known = False
            timeline.append({'start_at': observation['observed_at'], 'end_at': end.isoformat(),
                             'source_observed_at': observation['observed_at'], 'duration_hours': duration,
                             'temperature_c': temperature, 'channels': deepcopy(observation['channels']),
                             'rate_multiplier': rate, 'equivalent_age_increment_hours': increment,
                             'cumulative_equivalent_age_hours': partial_age if cumulative_known else None,
                             'remaining_reference_hours': max(0.0, parameters['reference_life_hours']-partial_age) if cumulative_known else None,
                             'integration': 'left-hold assumption' if supported else 'unscored interval',
                             'end_is_observation': index+1 < len(observations)})
    scored = not issues
    age = parameters['initial_equivalent_age_hours'] + math.fsum(duration * relative_decay_rate(temperature, parameters['reference_temperature_c'], parameters['q10']) for duration, temperature in intervals) if scored else None
    remaining_reference = max(0.0, parameters['reference_life_hours']-age) if scored else None
    forecast_rate = relative_decay_rate(parameters['forecast_temperature_c'], parameters['reference_temperature_c'], parameters['q10'])
    remaining_future = remaining_reference / forecast_rate if scored else None
    sensitivity = {'kind': 'chosen-parameter sensitivity; not a confidence interval or guaranteed bound',
                   'q10_values': sorted(set([parameters['q10_low'], parameters['q10'], parameters['q10_high']])),
                   'cases': [], 'remaining_reference_hours': {'lower': None, 'upper': None},
                   'remaining_hours_at_forecast_temperature': {'lower': None, 'upper': None}}
    if scored:
        for coefficient in sensitivity['q10_values']:
            case_age = parameters['initial_equivalent_age_hours'] + math.fsum(duration * relative_decay_rate(temperature, parameters['reference_temperature_c'], coefficient) for duration, temperature in intervals)
            reference_left = max(0.0, parameters['reference_life_hours']-case_age)
            projected_left = reference_left / relative_decay_rate(parameters['forecast_temperature_c'], parameters['reference_temperature_c'], coefficient)
            sensitivity['cases'].append({'q10': coefficient, 'equivalent_age_hours': case_age,
                                         'remaining_reference_hours': reference_left,
                                         'remaining_hours_at_forecast_temperature': projected_left})
        for field in ('remaining_reference_hours', 'remaining_hours_at_forecast_temperature'):
            values = [case[field] for case in sensitivity['cases']]
            sensitivity[field] = {'lower': min(values), 'upper': max(values)}
    warnings = [item['description'] for item in issues]
    if parameters['temperature_basis'] == 'container_air_proxy':
        warnings.append('Container-air temperature is an explicitly declared proxy; product/core temperature is not established')
    source_kinds = sorted({observation['source_kind'] for observation in observations})
    return {'model_version': MODEL_VERSION, 'model_kind': 'deterministic Q10 equivalent-age quality projection',
            'status': 'estimated' if scored else 'unscored', 'quality_only': True, 'validated': False,
            'safety_assessment': 'not performed', 'profile': parameters, 'evaluation_at': original_evaluation,
            'remaining_reference_hours': remaining_reference, 'remaining_hours_at_forecast_temperature': remaining_future,
            'remaining_quality_hours': sensitivity['remaining_hours_at_forecast_temperature']['lower'],
            'equivalent_age_hours': age, 'known_equivalent_age_hours': partial_age,
            'consumed_fraction': min(1.0, age/parameters['reference_life_hours']) if scored else None,
            'rate_multiplier_at_forecast_temperature': forecast_rate,
            'timeline': timeline, 'sensitivity': sensitivity,
            'coverage': {'complete_under_hold_assumption': not any(item['code'] != 'forecast_outside_domain' for item in issues), 'readings_count': len(observations),
                         'window_hours': window, 'covered_hours': min(window, covered),
                         'uncovered_hours': max(0.0, window-covered), 'largest_hold_minutes': largest_hold,
                         'max_gap_minutes': parameters['max_gap_minutes'], 'issues': issues},
            'context_channels': {field: [observation['channels'][field] for observation in observations] for field in UNMODELED_CHANNELS},
            'units': {'temperature': 'degrees Celsius', 'time': 'hours', 'humidity': 'percent RH',
                      'vibration': 'g as declared by the gateway; sensor measurement definition unverified', 'ethylene': 'ppm'},
            'provenance': {'temperature_basis': parameters['temperature_basis'], 'source_kinds': source_kinds,
                           'parameters': 'declared illustrative assumptions, not fitted poultry coefficients',
                           'integration': 'piecewise-constant preceding observation; bounded max gap',
                           'remaining_quality_hours': 'minimum forward life among explicitly chosen Q10 cases, not a statistical lower confidence bound'},
            'warnings': list(dict.fromkeys(warnings)), 'limitations': list(LIMITATIONS), 'sources': deepcopy(list(SOURCES))}
