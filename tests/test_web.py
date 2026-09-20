from pathlib import Path

from fastapi.testclient import TestClient

from jobfinder.pipeline import run_mock_scan
from jobfinder.storage.db import Database
from jobfinder.web import app as web_app


def test_web_index(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "web.db"
    db = Database(db_path)
    monkeypatch.setattr(web_app, "_db", db)
    run_mock_scan(db=db, max_intents=5)
    client = TestClient(web_app.app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Personal Job Finder" in resp.content
