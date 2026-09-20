from pathlib import Path

import pytest

from jobfinder.pipeline import run_mock_scan
from jobfinder.storage.db import Database


@pytest.fixture
def temp_db(tmp_path: Path) -> Database:
    db = Database(tmp_path / "test.db")
    db.init_schema()
    return db


def test_mock_scan_persists_jobs(temp_db: Database):
    stats = run_mock_scan(db=temp_db, max_intents=10)
    assert stats.candidates_discovered > 0
    assert stats.new_opportunities > 0
    counts = temp_db.job_counts()
    assert counts["total"] == stats.new_opportunities
    assert stats.duplicates >= 1
    assert stats.rejected >= 1  # senior role


def test_mock_scan_idempotent_source_urls(temp_db: Database):
    run_mock_scan(db=temp_db, max_intents=5)
    first = temp_db.job_counts()["total"]
    stats2 = run_mock_scan(db=temp_db, max_intents=5)
    assert stats2.new_opportunities == 0
    assert temp_db.job_counts()["total"] == first
