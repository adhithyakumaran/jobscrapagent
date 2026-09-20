from __future__ import annotations

from datetime import timedelta

from jobfinder.discovery.mock_data import MOCK_CANDIDATES
from jobfinder.freshness import utc_now
from jobfinder.discovery.base import DiscoveryContext
from jobfinder.models import RawCandidate


class MockDiscoveryProvider:
    """Returns fixed sample jobs; simulates intent-driven discovery."""

    name = "mock"

    def discover(self, context: DiscoveryContext) -> list[RawCandidate]:
        now = utc_now()
        results: list[RawCandidate] = []
        # Return full fixture set once per scan (intents count toward stats only)
        for item in MOCK_CANDIDATES:
            posted_offset_hours = item.get("posted_offset_hours", 24)
            kind = "job_listing" if item.get("title_hint") else "hiring_post"
            raw = RawCandidate(
                source=item.get("source", "mock"),
                source_url=item["source_url"],
                raw_text=item["raw_text"],
                title_hint=item.get("title_hint"),
                company_hint=item.get("company_hint"),
                location_hint=item.get("location_hint"),
                posted_at=now - timedelta(hours=posted_offset_hours),
                application_url=item.get("application_url"),
                application_method=item.get("application_method"),
                contact_email=item.get("contact_email"),
                domain_hint=item.get("domain_hint"),
                discovery_kind=kind,
            )
            results.append(raw)
        return results
