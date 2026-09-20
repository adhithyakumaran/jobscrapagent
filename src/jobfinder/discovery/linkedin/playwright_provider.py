from __future__ import annotations

import logging
import time

from jobfinder.config import LinkedInSourceConfig
from jobfinder.discovery.base import DiscoveryContext, ProviderRunStats
from jobfinder.extraction.linkedin import (
    build_jobs_search_url,
    parse_hiring_post_html,
    parse_job_listing_html,
)
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
                for intent in context.intents:
                    stats.intents_executed += 1
                    url = build_jobs_search_url(intent.query_string(), intent.location, start=0).replace(
                        "seeMoreJobPostings", "search"
                    )
                    if "/api/" in url:
                        url = (
                            "https://www.linkedin.com/jobs/search/?"
                            f"keywords={intent.query_string().replace(' ', '%20')}"
                            f"&location={intent.location.replace(' ', '%20')}"
                        )
                    page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    time.sleep(self.config.delay_seconds)
                    stats.pages_fetched += 1
                    html = page.content()
                    for cand in parse_job_listing_html(html):
                        if cand.source_url in context.seen_urls:
                            continue
                        context.seen_urls.add(cand.source_url)
                        results.append(cand)
                    # Content search for hiring posts (public search page)
                    post_q = f"{intent.hiring_term} {intent.experience_term} {intent.location}"
                    search_url = (
                        "https://www.linkedin.com/search/results/content/?"
                        f"keywords={post_q.replace(' ', '%20')}&origin=GLOBAL_SEARCH_HEADER"
                    )
                    try:
                        page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
                        time.sleep(self.config.delay_seconds)
                        stats.pages_fetched += 1
                        post_html = page.content()
                        for link in page.query_selector_all("a[href*='/posts/']"):
                            href = link.get_attribute("href") or ""
                            if href.startswith("/"):
                                href = "https://www.linkedin.com" + href
                            if href in context.seen_urls:
                                continue
                            context.seen_urls.add(href)
                            page.goto(href, wait_until="domcontentloaded", timeout=30000)
                            time.sleep(self.config.delay_seconds)
                            stats.pages_fetched += 1
                            posts = parse_hiring_post_html(
                                page.content(),
                                href,
                                location_hints=[intent.location],
                            )
                            results.extend(posts)
                            if len(results) >= self.config.max_results_per_intent:
                                break
                    except Exception:
                        logger.debug("Playwright content search skipped for intent")
                browser.close()
            stats.candidates = len(results)
            stats.success = len(results) > 0 or stats.pages_fetched > 0
        except Exception as exc:
            stats.success = False
            stats.error = str(exc)
            logger.warning("Playwright provider failed: %s", exc)
        return results, stats
