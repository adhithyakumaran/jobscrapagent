from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from jobfinder.matching.intents import SearchIntent
from jobfinder.models import RawCandidate


@dataclass
class ProviderRunStats:
    provider: str
    success: bool = True
    error: str | None = None
    intents_executed: int = 0
    pages_fetched: int = 0
    candidates: int = 0


@dataclass
class DiscoveryContext:
    intents: list[SearchIntent]
    seen_urls: set[str] = field(default_factory=set)


class DiscoveryProvider(Protocol):
    name: str

    def discover(
        self,
        context: DiscoveryContext,
    ) -> tuple[list[RawCandidate], ProviderRunStats]: ...
