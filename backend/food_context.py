"""Bounded historical USDA county context, kept separate from safety and routing."""
import csv
import hashlib
import io
import json

import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from backend.paths import read_json


def create_food_context_router(root):
    router = APIRouter(tags=['USDA historical food-access context'])

    def snapshot():
        report_path = root / 'reports/usda_food_environment.json'
        table_path = root / 'data/processed/usda_food_environment_missouri.parquet'
        if not report_path.exists() or not table_path.exists():
            raise HTTPException(404, 'USDA county context has not been ingested. Run scripts/ingest_usda.py; no observations are invented.')
        try:
            report = read_json(report_path)
            if report.get('status') != 'available':
                raise ValueError('Latest USDA ingestion is not available; inspect its recorded errors')
            if report.get('source_id') != 'usda_food_environment':
                raise ValueError('Unsupported USDA context source identity')
            expected = report['processed_file']['sha256']
            table_bytes = table_path.read_bytes()
            actual = hashlib.sha256(table_bytes).hexdigest()
            if actual != expected:
                raise ValueError('USDA derived-file checksum does not match its ingestion provenance')
            frame = pd.read_parquet(io.BytesIO(table_bytes))
            codes = [item['code'] for item in report['variables']]
            required = ['FIPS', 'State', 'County', 'county_display_name'] + codes
            if not set(required) <= set(frame.columns):
                raise ValueError('USDA derived table is missing documented columns')
            if len(frame) != report['geography']['county_count'] or frame.FIPS.duplicated().any():
                raise ValueError('USDA county count or identifiers disagree with provenance')
            if not frame.State.eq('MO').all() or not frame.FIPS.str.fullmatch(r'29\d{3}').fillna(False).all():
                raise ValueError('USDA county identifiers are not validated Missouri FIPS strings')
            # Serve values from the checked table; a stale copied report cannot override them.
            records = json.loads(frame[required].to_json(orient='records', double_precision=15))
            return dict(report, records=records, integrity_verified=True,
                        interpretation='Historical county context only; no location assignment, safety score, demand weight or dispatch change is inferred.')
        except Exception as error:
            raise HTTPException(503, f'{type(error).__name__}: {error}') from error

    @router.get('/api/food-access')
    def context():
        return snapshot()

    @router.get('/api/food-access.csv')
    def export():
        report = snapshot()
        columns = ['FIPS', 'State', 'County', 'county_display_name'] + [v['code'] for v in report['variables']]
        stream = io.StringIO(newline='')
        writer = csv.writer(stream)
        writer.writerow(columns + ['source_sha256', 'interpretation'])
        def cell(value):
            if value is None:
                return ''
            if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')):
                return "'" + value
            return value
        for row in report['records']:
            writer.writerow([cell(row.get(key)) for key in columns] + [report['source_file']['sha256'], 'Historical county context; not a safety or dispatch score'])
        return Response(stream.getvalue(), media_type='text/csv', headers={
            'Content-Disposition':'attachment; filename="aegis-usda-missouri-county-context.csv"',
            'X-AEGIS-Provenance':'Historical USDA county context; see /api/food-access for units, years, denominators and missingness',
        })

    return router
