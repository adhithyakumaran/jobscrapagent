from __future__ import annotations

import logging

from jobfinder.config import LinkedInSourceConfig
from jobfinder.discovery.base import DiscoveryContext, ProviderRunStats
from jobfinder.discovery.linkedin.guest import LinkedInGuestProvider
from jobfinder.discovery.linkedin.http_client import load_cookie_header
from jobfinder.models import RawCandidate

logger = logging.getLogger(__name__)


class LinkedInSessionProvider:
    """Wraps guest fetches with optional user-supplied session cookies."""

    name = "linkedin_session"

    def __init__(self, config: LinkedInSourceConfig) -> None:
        self.config = config
        self._guest = LinkedInGuestProvider(config)
        self._cookie_headers = load_cookie_header(config.session_cookie_file)

    def discover(
        self,
        context: DiscoveryContext,
    ) -> tuple[list[RawCandidate], ProviderRunStats]:
        if not self._cookie_headers:
            return [], ProviderRunStats(
                provider=self.name,
                success=False,
                error="no session cookie file configured",
            )
        # Session uses same guest logic; cookie injection handled in future httpx wrapper
        logger.info("Session provider: using cookie file (guest transport)")
        return self._guest.discover(context)
