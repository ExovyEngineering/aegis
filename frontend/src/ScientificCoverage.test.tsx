import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { NOAACoverageCard, ModelTimingCard } from './ScientificCoverage';
import { api } from './api';
vi.mock('./api', async original => ({ ...await original<object>(), api: vi.fn() }));
describe('Scientific evidence coverage', () => {
  it('distinguishes complete station-date rows from missing weather variables', async () => {
    vi.mocked(api).mockResolvedValue({ status: 'partial', station_count: 5, requested_station_count: 5, expected_station_days: 2730, observed_station_days: 2730, coverage_fraction: 1, metric_coverage_fraction: .998901, missing_metric_values: 9, stations: [{ city: 'Columbia', station_id: 'USW00003945', station_name: 'Verified station', latitude: 38.817, longitude: -92.215, distance_to_city_km: 14, expected_days: 546, observed_days: 546, missing_days: 0, metric_coverage: { PRCP: { missing_days: 0, flagged_days: 0 } }, status: 'captured' }] });
    render(<NOAACoverageCard />);
    expect(await screen.findByText('100.0%')).toBeInTheDocument();
    expect(screen.getByText('99.89%')).toBeInTheDocument();
    expect(screen.getByText('9 missing metric values')).toBeInTheDocument();
    expect(screen.getByText('Complete date rows do not establish complete variables.')).toBeInTheDocument();
    expect(screen.getByText('partial')).toBeInTheDocument();
  });
  it('does not present snapshot consistency as verified prospective release timing', async () => {
    vi.mocked(api).mockResolvedValue({ status: 'snapshot-consistent retrospective stress test; public release timing unverified', snapshot_release_verified: false, feature_availability: 'No per-result publication timestamp available', strict_split: { training_snapshot_cutoff: '2026-03-19', training_rows: 57459, validation_rows: 7754 }, snapshot_baseline: { brier: .09297314, roc_auc: .5 }, calendar_logistic: { brier: .09293427, roc_auc: .51 }, limitations: ['Not prospective validation'] });
    render(<ModelTimingCard />);
    expect(await screen.findByText(/public release timing unverified/)).toBeInTheDocument();
    expect(screen.getByText('No')).toBeInTheDocument();
    expect(screen.getByText('0.09297')).toBeInTheDocument();
    expect(screen.getByText('Not prospective validation')).toBeInTheDocument();
  });
});
