from jobfinder.actionable import build_job_actions, has_actionable_path, is_apply_link
from jobfinder.deduplication.dedup import DeduplicationService
from jobfinder.extraction.normalizer import raw_to_opportunity
from jobfinder.models import JobOpportunity, RawCandidate
from fastapi.testclient import TestClient

from jobfinder.web import app as web_app


def test_linkedin_job_url_preserved():
    raw = RawCandidate(
        source="linkedin",
        source_url="https://www.linkedin.com/jobs/view/12345",
        raw_text="Hiring fresher engineer",
        application_url="https://careers.example.com/apply",
        application_method="external_apply",
        discovery_kind="job_listing",
    )
    job = raw_to_opportunity(raw)
    assert job.source_url == "https://www.linkedin.com/jobs/view/12345"
    assert job.application_url == "https://careers.example.com/apply"


def test_linkedin_post_url_preserved():
    raw = RawCandidate(
        source="linkedin",
        source_url="https://www.linkedin.com/posts/user_activity-999",
        raw_text="We're hiring freshers in Chennai. DM your resume.",
        discovery_kind="hiring_post",
        source_post_url="https://www.linkedin.com/posts/user_activity-999",
        application_method="dm_resume",
    )
    job = raw_to_opportunity(raw)
    assert "linkedin.com/posts/" in (job.source_url or "")
    actions = build_job_actions(job)
    assert actions["open_label"] == "Open LinkedIn Post"
    assert "LinkedIn DM" in actions["application_summary"]


def test_email_preserved():
    job = JobOpportunity(
        source="linkedin",
        source_url="https://www.linkedin.com/posts/x",
        contact_email="careers@co.example",
        application_method="email",
        description="Hiring. Send CV to careers@co.example",
        discovery_kind="hiring_post",
    )
    actions = build_job_actions(job)
    assert actions["mailto"] == "mailto:careers@co.example"


def test_dm_resume_method():
    job = JobOpportunity(
        source="linkedin",
        source_url="https://www.linkedin.com/posts/dm-1",
        application_method="dm_resume",
        description="DM your resume",
        discovery_kind="hiring_post",
    )
    assert has_actionable_path(job)
    assert "LinkedIn DM" in build_job_actions(job)["application_summary"]


def test_dedup_preserves_urls():
    dedup = DeduplicationService()
    canonical = JobOpportunity(
        source="linkedin",
        source_url="https://www.linkedin.com/jobs/view/1",
        company_name="Co",
        job_title="Dev",
        location="Chennai",
        application_url="https://careers.co/apply",
    )
    duplicate = JobOpportunity(
        source="mock_board",
        source_url="https://jobsboard.example/1",
        company_name="Co",
        job_title="Dev",
        location="Chennai",
        application_url="https://careers.co/apply",
    )
    merged = dedup.merge_duplicate(canonical, duplicate)
    assert "https://www.linkedin.com/jobs/view/1" == merged.source_url
    assert merged.application_url == "https://careers.co/apply"
    assert "https://jobsboard.example/1" in merged.alternate_source_urls


def test_no_invented_urls():
    job = JobOpportunity(
        source="linkedin",
        source_url="https://www.linkedin.com/jobs/view/9",
        company_name="Co",
        job_title="Role",
        location="Chennai",
    )
    actions = build_job_actions(job)
    assert actions["apply_url"] is None
    assert actions["open_url"] == job.source_url


def test_ui_renders_linkedin_job_actions():
    client = TestClient(web_app.app)
    # Template logic via row builder
    from jobfinder.web.app import _job_to_row

    job = JobOpportunity(
        source="linkedin",
        source_url="https://www.linkedin.com/jobs/view/55",
        company_name="ABC",
        job_title="Graduate Engineer",
        location="Chennai",
        application_url="https://apply.example.com/x",
        application_method="external_apply",
        discovery_kind="job_listing",
        relevance_score=50,
    )
    row = _job_to_row(job)
    assert row is not None
    assert row["open_label"] == "Open LinkedIn Job"
    assert row["show_apply"]

    resp = client.get("/")
    assert resp.status_code == 200
