from __future__ import annotations

from dataclasses import dataclass

from jobfinder.config import ProfileConfig, is_any

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

HIRING_PHRASES = [
    "hiring",
    "we're hiring",
    "we are hiring",
    "immediate hiring",
    "immediate joiner",
    "urgent hiring",
    "job opening",
    "openings",
    "vacancy",
    "recruitment",
    "walk-in",
    "interview",
    "careers",
    "apply now",
    "send resume",
    "send CV",
    "DM resume",
    "interested candidates",
    "looking for candidates",
]


@dataclass(frozen=True)
class SearchIntent:
    experience_term: str
    hiring_term: str
    location: str
    domain_term: str
    role_term: str

    def query_string(self) -> str:
        parts = [self.hiring_term, self.experience_term]
        if self.role_term and self.role_term.lower() != "any":
            parts.append(self.role_term)
        if self.domain_term and self.domain_term.lower() != "any":
            parts.append(self.domain_term)
        parts.append(self.location)
        return " ".join(parts)


def _domain_terms(profile: ProfileConfig) -> list[str]:
    domains = profile.candidate.target_domains
    if is_any(domains):
        return ["any"]
    return [d for d in domains if d.strip()]


def _role_terms(profile: ProfileConfig) -> list[str]:
    roles = profile.candidate.preferred_roles
    if is_any(roles):
        return ["any"]
    return [r for r in roles if r.strip()]


def generate_search_intents(
    profile: ProfileConfig,
    max_intents: int | None = None,
) -> list[SearchIntent]:
    locations = profile.candidate.locations or ["Remote"]
    domains = _domain_terms(profile)
    roles = _role_terms(profile)

    intents: list[SearchIntent] = []
    for exp in EXPERIENCE_PHRASES:
        for hire in HIRING_PHRASES:
            for loc in locations:
                for dom in domains:
                    for role in roles:
                        intents.append(
                            SearchIntent(
                                experience_term=exp,
                                hiring_term=hire,
                                location=loc,
                                domain_term=dom,
                                role_term=role,
                            )
                        )
                        if max_intents and len(intents) >= max_intents:
                            return intents
    return intents
