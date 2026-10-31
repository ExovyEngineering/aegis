"""Analytical quality-budget identities and fail-closed sensor history checks."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import math

import pytest

from backend.freshness_kinetics import (
    DEFAULT_PROFILE, MAX_READINGS, MODEL_VERSION,
    evaluate_freshness, normalize_profile, relative_decay_rate,
)


START = datetime(2026, 10, 30, 8, tzinfo=timezone(timedelta(hours=-5)))


def at(hours=0):
    return (START + timedelta(hours=hours)).isoformat()


def profile(**changes):
    return {'started_at': at(), **changes}


def reading(hours=0, temperature=4, **channels):
    return {'observed_at': at(hours), 'temperature_c': temperature,
            'source_kind': 'simulated product temperature', **channels}


def codes(result):
    return {item['code'] for item in result['coverage']['issues']}


def test_q10_has_reference_units_and_analytical_ten_degree_ratio():
    assert relative_decay_rate(4) == 1
    assert relative_decay_rate(14) == 2
    assert relative_decay_rate(-6) == .5
    assert relative_decay_rate(24, 4, 3) == 9


def test_reference_hour_consumes_exactly_one_budget_hour_without_changing_inputs():
    samples = [reading(), reading(1)]
    assumptions = profile(initial_equivalent_age_hours=230)
    before = deepcopy((samples, assumptions))
    result = evaluate_freshness(samples, assumptions, at(1))
    assert (samples, assumptions) == before
    assert result['status'] == 'estimated'
    assert result['equivalent_age_hours'] == 231
    assert result['remaining_reference_hours'] == result['remaining_hours_at_forecast_temperature'] == 9
    assert result['remaining_quality_hours'] == 9
    assert result['coverage']['window_hours'] == result['coverage']['covered_hours'] == 1
    assert result['model_version'] == MODEL_VERSION
    assert result['quality_only'] and not result['validated']
    assert result['safety_assessment'] == 'not performed'


def test_declared_heat_replay_changes_clock_by_actual_exposure_and_exposes_broad_sensitivity():
    # Parent demo: a one-minute explicit transition avoids overwriting a prior
    # reading. Two hours at16°C consume 2*2**1.2 reference-equivalent hours.
    samples = [reading(), reading(1), reading(1+1/60, 16), reading(3+1/60)]
    result = evaluate_freshness(samples, profile(initial_equivalent_age_hours=230), at(3+1/60))
    expected = 240 - (230 + 1 + 1/60 + 2 * 2**1.2)
    conservative = 240 - (230 + 1 + 1/60 + 2 * 3**1.2)
    assert result['remaining_reference_hours'] == pytest.approx(expected)
    assert result['remaining_quality_hours'] == pytest.approx(conservative)
    assert 4 < result['remaining_hours_at_forecast_temperature'] < 4.5
    assert 1 < result['remaining_quality_hours'] < 2
    assert result['sensitivity']['q10_values'] == [1.5, 2, 3]
    assert 'not a confidence interval' in result['sensitivity']['kind']
    assert result['coverage']['largest_hold_minutes'] == 120


def test_new_warm_reading_does_not_retroactively_change_previous_exposure():
    cold = evaluate_freshness([reading(), reading(1)], profile(), at(1))
    warmed = evaluate_freshness([reading(), reading(1, 24)], profile(), at(1))
    assert warmed['equivalent_age_hours'] == cold['equivalent_age_hours'] == 1
    later = evaluate_freshness([reading(), reading(1, 24)], profile(), at(2))
    assert later['equivalent_age_hours'] == 5


def test_cooling_does_not_restore_consumed_budget():
    samples = [reading(0, 24), reading(1, 4)]
    warm = evaluate_freshness(samples, profile(), at(1))
    cooled = evaluate_freshness([*samples, reading(2, 4)], profile(), at(2))
    assert warm['equivalent_age_hours'] == 4
    assert cooled['equivalent_age_hours'] == 5
    assert cooled['remaining_reference_hours'] < warm['remaining_reference_hours']
    ages = [row['cumulative_equivalent_age_hours'] for row in cooled['timeline']]
    assert ages == sorted(ages)


def test_future_temperature_changes_forward_clock_without_rewriting_exposure():
    samples = [reading(), reading(1)]
    cold = evaluate_freshness(samples, profile(forecast_temperature_c=4), at(1))
    warm = evaluate_freshness(samples, profile(forecast_temperature_c=14), at(1))
    assert cold['equivalent_age_hours'] == warm['equivalent_age_hours'] == 1
    assert cold['remaining_reference_hours'] == warm['remaining_reference_hours'] == 239
    assert warm['remaining_hours_at_forecast_temperature'] == cold['remaining_hours_at_forecast_temperature'] / 2
    assert cold['remaining_quality_hours'] == 239
    assert warm['remaining_quality_hours'] == pytest.approx(239/3)


def test_sensitivity_compares_cases_instead_of_assuming_high_q10_is_always_worst():
    result = evaluate_freshness([reading()], profile(forecast_temperature_c=0), at())
    cases = result['sensitivity']['cases']
    worst = min(cases, key=lambda case: case['remaining_hours_at_forecast_temperature'])
    assert worst['q10'] == 1.5
    assert result['remaining_quality_hours'] == worst['remaining_hours_at_forecast_temperature']
    assert result['sensitivity']['remaining_hours_at_forecast_temperature']['lower'] <= result['remaining_hours_at_forecast_temperature'] <= result['sensitivity']['remaining_hours_at_forecast_temperature']['upper']


def test_expired_budget_stays_zero_while_consumed_exposure_is_retained():
    result = evaluate_freshness([reading(0, 24), reading(1, 4)], profile(reference_life_hours=3), at(1))
    assert result['equivalent_age_hours'] == 4
    assert result['remaining_reference_hours'] == result['remaining_hours_at_forecast_temperature'] == 0
    assert result['remaining_quality_hours'] == 0
    assert result['consumed_fraction'] == 1
    aged = evaluate_freshness([reading()], profile(initial_equivalent_age_hours=300), at())
    assert aged['remaining_reference_hours'] == 0 and aged['equivalent_age_hours'] == 300


def test_equal_baseline_and_evaluation_requires_an_observation_but_no_elapsed_age():
    result = evaluate_freshness([reading()], profile(), at())
    assert result['status'] == 'estimated' and result['equivalent_age_hours'] == 0
    assert result['remaining_reference_hours'] == 240
    assert result['coverage']['window_hours'] == 0
    assert result['coverage']['complete_under_hold_assumption']


def test_different_timezone_offsets_integrate_absolute_time_and_preserve_source_timestamp():
    samples = [reading(), {'observed_at':'2026-10-30T08:00:00-06:00','temperature_c':4}]
    result = evaluate_freshness(samples, profile(), '2026-10-30T08:00:00-06:00')
    assert result['equivalent_age_hours'] == 1
    assert result['timeline'][0]['source_observed_at'] == at()
    assert result['evaluation_at'] == '2026-10-30T08:00:00-06:00'


def test_context_channels_are_retained_without_fabricated_poultry_decay_effects():
    base = evaluate_freshness([reading(), reading(1)], profile(), at(1))
    extreme = evaluate_freshness([reading(0, ambient_temperature_c=70, humidity_percent=100, vibration_g=99, ethylene_ppm=1000), reading(1, ambient_temperature_c=70, humidity_percent=0, vibration_g=0, ethylene_ppm=0)], profile(), at(1))
    assert extreme['equivalent_age_hours'] == base['equivalent_age_hours']
    assert extreme['remaining_quality_hours'] == base['remaining_quality_hours']
    assert extreme['context_channels']['ethylene_ppm'] == [1000, 0]
    assert extreme['context_channels']['humidity_percent'] == [100, 0]
    assert extreme['timeline'][0]['channels']['ambient_temperature_c'] == 70
    assert 'sensor measurement definition unverified' in extreme['units']['vibration']


def test_air_proxy_remains_explicit_and_is_never_inferred_from_ambient():
    result = evaluate_freshness([reading(), reading(1)], profile(temperature_basis='container_air_proxy'), at(1))
    assert result['provenance']['temperature_basis'] == 'container_air_proxy'
    assert any('product/core temperature is not established' in warning for warning in result['warnings'])
    missing = evaluate_freshness([reading(0, None, ambient_temperature_c=4)], profile(), at(1))
    assert missing['status'] == 'unscored'
    assert 'missing_product_temperature' in codes(missing)
    assert missing['remaining_quality_hours'] is None


@pytest.mark.parametrize('samples,evaluation,expected', [
    ([], at(1), 'missing_observations'),
    ([reading(1)], at(2), 'baseline_not_covered'),
    ([reading(), reading(0)], at(1), 'nonunique_or_out_of_order'),
    ([reading(), reading(1), reading(.5)], at(1), 'nonunique_or_out_of_order'),
    ([reading(), reading(2)], at(1), 'outside_evaluation_window'),
    ([reading(-1), reading()], at(1), 'outside_evaluation_window'),
    ([reading(0, None)], at(1), 'missing_product_temperature'),
    ([reading(0, -1)], at(1), 'temperature_outside_domain'),
    ([reading(0, 31)], at(1), 'temperature_outside_domain'),
    ([reading()], at(2+1/3600), 'coverage_gap'),
])
def test_incomplete_or_unsupported_history_abstains(samples, evaluation, expected):
    before = deepcopy(samples)
    result = evaluate_freshness(samples, profile(), evaluation)
    assert samples == before
    assert result['status'] == 'unscored' and expected in codes(result)
    assert result['equivalent_age_hours'] is None
    assert result['remaining_reference_hours'] is None
    assert result['remaining_hours_at_forecast_temperature'] is None
    assert result['remaining_quality_hours'] is None
    assert result['sensitivity']['cases'] == []


def test_exact_maximum_gap_is_supported_but_large_gap_is_not_filled():
    exact = evaluate_freshness([reading()], profile(), at(2))
    assert exact['equivalent_age_hours'] == 2
    gapped = evaluate_freshness([reading(), reading(3)], profile(), at(3))
    assert gapped['coverage']['covered_hours'] == 0
    assert gapped['coverage']['uncovered_hours'] == 3
    assert gapped['timeline'][0]['equivalent_age_increment_hours'] is None
    assert gapped['known_equivalent_age_hours'] == 0


def test_duplicate_instants_with_different_offsets_are_not_treated_as_two_samples():
    samples = [reading(), {'observed_at':'2026-10-30T13:00:00+00:00','temperature_c':5}]
    result = evaluate_freshness(samples, profile(), at(1))
    assert result['status'] == 'unscored' and 'nonunique_or_out_of_order' in codes(result)


def test_future_assumption_outside_domain_abstains_while_coverage_remains_explicit():
    result = evaluate_freshness([reading(), reading(1)], profile(forecast_temperature_c=40), at(1))
    assert result['status'] == 'unscored' and 'forecast_outside_domain' in codes(result)
    assert result['coverage']['complete_under_hold_assumption']
    assert result['remaining_quality_hours'] is None


@pytest.mark.parametrize('field,value', [
    ('temperature_c', float('nan')), ('temperature_c', float('inf')), ('temperature_c', True),
    ('temperature_c', '4'), ('temperature_c', 81), ('ambient_temperature_c', -81),
    ('humidity_percent', -1), ('humidity_percent', 101), ('vibration_g', -0.1),
    ('ethylene_ppm', -1), ('ethylene_ppm', 1_000_001),
    ('source_kind', True), ('source_kind', ''),
])
def test_malformed_channels_and_provenance_are_rejected(field, value):
    sample = reading(); sample[field] = value
    with pytest.raises(ValueError):
        evaluate_freshness([sample], profile(), at())


@pytest.mark.parametrize('changes', [
    {'reference_life_hours':0}, {'initial_equivalent_age_hours':-1}, {'q10':True},
    {'q10':0.5}, {'q10':float('nan')}, {'q10_low':3}, {'q10_high':1.1},
    {'max_gap_minutes':0}, {'minimum_temperature_c':5}, {'maximum_temperature_c':-1},
    {'temperature_basis':'ambient'}, {'calibration_status':'validated'},
    {'humidity_decay_coefficient':.2}, {'profile_id':''},
])
def test_unsupported_or_falsely_calibrated_profiles_are_rejected(changes):
    with pytest.raises(ValueError):
        evaluate_freshness([reading()], profile(**changes), at())


@pytest.mark.parametrize('value', ['2026-10-30T08:00:00', '2026-10-30', 'bad timestamp', None])
def test_naive_or_malformed_observation_times_are_never_assigned_a_timezone(value):
    sample = reading(); sample['observed_at'] = value
    with pytest.raises(ValueError, match='timezone-aware'):
        evaluate_freshness([sample], profile(), at())


def test_missing_baseline_or_evaluation_before_baseline_is_rejected():
    with pytest.raises(ValueError, match='started_at'):
        evaluate_freshness([reading()], {}, at())
    with pytest.raises(ValueError, match='precede'):
        evaluate_freshness([reading()], profile(), at(-1))
    with pytest.raises(ValueError, match='timezone-aware'):
        evaluate_freshness([reading()], profile(), '2026-10-30T09:00:00')


def test_observation_bound_and_history_bound_abstain_without_unbounded_work():
    with pytest.raises(ValueError, match='at most'):
        evaluate_freshness([reading()]*(MAX_READINGS+1), profile(), at())
    with pytest.raises(ValueError, match='sequence'):
        evaluate_freshness((reading() for _ in range(2)), profile(), at())
    result = evaluate_freshness([reading()], profile(), at(24*367))
    assert result['status'] == 'unscored' and 'history_bound' in codes(result)


def test_repeated_evaluation_is_deterministic_json_safe_and_does_not_mutate_constants():
    result = evaluate_freshness([reading(), reading(1)], profile(), at(1))
    assert result == evaluate_freshness([reading(), reading(1)], profile(), at(1))
    json.dumps(result, allow_nan=False)
    original = deepcopy(DEFAULT_PROFILE)
    result['profile']['q10'] = 10
    result['sources'][0]['label'] = 'changed local output'
    again = evaluate_freshness([reading()], profile(), at())
    assert DEFAULT_PROFILE == original
    assert again['profile']['q10'] == 2
    assert again['sources'][0]['label'] != 'changed local output'
    assert any('not a recommended poultry storage life' in line for line in again['limitations'])


def test_profile_normalization_explicitly_carries_declared_identity_and_defaults():
    normalized = normalize_profile(profile(profile_id='L05-assumptions-v1', product_category='simulated poultry'))
    assert normalized['reference_life_hours'] == 240
    assert normalized['started_at'] == at()
    assert normalized['profile_id'] == 'L05-assumptions-v1'
    assert normalized['calibration_status'] == 'illustrative_unvalidated'
