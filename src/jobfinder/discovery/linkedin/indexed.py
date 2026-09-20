from __future__ import annotations

import logging
from urllib.parse import quote_plus

from jobfinder.config import LinkedInSourceConfig
from jobfinder.discovery.base import DiscoveryContext, ProviderRunStats
from jobfinder.discovery.linkedin.http_client import fetch_with_backoff
from jobfinder.discovery.linkedin.intent_filter import intents_for_listings, intents_for_posts
from jobfinder.extraction.linkedin import (
    build_content_search_url,
    parse_hiring_post_html,
    parse_indexed_links,
    parse_job_detail_html,
)
from jobfinder.models import RawCandidate

logger = logging.getLogger(__name__)


def _post_search_url(query: str) -> str:
    q = quote_plus(f"{query} site:linkedin.com/posts")
    return f"https://html.duckduckgo.com/html/?q={q}"


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
        post_intents = intents_for_posts(context.intents)
        listing_intents = intents_for_listings(context.intents)
        ordered = post_intents + listing_intents
        try:
            for intent in ordered:
                stats.intents_executed += 1
                q = intent.query_string()
                if intent.intent_type in ("hiring_post", "experimental"):
                    url = _post_search_url(q)
                else:
                    url = build_content_search_url(f"{q} site:linkedin.com/jobs/view")
                fetched, hits = fetch_with_backoff(
                    url,
                    delay=self.config.delay_seconds,
                    backoff_base=self.config.rate_limit_backoff_seconds,
                    max_retries=self.config.rate_limit_max_retries,
                )
                stats.rate_limit_hits += hits
                stats.pages_fetched += 1
                if fetched.rate_limited:
                    logger.warning("Indexed search rate limited")
                    continue
                if not fetched.html:
                    continue
                links = parse_indexed_links(fetched.html)
                prefer_posts = intent.intent_type in ("hiring_post", "experimental")
                if prefer_posts:
                    links = [l for l in links if l.discovery_kind == "hiring_post"] or links
                for link in links:
                    if link.source_url in context.seen_urls:
                        continue
                    context.seen_urls.add(link.source_url)
                    page, phits = fetch_with_backoff(
                        link.source_url,
                        delay=self.config.delay_seconds,
                        backoff_base=self.config.rate_limit_backoff_seconds,
                        max_retries=self.config.rate_limit_max_retries,
                    )
                    stats.rate_limit_hits += phits
                    stats.pages_fetched += 1
                    if page.rate_limited:
                        logger.warning("Indexed page fetch rate limited")
                        break
                    if not page.html:
                        results.append(link)
                        continue
                    if link.discovery_kind == "job_listing":
                        detailed = parse_job_detail_html(page.html, link.source_url)
                        results.append(detailed or link)
                    else:
                        posts = parse_hiring_post_html(
                            page.html,
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
