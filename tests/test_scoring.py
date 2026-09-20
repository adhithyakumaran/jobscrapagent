from datetime import timedelta

from jobfinder.config import load_profile
from jobfinder.freshness import utc_now
from jobfinder.matching.relevance import RelevanceEngine
from jobfinder.models import JobOpportunity


def test_fresher_job_scores_higher_than_senior():
    profile = load_profile()
    engine = RelevanceEngine(profile)
    fresher = JobOpportunity(
        source="test",
        source_url="https://example.com/fresher",
        company_name="Co",
        job_title="Graduate Engineer",
        location="Chennai",
        description="We are hiring freshers in Chennai. 0-1 years.",
        posted_at=utc_now() - timedelta(hours=2),
        is_fresher=True,
        application_url="https://example.com/apply",
    )
    senior = JobOpportunity(
        source="test",
        source_url="https://example.com/senior",
        company_name="Co",
        job_title="Senior Manager",
        location="Chennai",
        description="10+ years experience required. Lead team.",
        posted_at=utc_now() - timedelta(hours=2),
        experience_min=10,
    )
    r1, _, _ = engine.score(fresher)
    r2, _, _ = engine.score(senior)
    assert r1 > r2
