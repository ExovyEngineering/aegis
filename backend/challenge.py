"""Bounded, read-only access to the final challenge evidence and handoff files."""
import json
import math
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse


ARTIFACTS = {
    'guide.pdf': ('reports/final_submission_guide.pdf', 'application/pdf'),
    'guide.html': ('reports/final_submission_guide.html', 'text/html'),
    'guide.md': ('reports/final_submission_guide.md', 'text/markdown'),
    'readiness.json': ('reports/challenge_readiness.json', 'application/json'),
    'integrated-model.json': ('reports/integrated_model_evaluation.json', 'application/json'),
    'analytic-data.csv': ('data/processed/integrated_mo_analytic.csv', 'text/csv'),
    'decision-study.json': ('reports/decision_study.json', 'application/json'),
    'decision-study.csv': ('reports/decision_study.csv', 'text/csv'),
    'system-map.png': ('reports/figures/one_health_system.png', 'image/png'),
    'team-science.md': ('docs/team_science_statement.md', 'text/markdown'),
    'team-science.pdf': ('reports/team_science_statement.pdf', 'application/pdf'),
    'dictionary.csv': ('reports/data_dictionary.csv', 'text/csv'),
    'provenance.json': ('reports/source_provenance.json', 'application/json'),
}


def _path(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise HTTPException(503, 'Evidence resolves outside the project; no file was served')
    return path


def _report(root, relative):
    path = _path(root, relative)
    if not path.is_file():
        raise HTTPException(503, f'Recorded evidence is not available: {relative}')
    if path.stat().st_size > 20 * 1024 * 1024:
        raise HTTPException(503, f'Recorded evidence exceeds the inspection bound: {relative}')
    def invalid(value):
        raise ValueError(f'Unsupported nonfinite JSON value: {value}')
    def finite_float(value):
        result=float(value)
        if not math.isfinite(result):
            raise ValueError('Nonfinite JSON number')
        return result
    try:
        result = json.loads(path.read_text(encoding='utf-8'), parse_constant=invalid, parse_float=finite_float)
        if not isinstance(result, dict):
            raise ValueError('Expected a JSON object')
    except (OSError, UnicodeError, ValueError) as error:
        raise HTTPException(503, f'Recorded evidence could not be read: {relative}: {type(error).__name__}: {error}') from error
    return result


def create_challenge_router(root):
    router = APIRouter(prefix='/api/challenge', tags=['Five challenge tasks and final evidence'])

    @router.get('')
    def readiness():
        return _report(root, 'reports/challenge_readiness.json')

    @router.get('/integrated-model')
    def integrated_model():
        return _report(root, 'reports/integrated_model_evaluation.json')

    @router.get('/decision-study')
    def decision_study():
        return _report(root, 'reports/decision_study.json')

    @router.get('/artifacts/{name}')
    def artifact(name: str):
        if name not in ARTIFACTS:
            raise HTTPException(404, 'Unknown challenge artifact')
        relative, media_type = ARTIFACTS[name]
        path = _path(root, relative)
        if not path.is_file():
            raise HTTPException(404, f'Artifact has not been generated: {relative}')
        return FileResponse(path, media_type=media_type, filename=path.name,
                            content_disposition_type='inline' if media_type in {'text/html', 'image/png'} else 'attachment')

    return router
