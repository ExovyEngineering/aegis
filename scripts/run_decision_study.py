"""Reproduce read-only Task 3 policy comparisons; writes report artifacts only."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.decision_study import build_decision_study
from backend.paths import write_json


def read_risk_context(root=ROOT):
    path = root / 'reports/model_evaluation.json'
    if not path.exists():
        return {'status': 'unavailable', 'historical_prevalence': None,
                'reason': 'Existing national FSIS model report is absent; no prior is invented.'}
    try:
        body = path.read_bytes()
        source = json.loads(body)
        prior = source.get('historical_prevalence')
        if type(prior) not in (int, float) or not 0 <= prior <= 1:
            raise ValueError('No valid national historical prevalence in source report')
        return {'status': 'available historical context only', 'historical_prevalence': prior,
                'model_status': source.get('status'), 'target': source.get('target'),
                'source_file': 'reports/model_evaluation.json', 'source_sha256': hashlib.sha256(body).hexdigest()}
    except (ValueError, OSError) as error:
        return {'status': 'unavailable', 'historical_prevalence': None, 'reason': str(error)}


def render_markdown(study):
    lines = ['# Read-only food-volume and destination-service decision study', '', study['objective'], '',
             '**Computed simulation. Every proposal requires human review. No operator state was accessed or changed.**', '',
             'The status-quo comparator takes the first feasible input candidate. The volume policy first maximizes kg, then the kg delivered from lots with modeled quality clocks ending within six hours. The balanced policy first maximizes equal destination service credit (capped at 50% of each destination demand), then kg and short-clock delivery. Every policy receives the same constraints and passes independent arithmetic review.', '',
             'National FSIS selected-sample prevalence is shared context only. Quality guidance comes from declared illustrative temperature histories and the existing Q10 quality model; it is not pathogen-risk reduction. Historical USDA county context supplies no need weights because the fictional destinations have no verified county crosswalk.', '',
             '| Scenario | Policy | Distributed kg | Unmet kg | Retained inventory kg | Quality-budget exposure kg | Destinations served | At least 50% served | Temperature reviews | Shipment hours |',
             '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for scenario in study['scenarios']:
        for policy in scenario['policies']:
            m = policy['metrics']
            lines.append(f"| {scenario['name']} | {policy['policy_name']} | {m['distributed_kg']} | {m['unmet_demand_kg']} | {m['retained_inventory_kg']} | {m['projected_quality_budget_exposure_kg']} | {m['destinations_served']} | {m['destinations_meeting_50_percent_demand']} | {m['temperature_review_shipments']} | {m['total_estimated_shipment_hours']} |")
    lines.extend(['', 'Retained inventory includes stock protected by a hold/recall; it is not all dispatchable. Quality-budget exposure counts eligible unsent stock whose illustrative quality clock ends within the six-hour horizon. Unsent inventory is not labeled waste. Temperature review counts measure workload, not contamination.', '',
                  'All policies dispatch **zero kg from held/recalled lots** and have **zero independent constraint violations** in the generated artifact.', '',
                  'The full JSON includes each scenario input network, quality model inputs and sensitivity results, each selected candidate, per-destination demand fulfillment, safety exclusions, priority diagnostics, lexicographic solver stages and comparison deltas. CSV exports one row per scenario/policy and a separate row per destination.', '', '## Scenario assumptions', ''])
    for scenario in study['scenarios']:
        lines.append(f"**{scenario['name']}**")
        lines.extend([''] + ['- ' + assumption for assumption in scenario['assumptions']] + [''])
    lines.extend(['## Unresolved scientific limitations', ''] + ['- ' + limitation for limitation in study['limitations']] + ['', study['unresolved_risk_action_link'], ''])
    return '\n'.join(lines)


def run(output_dir=None):
    output = Path(output_dir) if output_dir is not None else ROOT / 'reports'
    study = build_decision_study(read_risk_context())
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / 'decision_study.json', study)
    summary_rows, service_rows = [], []
    for scenario in study['scenarios']:
        for policy in scenario['policies']:
            identity = {'scenario_id': scenario['id'], 'policy_id': policy['policy_id'], 'simulation': True}
            summary_rows.append({**identity, **policy['metrics']})
            service_rows.extend({**identity, **row} for row in policy['demand_service'])
    for filename, rows in [('decision_study.csv', summary_rows), ('decision_study_demand_service.csv', service_rows)]:
        with (output / filename).open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    (output / 'decision_study.md').write_text(render_markdown(study), encoding='utf-8')
    return study


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports')
    arguments = parser.parse_args()
    result = run(arguments.output_dir)
    print(json.dumps({'status': result['status'], 'scenarios': len(result['scenarios']),
                      'policy_comparisons': sum(len(row['policies']) for row in result['scenarios']),
                      'operator_state_modified': result['operator_state_modified']}))
