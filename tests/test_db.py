from pathlib import Path

from jobfinder.freshness import utc_now
from jobfinder.models import JobOpportunity, JobStatus
from jobfinder.storage.db import Database


def test_insert_and_list(tmp_path: Path):
    db = Database(tmp_path / "jobs.db")
    db.init_schema()
    job = JobOpportunity(
        source="test",
        source_url="https://example.com/job/1",
        company_name="TestCo",
        job_title="Analyst",
        location="Remote India",
        posted_at=utc_now(),
        discovered_at=utc_now(),
        relevance_score=50.0,
        confidence_score=40.0,
        status=JobStatus.NEW,
    )
    db.insert_job(job)
    listed = db.list_jobs(status="new")
    assert len(listed) == 1
    assert listed[0].company_name == "TestCo"
    assert db.set_job_status(job.id, JobStatus.SEEN)
    assert db.list_jobs(status="new") == []
