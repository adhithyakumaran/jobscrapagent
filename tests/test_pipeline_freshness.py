from datetime import timedelta

from jobfinder.config import load_profile
from jobfinder.freshness import utc_now
from jobfinder.models import RawCandidate
from jobfinder.pipeline import _ingest_candidates, ScanStats
from jobfinder.deduplication.dedup import DeduplicationService
from jobfinder.matching.relevance import RelevanceEngine
from jobfinder.storage.db import Database


def test_stale_and_unknown_not_inserted(tmp_path):
    db = Database(tmp_path / "fresh.db")
    db.init_schema()
    profile = load_profile()
    scorer = RelevanceEngine(profile)
    dedup = DeduplicationService()
    stats = ScanStats()
    now = utc_now()

    raw_list = [
        RawCandidate(
            source="linkedin",
            source_url="https://www.linkedin.com/jobs/view/fresh-1",
            raw_text="Graduate engineer fresher role Chennai apply now",
            title_hint="Graduate Engineer",
            company_hint="Co",
            location_hint="Chennai",
            posted_at=now - timedelta(days=5),
            discovery_kind="job_listing",
        ),
        RawCandidate(
            source="linkedin",
            source_url="https://www.linkedin.com/jobs/view/stale-1",
            raw_text="Graduate engineer fresher role Chennai apply now",
            title_hint="Graduate Engineer",
            company_hint="Co",
            location_hint="Chennai",
            posted_at=now - timedelta(days=40),
            discovery_kind="job_listing",
        ),
        RawCandidate(
            source="linkedin",
            source_url="https://www.linkedin.com/jobs/view/unknown-1",
            raw_text="Graduate engineer fresher role Chennai apply now",
            title_hint="Graduate Engineer",
            company_hint="Co",
            location_hint="Chennai",
            posted_at=None,
            discovery_kind="job_listing",
        ),
    ]

    new_jobs = _ingest_candidates(raw_list, profile, db, scorer, dedup, stats)
    assert stats.fresh == 1
    assert stats.stale == 1
    assert stats.unknown_date == 1
    assert stats.freshness_rejected == 2
    assert len(new_jobs) == 1
    assert new_jobs[0].source_url.endswith("fresh-1")
