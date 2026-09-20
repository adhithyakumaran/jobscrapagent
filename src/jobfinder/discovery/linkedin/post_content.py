from __future__ import annotations

import logging
import time
from urllib.parse import quote

from jobfinder.config import LinkedInSourceConfig
from jobfinder.discovery.base import DiscoveryContext, ProviderRunStats
from jobfinder.extraction.linkedin import parse_hiring_post_html
from jobfinder.models import RawCandidate

logger = logging.getLogger(__name__)


def discover_hiring_posts_playwright(
    page,
    intents: list,
    config: LinkedInSourceConfig,
    context: DiscoveryContext,
    stats: ProviderRunStats,
    results: list[RawCandidate],
) -> None:
    for intent in intents:
        stats.intents_executed += 1
        query = intent.query_string()
        search_url = (
            "https://www.linkedin.com/search/results/content/?"
            f"keywords={quote(query)}&origin=GLOBAL_SEARCH_HEADER"
        )
        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
            time.sleep(config.delay_seconds)
            stats.pages_fetched += 1
        except Exception as exc:
            logger.debug("Content search navigation failed: %s", exc)
            continue

        links: list[str] = []
        for link in page.query_selector_all("a[href*='/posts/']"):
            href = link.get_attribute("href") or ""
            if href.startswith("/"):
                href = "https://www.linkedin.com" + href.split("?")[0]
            if "/posts/" not in href:
                continue
            if href in context.seen_urls:
                continue
            links.append(href)
            if len(links) >= config.max_posts_per_intent:
                break

        for href in links:
            context.seen_urls.add(href)
            try:
                page.goto(href, wait_until="domcontentloaded", timeout=30000)
                time.sleep(config.delay_seconds)
                stats.pages_fetched += 1
            except Exception:
                continue
            posts = parse_hiring_post_html(
                page.content(),
                href,
                location_hints=[intent.location],
            )
            results.extend(posts)
            if len(results) >= config.max_results_per_intent:
                return
