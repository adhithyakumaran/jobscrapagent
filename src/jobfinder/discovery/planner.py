from __future__ import annotations

import re
from dataclasses import dataclass

from jobfinder.config import ProfileConfig
from jobfinder.matching.intents import SearchIntent, generate_search_intents

HIGH_VALUE_HIRING = {
    "we are hiring",
    "we're hiring",
    "hiring",
    "immediate hiring",
    "urgent hiring",
    "walk-in",
    "walk in",
    "job opening",
    "send resume",
    "dm resume",
}
HIGH_VALUE_EXP = {"fresher", "freshers", "entry level", "graduate", "0-1 years", "campus"}


def normalize_query(q: str) -> str:
    s = q.lower().strip()
    s = s.replace("we're", "we are")
    s = re.sub(r"[-']", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


@dataclass
class PlannedIntents:
    generated: int
    deduplicated: int
    selected: list[SearchIntent]
    scores: dict[str, float]


def _intent_score(intent: SearchIntent, profile: ProfileConfig) -> float:
    score = 1.0
    if intent.hiring_term.lower() in HIGH_VALUE_HIRING:
        score += 3.0
    if intent.experience_term.lower() in HIGH_VALUE_EXP:
        score += 2.5
    if intent.location in profile.candidate.locations:
        score += 2.0
    if intent.domain_term.lower() != "any":
        score += 1.0
    if intent.role_term.lower() != "any":
        score += 1.0
    return score


def plan_search_intents(
    profile: ProfileConfig,
    budget: int,
) -> PlannedIntents:
    all_intents = generate_search_intents(profile)
    generated = len(all_intents)

    best_by_query: dict[str, SearchIntent] = {}
    scores: dict[str, float] = {}
    for intent in all_intents:
        q = normalize_query(intent.query_string())
        sc = _intent_score(intent, profile)
        if q not in best_by_query or sc > scores.get(q, 0):
            best_by_query[q] = intent
            scores[q] = sc

    deduplicated = len(best_by_query)
    ranked = sorted(best_by_query.values(), key=lambda i: scores[normalize_query(i.query_string())], reverse=True)
    selected = ranked[:budget]
    return PlannedIntents(
        generated=generated,
        deduplicated=deduplicated,
        selected=selected,
        scores=scores,
    )
