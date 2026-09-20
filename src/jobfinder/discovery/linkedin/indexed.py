from __future__ import annotations

import logging
from urllib.parse import quote_plus

from jobfinder.config import LinkedInSourceConfig
from jobfinder.discovery.base import DiscoveryContext, ProviderRunStats
from jobfinder.discovery.linkedin.http_client import fetch_url
from jobfinder.extraction.linkedin import (
    build_content_search_url,
    parse_hiring_post_html,
    parse_indexed_links,
    parse_job_detail_html,
)
from jobfinder.models import RawCandidate

logger = logging.getLogger(__name__)


class LinkedInIndexedProvider:
    name = "linkedin_indexed"

    def __init__(self, config: LinkedInSourceConfig) -> None:
        self.config = config

    def discover(
        self,
        context: DiscoveryContext,
    ) -> tuple[list[RawCandidate], ProviderRunStats]:
        stats = ProviderRunStats(provider=self.name)
        results: list[RawCandidate] = []
        try:
            for intent in context.intents:
                stats.intents_executed += 1
                q = f"{intent.query_string()} site:linkedin.com"
                url = build_content_search_url(q)
                fetched = fetch_url(url, delay=self.config.delay_seconds)
                stats.pages_fetched += 1
                if fetched.rate_limited or not fetched.html:
                    continue
                links = parse_indexed_links(fetched.html)
                for link in links:
                    if link.source_url in context.seen_urls:
                        continue
                    context.seen_urls.add(link.source_url)
                    page = fetch_url(link.source_url, delay=self.config.delay_seconds)
                    stats.pages_fetched += 1
                    if page.rate_limited:
                        break
                    page_html = page.html
                    if not page_html:
                        results.append(link)
                        continue
                    if link.discovery_kind == "job_listing":
                        detailed = parse_job_detail_html(page_html, link.source_url)
                        results.append(detailed or link)
                    else:
                        posts = parse_hiring_post_html(
                            page_html,
                            link.source_url,
                            location_hints=[intent.location],
                        )
                        results.extend(posts or [link])
                    if len(results) >= self.config.max_results_per_intent:
                        break
            stats.candidates = len(results)
            stats.success = True
        except Exception as exc:
            stats.success = False
            stats.error = str(exc)
            logger.warning("Indexed provider failed: %s", exc)
        return results, stats
