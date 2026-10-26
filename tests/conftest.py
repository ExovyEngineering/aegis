"""Tests use temporary databases/caches and never mutate supplied raw data."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient
import backend.main as api


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, 'DB', tmp_path / 'test.sqlite')
    with TestClient(api.app) as client:
        yield client
