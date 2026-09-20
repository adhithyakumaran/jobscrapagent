from __future__ import annotations

import logging

from jobfinder.config import LinkedInSourceConfig
from jobfinder.discovery.base import DiscoveryContext, ProviderRunStats
from jobfinder.discovery.linkedin.http_client import fetch_with_backoff
from jobfinder.discovery.linkedin.intent_filter import intents_for_listings
from jobfinder.extraction.linkedin import (
    build_jobs_search_url,
    parse_job_detail_html,
    parse_job_listing_html,
)
from jobfinder.models import RawCandidate

logger = logging.getLogger(__name__)


class LinkedInGuestProvider:
    name = "linkedin_guest"

    def __init__(self, config: LinkedInSourceConfig) -> None:
        self.config = config

    def discover(
        self,
        context: DiscoveryContext,
    ) -> tuple[list[RawCandidate], ProviderRunStats]:
        stats = ProviderRunStats(provider=self.name)
        results: list[RawCandidate] = []
        intents = intents_for_listings(context.intents)
        if not intents:
            stats.success = True
            return results, stats
        try:
            for intent in intents:
                stats.intents_executed += 1
                collected = 0
                details_fetched = 0
                for page in range(self.config.max_pages_per_intent):
                    start = page * 25
                    url = build_jobs_search_url(intent.query_string(), intent.location, start=start)
                    fetched, hits = fetch_with_backoff(
                        url,
                        delay=self.config.delay_seconds,
                        backoff_base=self.config.rate_limit_backoff_seconds,
                        max_retries=self.config.rate_limit_max_retries,
                    )
                    stats.rate_limit_hits += hits
                    stats.pages_fetched += 1
                    if fetched.rate_limited:
                        logger.warning("Guest listing search rate limited — skipping intent")
                        break
                    if not fetched.html:
                        break
                    batch = parse_job_listing_html(fetched.html)
                    if not batch:
                        break
                    for cand in batch:
                        if cand.source_url in context.seen_urls:
                            continue
                        context.seen_urls.add(cand.source_url)
                        if details_fetched < self.config.detail_fetch_limit_per_intent:
                            detail, dhits = fetch_with_backoff(
                                cand.source_url,
                                delay=self.config.delay_seconds,
                                backoff_base=self.config.rate_limit_backoff_seconds,
                                max_retries=self.config.rate_limit_max_retries,
                            )
                            stats.rate_limit_hits += dhits
                            stats.pages_fetched += 1
                            if detail.rate_limited:
                                logger.warning("Guest job detail rate limited — using listing card")
                                results.append(cand)
                                collected += 1
                                break
                            details_fetched += 1
                            if detail.html:
                                detailed = parse_job_detail_html(detail.html, cand.source_url)
                                if detailed:
                                    cand = detailed
                        results.append(cand)
                        collected += 1
                        if collected >= self.config.max_results_per_intent:
                            break
                    if collected >= self.config.max_results_per_intent:
                        break
            stats.candidates = len(results)
            stats.success = True
        except Exception as exc:
            stats.success = False
            stats.error = str(exc)
            logger.warning("Guest provider failed: %s", exc)
        return results, stats
