"""Render the owner-reported team contribution and measured comparison in one page."""
import json
from io import BytesIO
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
        'Our starting question: how can a poultry distributor use public food-safety and environmental evidence to make better delivery decisions while keeping food available? AEGIS developed from a logistics idea into an auditable path from historical evidence to a reviewed operational choice, with a simulated Missouri network, freshness replay and driver instructions.',
        'Complementary roles, reported by the project lead: Isaac Jenkins led the disease/public-health perspective and disease-related databases. Micky fact-checked code and helped establish the GitHub repository. The project lead handled supply-chain logistics, gathered the remaining data, defined application requirements and designed operational extensions. Codex assisted implementation, documentation and automated testing. No professional credentials or external interviews are claimed.',
        'A decision changed: Isaac\'s disease-side input helped broaden the logistics concept to include CDC data, especially BEAM, and historical patterns. Human surveillance became a distinct evidence layer rather than an assumed contamination label for a shipment. The lead\'s feedback on confusing controls and driver distraction shaped guided questions, clearer map workflows and parked-use reporting. These are reported project decisions, not a formal usability study.',
        f"What integration taught us: FSIS supplies selected-sample outcomes, PulseNet-derived BEAM aggregates supply human context, and NOAA supplies ambient observations. NORS and USDA Food Environment Atlas add two domains. On {n} held-out Missouri samples, core Brier was {brier('core_integrated')} versus baseline {brier('baseline')}; BEAM/NOAA marginal intervals included zero. NORS worsened Brier to {brier('with_nors')}, with an old, constant holdout feature. More data did not automatically improve prediction. USDA remains contextual without a verified recipient/needs crosswalk.",
        'How the idea matured: uncertain surveillance never automatically holds a lot. Binding recall/hold exclusions and human approval govern dispatch. Freshness replay and constrained comparisons explore timing, eligible volume and service; all logistics and cargo telemetry are simulated. No measured spoilage, prevented illness or real-world savings are claimed.',
        'Next partner: a refrigerated distributor with a public-health/food-safety partner could provide deidentified traceability, actual publication timestamps, calibrated cargo histories and receiving/demand data for prospective validation and food-access analysis. Authors will review credit and claims; Micky\'s surname and the lead\'s author name remain for completion. Kiro was not used; prepared specs are not genuine Kiro evidence. Full statement: docs/team_science_statement.md.'
    ]
    pages=render_pdf([('One-page team science statement',body)],ROOT/'reports/team_science_statement.pdf')
    if pages!=1:raise ValueError('Team statement exceeds one page; edit before claiming the one-page deliverable')
    from pypdf import PdfWriter
    output=ROOT/'reports/team_science_statement.pdf'
    writer=PdfWriter(clone_from=output)
    writer.add_metadata({'/Title':'AEGIS Team Science Statement','/Subject':'Reported interdisciplinary contributions, changed decisions, added-data findings and next collaboration'})
    buffer=BytesIO();writer.write(buffer);output.write_bytes(buffer.getvalue())
    print('Generated one-page team science PDF from owner-reported contributions and recorded study metrics')


if __name__=='__main__':main()
