"""Create a source-specific Missouri USDA county-context extract."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.paths import ROOT, data_dir, write_json
from backend.ingestion.usda import (REPORT_PATH, SOURCE_ID, discover_food_environment_files,
                                    ingest_food_environment)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=data_dir())
    parser.add_argument('--file', type=Path, help='Use one explicitly selected workbook')
    parser.add_argument('--output-root', type=Path, default=ROOT,
                        help='Root for derived data/reports, useful for isolated verification')
    args = parser.parse_args(argv)
    discovery_errors = []
    try:
        if args.file:
            source = args.file
        else:
            if not args.data_dir.is_dir():
                raise FileNotFoundError(f'Data directory not found: {args.data_dir}')
            candidates, discovery_errors = discover_food_environment_files(args.data_dir)
            if not candidates:
                raise FileNotFoundError('No workbook with the supported USDA Food Environment Atlas sheet metadata was found')
            if len(candidates) != 1:
                raise ValueError(f'Multiple candidate atlas workbooks found; select --file explicitly: {[str(path) for path in candidates]}')
            source = candidates[0]
        report = ingest_food_environment(source, args.output_root)
        if discovery_errors:
            report['discovery_errors'] = discovery_errors
            write_json(args.output_root / REPORT_PATH, report)
        print(f"USDA Food Environment Atlas: {report['geography']['county_count']} Missouri counties/county-equivalents; {len(report['variables'])} historical variables")
        print(f"Source: {source.name}; SHA-256 {report['source_file']['sha256']}")
        print(f"Derived data: {report['processed_file']['path']}; report: {REPORT_PATH}")
        print('Missing observations remain null: ' + ', '.join(f'{key}={value}' for key, value in report['coverage']['null_counts'].items()))
        for error in discovery_errors:
            print(f"Skipped unreadable workbook {error['file']}: {error['error']}", file=sys.stderr)
        return 0
    except Exception as exc:
        error = f'{type(exc).__name__}: {exc}'
        write_json(args.output_root / REPORT_PATH, {
            'status': 'failed', 'source_id': SOURCE_ID, 'error': error,
            'discovery_errors': discovery_errors,
            'coverage_warning': 'Ingestion failed; any prior derived file must not be represented as a newly verified extract.',
        })
        print(f'USDA ingestion failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
