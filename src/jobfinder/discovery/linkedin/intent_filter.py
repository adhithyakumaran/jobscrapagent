from __future__ import annotations

from jobfinder.matching.intents import IntentType, SearchIntent

POST_TYPES = frozenset({"hiring_post", "experimental"})
LISTING_TYPES = frozenset({"job_listing", "role_domain"})


def intents_for_posts(intents: list[SearchIntent]) -> list[SearchIntent]:
    return [i for i in intents if i.intent_type in POST_TYPES]


def intents_for_listings(intents: list[SearchIntent]) -> list[SearchIntent]:
    return [i for i in intents if i.intent_type in LISTING_TYPES]
