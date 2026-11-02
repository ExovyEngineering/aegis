"""Render the owner-reported team contribution and measured comparison in one page."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_project_brief import render_pdf


def main():
    study=json.loads((ROOT/'reports/integrated_model_evaluation.json').read_text(encoding='utf-8'))
    n=study['primary_split']['validation_rows']
    brier=lambda key:format(study['models'][key]['metrics']['brier'],'.5f')
    body=[
        "Contributors (reported by the project owner): Isaac handled the disease side; Micky provided coding help; the project owner led integration and user-facing workflow priorities. Contributor last names and the owner's final author name will be added by the team. No professional credentials or external interviews are claimed.",
        'Team decision that changed: disease-side input helped the project incorporate CDC data, especially BEAM surveillance, and examine historical patterns. This is a project-owner-reported contribution. Separately, operator feedback about unhelpful chicken queries, unexplained map layers and texting while driving led to guided questions, task-based map explanations and parked-use driver controls.',
        'The three core sources retain different roles: PulseNet-derived BEAM human aggregates provide regional context; FSIS selected poultry samples provide the retrospective target; NOAA observations provide an ambient index. NORS historical outbreaks and USDA Food Environment Atlas add two domains. No person, genome, lot, supplier or outbreak is causally linked by co-location.',
        f"Measured added-data result: the {n}-sample Missouri holdout has core Brier {brier('core_integrated')} versus baseline {brier('baseline')}. Added BEAM/NOAA effects remain uncertain; NORS Brier is {brier('with_nors')} in this cohort, with a constant holdout feature. Read the recorded paired intervals; no gain is assumed. USDA stays contextual because fictional recipients lack a verified county/needs cross-walk.",
        'Next partner/data: a real refrigerated distributor and public-health/food-safety partner could supply deidentified lot/establishment/time traceability, result-publication timestamps, calibrated cargo histories and recipient receiving/demand data. These would improve availability and access analyses. Kiro was not used, as disclosed by the owner. Software checks do not establish prospective validity, team signoff or a timed human video. Full role/decision wording is in docs/team_science_statement.md and requires author review.'
    ]
    pages=render_pdf([('One-page team science statement',body)],ROOT/'reports/team_science_statement.pdf')
    if pages!=1:raise ValueError('Team statement exceeds one page; edit before claiming the one-page deliverable')
    print('Generated one-page team science PDF from owner-reported contributions and recorded study metrics')


if __name__=='__main__':main()
