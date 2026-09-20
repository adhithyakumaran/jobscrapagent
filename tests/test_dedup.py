from jobfinder.deduplication.dedup import DeduplicationService, normalize_company
from jobfinder.models import JobOpportunity


def test_normalize_company_strips_suffix():
    assert "abc" in normalize_company("ABC Technologies Pvt. Ltd.")


def test_duplicate_by_application_url():
    dedup = DeduplicationService()
    a = JobOpportunity(
        source="a",
        source_url="https://example.com/a",
        company_name="ABC Technologies",
        job_title="Graduate Software Engineer",
        location="Chennai",
        application_url="https://abc.example/careers/grad",
        description="Fresher role",
    )
    b = JobOpportunity(
        source="b",
        source_url="https://example.com/b",
        company_name="ABC Tech",
        job_title="Graduate Software Engineer",
        location="Chennai",
        application_url="https://abc.example/careers/grad",
        description="Same apply link",
    )
    result = dedup.find_duplicate(b, [a])
    assert result.is_duplicate
    assert result.reason == "application_url"
