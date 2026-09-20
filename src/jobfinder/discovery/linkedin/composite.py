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
    "guest": LinkedInGuestProvider,
    "playwright": LinkedInPlaywrightProvider,
    "indexed": LinkedInIndexedProvider,
    "session": LinkedInSessionProvider,
}


class LinkedInCompositeProvider:
    name = "linkedin"

    def __init__(self, config: LinkedInSourceConfig) -> None:
        self.config = config
        self._providers = []
        for key in config.providers:
            cls = PROVIDER_MAP.get(key)
            if cls:
                self._providers.append(cls(config))
        if config.session_cookie_file:
            self._providers.insert(0, LinkedInSessionProvider(config))

    def discover(
        self,
        context: DiscoveryContext,
    ) -> tuple[list[RawCandidate], list[ProviderRunStats]]:
        all_candidates: list[RawCandidate] = []
        run_stats: list[ProviderRunStats] = []
        for provider in self._providers:
            logger.info("LinkedIn provider: %s", provider.name)
            batch, st = provider.discover(context)
            run_stats.append(st)
            if batch:
                all_candidates.extend(batch)
                logger.info(
                    "  %s: %s candidates (%s pages)",
                    provider.name,
                    st.candidates,
                    st.pages_fetched,
                )
            elif st.error:
                logger.info("  %s failed: %s — trying next", provider.name, st.error)
            else:
                logger.info("  %s: no results", provider.name)
        return all_candidates, run_stats
