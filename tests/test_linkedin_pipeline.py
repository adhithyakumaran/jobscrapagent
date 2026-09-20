from pathlib import Path

from jobfinder.deduplication.dedup import DeduplicationService
from jobfinder.extraction.normalizer import raw_to_opportunity
from jobfinder.models import JobOpportunity, RawCandidate


def test_linkedin_job_and_post_dedup():
    job = JobOpportunity(
        source="linkedin",
        source_url="https://www.linkedin.com/jobs/view/111",
        company_name="Example Corp",
        job_title="Graduate Engineer",
        location="Chennai",
        application_url="https://example.com/apply/123",
        description="Fresher hiring",
    )
    post = JobOpportunity(
        source="linkedin",
        source_url="https://www.linkedin.com/posts/222",
        company_name="Example Corp",
        job_title="Graduate Engineer",
        location="Chennai",
        application_url="https://example.com/apply/123",
        description="We are hiring freshers",
    )
    dedup = DeduplicationService()
    r = dedup.find_duplicate(post, [job])
    assert r.is_duplicate


def test_missing_posted_stays_null():
    raw = RawCandidate(
        source="linkedin",
        source_url="https://www.linkedin.com/posts/x",
        raw_text="We're hiring freshers in Chennai.",
        discovery_kind="hiring_post",
    )
    job = raw_to_opportunity(raw)
    assert job.posted_at is None


def test_provider_failure_fallback():
    from jobfinder.discovery.linkedin.composite import LinkedInCompositeProvider
    from jobfinder.config import LinkedInSourceConfig
    from jobfinder.discovery.base import DiscoveryContext
    from jobfinder.matching.intents import SearchIntent

    class FailProvider:
        name = "fail"

        def discover(self, context):
            from jobfinder.discovery.base import ProviderRunStats

            return [], ProviderRunStats(provider="fail", success=False, error="boom")

    cfg = LinkedInSourceConfig(providers=["guest"], max_pages_per_intent=0)
    comp = LinkedInCompositeProvider(cfg)
    comp._providers = [FailProvider(), FailProvider()]
    ctx = DiscoveryContext(
        intents=[
            SearchIntent("fresher", "hiring", "Chennai", "any", "any"),
        ]
    )
    results, stats = comp.discover(ctx)
    assert results == []
    assert len(stats) == 2
    assert all(not s.success for s in stats)
