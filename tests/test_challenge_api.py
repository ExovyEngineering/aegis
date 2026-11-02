"""The final evidence routes only inspect bounded allowlisted local artifacts."""
import json
import socket
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import httpx
import pytest

import backend.challenge as challenge


def make_client(root):
    app = FastAPI()
    app.include_router(challenge.create_challenge_router(root))
    return TestClient(app)


def test_allowlisted_get_exports_preserve_bytes_and_never_open_database_or_network(tmp_path, monkeypatch):
    sentinels = {}
    for name in ["data/raw/source.csv", "data/aegis.sqlite", "data/aegis.sqlite-wal"]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        sentinels[path] = ("private sentinel " + name).encode()
        path.write_bytes(sentinels[path])
    expected = {"guide.pdf", "guide.html", "guide.md", "readiness.json", "integrated-model.json",
                "analytic-data.csv", "decision-study.json", "decision-study.csv", "system-map.png",
                "team-science.md", "dictionary.csv", "provenance.json"}
    assert expected.issubset(challenge.ARTIFACTS)
    payloads = {}
    for name in expected:
        relative, _ = challenge.ARTIFACTS[name]
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = (b"%PDF-1.4\n" if name.endswith(".pdf") else b"captured bytes: ") + name.encode()
        path.write_bytes(payload)
        payloads[name] = payload
    for relative in ["reports/challenge_readiness.json", "reports/integrated_model_evaluation.json", "reports/decision_study.json"]:
        value = {"status": "recorded sentinel", "operational_activation_allowed": False, "measured": 0.125}
        path = tmp_path / relative
        path.write_text(json.dumps(value), encoding="utf-8")
        for name, (candidate, _) in challenge.ARTIFACTS.items():
            if candidate == relative:
                payloads[name] = path.read_bytes()

    def forbidden(*args, **kwargs):
        raise AssertionError("Read-only evidence routes must not contact a provider or open operator state")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(sqlite3, "connect", forbidden)
    with make_client(tmp_path) as client:
        for name in expected:
            response = client.get("/api/challenge/artifacts/" + name)
            assert response.status_code == 200
            assert response.content == payloads[name]
            assert challenge.ARTIFACTS[name][1] in response.headers["content-type"]
            disposition = "inline" if name in {"guide.html", "system-map.png"} else "attachment"
            assert disposition in response.headers["content-disposition"]
        for route in ["/api/challenge", "/api/challenge/integrated-model", "/api/challenge/decision-study"]:
            response = client.get(route)
            assert response.status_code == 200
            assert response.json()["operational_activation_allowed"] is False
            assert response.json()["measured"] == 0.125
            assert client.post(route).status_code == 405
        assert client.get("/api/challenge/artifacts/aegis.sqlite").status_code == 404
        assert client.get("/api/challenge/artifacts/%2e%2e%2f.env").status_code == 404
    assert all(path.read_bytes() == payload for path, payload in sentinels.items())


@pytest.mark.parametrize("payload", [None, "{broken", "[]", '{"score":NaN}', '{"score":-Infinity}', '{"score":1e309}'])
def test_unavailable_corrupt_or_nonfinite_reports_abstain_with_503(tmp_path, payload):
    if payload is not None:
        path = tmp_path / "reports/integrated_model_evaluation.json"
        path.parent.mkdir()
        path.write_text(payload, encoding="utf-8")
    with make_client(tmp_path) as client:
        response = client.get("/api/challenge/integrated-model")
        assert response.status_code == 503
        assert "Recorded evidence" in response.json()["detail"]
        assert client.get("/api/challenge/artifacts/guide.pdf").status_code == 404


def test_report_size_bound_and_resolved_path_boundary(tmp_path, monkeypatch):
    large = tmp_path / "reports/integrated_model_evaluation.json"
    large.parent.mkdir()
    with large.open("wb") as stream:
        stream.seek(20 * 1024 * 1024)
        stream.write(b" ")
    outside = tmp_path.parent / (tmp_path.name + "-private.json")
    outside.write_text('{"private":"not for export"}', encoding="utf-8")
    with pytest.raises(HTTPException) as error:
        challenge._path(tmp_path, outside)
    assert error.value.status_code == 503
    monkeypatch.setattr(challenge, "ARTIFACTS", {"escaped.json": (outside, "application/json")})
    with make_client(tmp_path) as client:
        response = client.get("/api/challenge/integrated-model")
        assert response.status_code == 503 and "bound" in response.json()["detail"]
        response = client.get("/api/challenge/artifacts/escaped.json")
        assert response.status_code == 503
        assert "not for export" not in response.text
