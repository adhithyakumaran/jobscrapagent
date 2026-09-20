from __future__ import annotations

import logging

from jobfinder.config import LinkedInSourceConfig
from jobfinder.discovery.base import DiscoveryContext, ProviderRunStats
from jobfinder.discovery.linkedin.guest import LinkedInGuestProvider
from jobfinder.discovery.linkedin.http_client import load_cookie_header
from jobfinder.discovery.linkedin.intent_filter import intents_for_posts
from jobfinder.discovery.linkedin.post_content import discover_hiring_posts_playwright
from jobfinder.models import RawCandidate

logger = logging.getLogger(__name__)


class LinkedInSessionProvider:
    """Session cookies + Playwright content search for hiring posts."""

    name = "linkedin_session"

    def __init__(self, config: LinkedInSourceConfig) -> None:
        self.config = config
        self._guest = LinkedInGuestProvider(config)
        self._cookie_headers = load_cookie_header(config.session_cookie_file)

    def discover(
        self,
        context: DiscoveryContext,
    ) -> tuple[list[RawCandidate], ProviderRunStats]:
        results: list[RawCandidate] = []
        stats = ProviderRunStats(provider=self.name)

        if not self._cookie_headers:
            stats.success = False
            stats.error = "no session cookie file configured"
            return results, stats

        post_intents = intents_for_posts(context.intents)
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.info("Session provider: playwright missing, falling back to guest with cookies")
            return self._guest.discover(context)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.config.playwright_headless)
                context_pw = browser.new_context(extra_http_headers=self._cookie_headers)
                page = context_pw.new_page()
                if post_intents:
                    discover_hiring_posts_playwright(
                        page, post_intents, self.config, context, stats, results
                    )
                browser.close()
            stats.candidates = len(results)
            stats.success = len(results) > 0 or stats.pages_fetched > 0
        except Exception as exc:
            stats.success = False
            stats.error = str(exc)
            logger.warning("Session provider failed: %s", exc)
        return results, stats
