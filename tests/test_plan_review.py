from copy import deepcopy
import pytest
from backend.simulation import seed_network
from backend.optimization import optimize
from backend.plan_review import review_plan


@pytest.mark.parametrize('scenario', list('ABCD'))
def test_independent_review_matches_resource_arithmetic(scenario):
    n = seed_network(); plan = optimize(n, scenario)
    r = plan['review']
    assert r['passed'] and r['violations'] == []
    assert sum(x['used_kg'] for x in r['resources'] if x['kind']=='destination') == sum(s['quantity_kg'] for s in plan['shipments'])
    assert len(r['excluded_shipments'])+len(plan['shipments']) == len(n['shipments'])
    assert all(x['remaining_kg'] >= 0 for x in r['resources'])


def test_independent_review_rejects_tampering_and_capacity_without_solver():
    n = seed_network(); selected = optimize(n)['shipments']
    tampered = deepcopy(selected); tampered[0]['quantity_kg'] = -1
    assert 'candidate fields changed' in str(review_plan(n, tampered)['violations'])
    n['trucks'][0]['capacity_kg'] = 0
    assert not review_plan(n, selected)['passed']
    assert not review_plan(seed_network(), selected+[selected[0]])['passed']


def test_exclusion_reasons_do_not_claim_solver_causality():
    n=seed_network(); r=optimize(n)['review']
    assert any('lot held' in row['reasons'] for row in r['excluded_shipments'])
    assert 'not a counterfactual' in r['exclusion_note']


def test_recalled_or_held_assignment_fails_even_if_supplied_by_external_code():
    n=seed_network(); selected=optimize(n)['shipments']; lid=selected[0]['lot_id']
    next(x for x in n['lots'] if x['id']==lid)['recalled']=True
    assert 'lot recalled' in str(review_plan(n,selected)['violations'])
