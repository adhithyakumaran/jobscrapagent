from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from jobfinder.config import ProfileConfig, is_any

IntentType = Literal["job_listing", "hiring_post", "role_domain", "experimental"]

EXPERIENCE_PHRASES = [
    "fresher",
    "freshers",
    "entry level",
    "graduate",
    "graduates",
    "0-1 years",
    "0 to 1 years",
    "trainee",
    "graduate trainee",
    "associate",
    "junior",
    "early career",
    "campus",
    "off campus",
    "recent graduate",
]

LISTING_HIRING_PHRASES = [
    "hiring",
    "job opening",
    "vacancy",
    "recruitment",
]

POST_INTENT_PHRASES = [
    "we are hiring",
    "we're hiring",
    "hiring freshers",
    "freshers can apply",
    "looking for freshers",
    "looking for graduates",
    "immediate hiring",
    "urgent hiring",
    "walk-in interview",
    "walk in",
    "send resume",
    "send CV",
    "DM resume",
    "DM your resume",
    "comment interested",
    "multiple openings",
    "job openings",
    "campus hiring",
    "off campus hiring",
]

EXPERIMENTAL_POST_PHRASES = [
    ("talent acquisition", "hiring"),
    ("recruiter", "hiring"),
    ("HR", "hiring"),
]


@dataclass(frozen=True)
class SearchIntent:
    intent_type: IntentType
    location: str
    post_phrase: str = ""
    experience_term: str = ""
    hiring_term: str = ""
    domain_term: str = "any"
    role_term: str = "any"

    def query_string(self) -> str:
        if self.intent_type == "hiring_post":
            parts = [self.post_phrase]
            if self.experience_term:
                parts.append(self.experience_term)
            parts.append(self.location)
            return " ".join(p for p in parts if p)

        if self.intent_type == "experimental":
            parts = [self.post_phrase, self.hiring_term, self.experience_term, self.location]
            return " ".join(p for p in parts if p)

        if self.intent_type == "role_domain":
            parts = []
            if self.role_term.lower() != "any":
                parts.append(self.role_term)
            if self.domain_term.lower() != "any":
                parts.append(self.domain_term)
            parts.append(self.experience_term)
            parts.append(self.location)
            return " ".join(p for p in parts if p)

        # job_listing — formal job search style
        parts = [self.experience_term, self.hiring_term]
        if self.role_term.lower() != "any":
            parts.append(self.role_term)
        if self.domain_term.lower() != "any":
            parts.append(self.domain_term)
        parts.append(self.location)
        return " ".join(p for p in parts if p)


def _experience_phrases_for_profile(profile: ProfileConfig) -> list[str]:
    phrases = list(EXPERIENCE_PHRASES)
    year = profile.candidate.education.graduation_year
    if year:
        phrases.append(f"{year} graduate")
    return phrases


def _locations(profile: ProfileConfig) -> list[str]:
    return profile.candidate.locations or ["Remote"]


def generate_hiring_post_intents(profile: ProfileConfig) -> list[SearchIntent]:
    locations = _locations(profile)
    experience = _experience_phrases_for_profile(profile)
    intents: list[SearchIntent] = []
    for phrase in POST_INTENT_PHRASES:
        for loc in locations:
            intents.append(
                SearchIntent(
                    intent_type="hiring_post",
                    location=loc,
                    post_phrase=phrase,
                )
            )
            for exp in ("fresher", "freshers", "graduate"):
                intents.append(
                    SearchIntent(
                        intent_type="hiring_post",
                        location=loc,
                        post_phrase=phrase,
                        experience_term=exp,
                    )
                )
    return intents


def generate_job_listing_intents(profile: ProfileConfig) -> list[SearchIntent]:
    locations = _locations(profile)
    experience = _experience_phrases_for_profile(profile)
    domains_any = is_any(profile.candidate.target_domains)
    roles_any = is_any(profile.candidate.preferred_roles)

    intents: list[SearchIntent] = []
    for exp in experience:
        for hire in LISTING_HIRING_PHRASES:
            for loc in locations:
                if domains_any and roles_any:
                    intents.append(
                        SearchIntent(
                            intent_type="job_listing",
                            location=loc,
                            experience_term=exp,
                            hiring_term=hire,
                        )
                    )
                else:
                    domains = (
                        ["any"]
                        if domains_any
                        else [d for d in profile.candidate.target_domains if d.strip()]
                    )
                    roles = (
                        ["any"]
                        if roles_any
                        else [r for r in profile.candidate.preferred_roles if r.strip()]
                    )
                    for dom in domains:
                        for role in roles:
                            intents.append(
                                SearchIntent(
                                    intent_type="job_listing",
                                    location=loc,
                                    experience_term=exp,
                                    hiring_term=hire,
                                    domain_term=dom,
                                    role_term=role,
                                )
                            )
    return intents


def generate_role_domain_intents(profile: ProfileConfig) -> list[SearchIntent]:
    if is_any(profile.candidate.target_domains) and is_any(profile.candidate.preferred_roles):
        return []

    locations = _locations(profile)
    experience = _experience_phrases_for_profile(profile)[:6]
    domains = (
        profile.candidate.target_domains
        if not is_any(profile.candidate.target_domains)
        else []
    )
    roles = (
        profile.candidate.preferred_roles if not is_any(profile.candidate.preferred_roles) else []
    )
    intents: list[SearchIntent] = []
    for loc in locations:
        for exp in experience:
            for dom in domains or ["any"]:
                for role in roles or ["any"]:
                    intents.append(
                        SearchIntent(
                            intent_type="role_domain",
                            location=loc,
                            experience_term=exp,
                            domain_term=dom,
                            role_term=role,
                        )
                    )
    return intents


def generate_experimental_intents(profile: ProfileConfig) -> list[SearchIntent]:
    locations = _locations(profile)
    intents: list[SearchIntent] = []
    for a, b in EXPERIMENTAL_POST_PHRASES:
        for loc in locations:
            for exp in ("fresher", "freshers", "entry level"):
                intents.append(
                    SearchIntent(
                        intent_type="experimental",
                        location=loc,
                        post_phrase=a,
                        hiring_term=b,
                        experience_term=exp,
                    )
                )
    return intents


def generate_all_intents_by_type(profile: ProfileConfig) -> dict[IntentType, list[SearchIntent]]:
    return {
        "hiring_post": generate_hiring_post_intents(profile),
        "job_listing": generate_job_listing_intents(profile),
        "role_domain": generate_role_domain_intents(profile),
        "experimental": generate_experimental_intents(profile),
    }


def generate_search_intents(
    profile: ProfileConfig,
    max_intents: int | None = None,
) -> list[SearchIntent]:
    """Legacy flat list (all types combined)."""
    combined: list[SearchIntent] = []
    for bucket in generate_all_intents_by_type(profile).values():
        combined.extend(bucket)
        if max_intents and len(combined) >= max_intents:
            return combined[:max_intents]
    return combined
