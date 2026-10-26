"""Checks actual feature construction against future-label perturbations."""
import json

import numpy as np
import pandas as pd

import scripts.train_model as training


def test_chronological_embargo_and_future_labels_do_not_enter_features(tmp_path, monkeypatch):
    dates = pd.date_range('2023-01-01', periods=500, freq='D').repeat(2)
    supplied = pd.DataFrame({
        'collection_date': dates,
        'salmonella_sp_analysis': ['Positive', 'Negative'] * 500,
        'salmonella_sp_analysis_canceled': ['NULL'] * 1000,
        'establishment_state': ['MO'] * 1000,
    })
    captured = []
    class InspectModel:
        def __init__(self, **kwargs):
            self.coef_ = np.array([[0.0, 0.0, 0.0]])
        def fit(self, features, labels):
            self.fitted_features = features.copy()
            return self
        def predict_proba(self, features):
            captured.append((self.fitted_features.copy(), features.copy()))
            return np.column_stack([np.full(len(features), .7), np.full(len(features), .3)])
    monkeypatch.setattr(training, 'ROOT', tmp_path)
    (tmp_path / 'docs').mkdir()
    monkeypatch.setattr(training.pd, 'read_parquet', lambda *args, **kwargs: supplied.copy())
    monkeypatch.setattr(training, 'LogisticRegression', InspectModel)
    training.main()
    first_report = json.loads((tmp_path / 'reports/model_evaluation.json').read_text())
    assert (pd.Timestamp(first_report['validation_start']) - pd.Timestamp(first_report['training_end'])).days > 90
    assert first_report['features'] == ['lag90_prevalence', 'month_sin', 'month_cos']
    assert 'Assumed' in first_report['feature_availability']
    assert 'publication timestamps unavailable' in first_report['feature_availability']
    assert 'not a validated prospective forecast' in first_report['status']
    # Change labels at/after the first validation day. Its features, and all
    # features within the next 90 days, must be unaffected.
    split = pd.Timestamp(first_report['validation_start'])
    supplied.loc[supplied.collection_date >= split, 'salmonella_sp_analysis'] = 'Positive'
    training.main()
    pd.testing.assert_frame_equal(captured[0][0], captured[1][0])
    rows = int((dates[(dates >= split) & (dates < split + pd.Timedelta(days=90))]).size)
    pd.testing.assert_frame_equal(captured[0][1].iloc[:rows], captured[1][1].iloc[:rows])
    # Enough history exists for the first held-out feature to be 0.5.
    assert np.allclose(captured[0][1].iloc[:rows]['lag90_prevalence'], .5)


def test_single_class_evaluation_does_not_invent_discrimination_metrics():
    result = training.evaluate(np.zeros(14, dtype=int), np.full(14, .2), pd.date_range('2024-01-01', periods=14))
    assert result['pr_auc_average_precision'] is None
    assert result['roc_auc'] is None
    assert np.isclose(result['brier'], .04)
    assert result['n'] == 14
    assert result['positives'] == 0
