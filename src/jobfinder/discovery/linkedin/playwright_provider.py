from __future__ import annotations

import logging
import time
from urllib.parse import quote

from jobfinder.config import LinkedInSourceConfig
from jobfinder.discovery.base import DiscoveryContext, ProviderRunStats
from jobfinder.discovery.linkedin.intent_filter import intents_for_listings, intents_for_posts
from jobfinder.discovery.linkedin.post_content import discover_hiring_posts_playwright
from jobfinder.extraction.linkedin import parse_job_listing_html
from jobfinder.models import RawCandidate

logger = logging.getLogger(__name__)


class LinkedInPlaywrightProvider:
    name = "linkedin_playwright"

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
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            stats.success = False
            stats.error = "playwright not installed"
            return results, stats

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.config.playwright_headless)
                page = browser.new_page()

                if post_intents:
                    discover_hiring_posts_playwright(
                        page, post_intents, self.config, context, stats, results
                    )

                for intent in listing_intents[: max(1, len(listing_intents) // 2)]:
                    stats.intents_executed += 1
                    url = (
                        "https://www.linkedin.com/jobs/search/?"
                        f"keywords={quote(intent.query_string())}"
                        f"&location={quote(intent.location)}"
                    )
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=45000)
                        time.sleep(self.config.delay_seconds)
                        stats.pages_fetched += 1
                        for cand in parse_job_listing_html(page.content()):
                            if cand.source_url in context.seen_urls:
                                continue
                            context.seen_urls.add(cand.source_url)
                            results.append(cand)
                    except Exception:
                        logger.debug("Playwright job search skipped for intent")

                browser.close()
            stats.candidates = len(results)
            stats.success = len(results) > 0 or stats.pages_fetched > 0
        except Exception as exc:
            stats.success = False
            stats.error = str(exc)
            logger.warning("Playwright provider failed: %s", exc)
        return results, stats
