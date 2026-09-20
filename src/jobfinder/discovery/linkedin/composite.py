from __future__ import annotations

import logging

from jobfinder.config import LinkedInSourceConfig
from jobfinder.discovery.base import DiscoveryContext, ProviderRunStats
from jobfinder.discovery.linkedin.guest import LinkedInGuestProvider
from jobfinder.discovery.linkedin.indexed import LinkedInIndexedProvider
from jobfinder.discovery.linkedin.playwright_provider import LinkedInPlaywrightProvider
from jobfinder.discovery.linkedin.session import LinkedInSessionProvider
from jobfinder.models import RawCandidate

logger = logging.getLogger(__name__)

PROVIDER_MAP = {
    "playwright": LinkedInPlaywrightProvider,
    "session": LinkedInSessionProvider,
    "guest": LinkedInGuestProvider,
    "indexed": LinkedInIndexedProvider,
}

# Priority order for content/hiring posts first
DEFAULT_ORDER = ["playwright", "session", "guest", "indexed"]


class LinkedInCompositeProvider:
    name = "linkedin"

    def __init__(self, config: LinkedInSourceConfig) -> None:
        self.config = config
        order = config.providers or DEFAULT_ORDER
        seen: set[str] = set()
        self._providers = []
        for key in order:
            if key in seen:
                continue
            cls = PROVIDER_MAP.get(key)
            if not cls:
                continue
            if key == "session" and not config.session_cookie_file:
                continue
            seen.add(key)
            self._providers.append(cls(config))

    def discover(
        self,
        context: DiscoveryContext,
    ) -> tuple[list[RawCandidate], list[ProviderRunStats]]:
        all_candidates: list[RawCandidate] = []
        run_stats: list[ProviderRunStats] = []
        for provider in self._providers:
            logger.info("LinkedIn provider: %s", provider.name)
            try:
                batch, st = provider.discover(context)
            except Exception as exc:
                st = ProviderRunStats(provider=provider.name, success=False, error=str(exc))
                batch = []
            run_stats.append(st)
            if batch:
                all_candidates.extend(batch)
                logger.info(
                    "  %s: %s candidates (%s pages, rate_limits=%s)",
                    provider.name,
                    st.candidates,
                    st.pages_fetched,
                    st.rate_limit_hits,
                )
            elif st.error:
                logger.info("  %s failed: %s — trying next", provider.name, st.error)
            else:
                logger.info("  %s: no results", provider.name)
        return all_candidates, run_stats
