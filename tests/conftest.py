"""Tests use temporary databases/caches and never mutate supplied raw data."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient
import backend.main as api


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, 'DB', tmp_path / 'test.sqlite')
    # Legacy workflow tests represent an already parked operator. New Drive
    # integration tests use their own fresh DB to verify the default lock.
    with api.db() as connection:
        network, _ = api.load(connection)
        instant = datetime.now(timezone.utc)
        connection.executemany(
            'INSERT INTO driver_focus VALUES (?,?,?,?,?)',
            [(truck['id'], 'parked', 1, (instant + timedelta(minutes=10)).isoformat(),
              instant.isoformat()) for truck in network['trucks']],
        )
    with TestClient(api.app) as client:
        yield client
