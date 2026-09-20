from __future__ import annotations

import re
from dataclasses import dataclass, field

from jobfinder.config import IntentMixConfig, ProfileConfig
from jobfinder.matching.intents import (
    IntentType,
    SearchIntent,
    generate_all_intents_by_type,
)

HIGH_VALUE_POST = {
    "we are hiring",
    "we're hiring",
    "hiring freshers",
    "dm your resume",
    "dm resume",
    "walk-in interview",
    "walk in",
    "send resume",
    "immediate hiring",
    "urgent hiring",
}


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
    by_type_generated: dict[str, int] = field(default_factory=dict)
    by_type_selected: dict[str, int] = field(default_factory=dict)


def _intent_score(intent: SearchIntent, profile: ProfileConfig) -> float:
    score = 1.0
    if intent.intent_type == "hiring_post":
        score += 5.0
        if intent.post_phrase.lower() in HIGH_VALUE_POST:
            score += 4.0
    if intent.intent_type == "experimental":
        score += 2.0
    if intent.location in profile.candidate.locations:
        score += 2.0
    if intent.experience_term.lower() in {"fresher", "freshers", "entry level", "graduate"}:
        score += 2.0
    return score


def _dedupe_intents(intents: list[SearchIntent], profile: ProfileConfig) -> list[SearchIntent]:
    best: dict[str, SearchIntent] = {}
    scores: dict[str, float] = {}
    for intent in intents:
        key = f"{intent.intent_type}|{normalize_query(intent.query_string())}"
        sc = _intent_score(intent, profile)
        if key not in best or sc > scores.get(key, 0):
            best[key] = intent
            scores[key] = sc
    return list(best.values())


def plan_search_intents(
    profile: ProfileConfig,
    budget: int,
    mix: IntentMixConfig | None = None,
) -> PlannedIntents:
    from jobfinder.config import IntentMixConfig as Mix

    mix = mix or Mix()
    buckets = generate_all_intents_by_type(profile)
    generated = sum(len(v) for v in buckets.values())
    by_type_generated = {k: len(v) for k, v in buckets.items()}

    def rank_pool(pool: list[SearchIntent]) -> list[SearchIntent]:
        uniq = _dedupe_intents(pool, profile)
        return sorted(uniq, key=lambda i: _intent_score(i, profile), reverse=True)

    quotas = {
        "hiring_post": max(1, int(budget * mix.hiring_post)),
        "job_listing": max(1, int(budget * mix.job_listing)),
        "role_domain": max(0, int(budget * mix.role_domain)),
        "experimental": max(0, int(budget * mix.experimental)),
    }
    # Adjust to exact budget
    while sum(quotas.values()) > budget:
        for k in ("job_listing", "hiring_post", "experimental", "role_domain"):
            if quotas[k] > 1:
                quotas[k] -= 1
                if sum(quotas.values()) <= budget:
                    break
    while sum(quotas.values()) < budget:
        quotas["hiring_post"] += 1

    selected: list[SearchIntent] = []
    seen_keys: set[str] = set()
    for itype in ("hiring_post", "job_listing", "role_domain", "experimental"):
        pool = rank_pool(buckets.get(itype, []))
        count = 0
        for intent in pool:
            key = normalize_query(intent.query_string())
            if key in seen_keys:
                continue
            seen_keys.add(key)
            selected.append(intent)
            count += 1
            if count >= quotas.get(itype, 0):
                break

    if len(selected) < budget:
        for itype in ("hiring_post", "job_listing", "role_domain", "experimental"):
            for intent in rank_pool(buckets.get(itype, [])):
                key = normalize_query(intent.query_string())
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                selected.append(intent)
                if len(selected) >= budget:
                    break
            if len(selected) >= budget:
                break

    selected = selected[:budget]
    by_type_selected: dict[str, int] = {}
    for s in selected:
        by_type_selected[s.intent_type] = by_type_selected.get(s.intent_type, 0) + 1

    all_queries = set()
    for pool in buckets.values():
        for i in pool:
            all_queries.add(normalize_query(i.query_string()))

    return PlannedIntents(
        generated=generated,
        deduplicated=len(all_queries),
        selected=selected,
        scores={},
        by_type_generated=by_type_generated,
        by_type_selected=by_type_selected,
    )
