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
    "job opening",
    "job openings",
    "vacancy",
    "vacancies",
    "recruitment",
    "immediate hiring",
    "urgent hiring",
    "immediate joiner",
    "walk-in",
    "walk in",
    "send resume",
    "send CV",
    "DM resume",
    "apply now",
    "looking for candidates",
    "interested candidates",
    "comment interested",
    "urgent requirement",
    "freshers can apply",
    "multiple openings",
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


def _experience_phrases_for_profile(profile: ProfileConfig) -> list[str]:
    phrases = list(EXPERIENCE_PHRASES)
    year = profile.candidate.education.graduation_year
    if year:
        phrases.append(f"{year} graduate")
    return phrases


def generate_search_intents(
    profile: ProfileConfig,
    max_intents: int | None = None,
) -> list[SearchIntent]:
    locations = profile.candidate.locations or ["Remote"]
    domains = _domain_terms(profile)
    roles = _role_terms(profile)
    experience = _experience_phrases_for_profile(profile)

    intents: list[SearchIntent] = []
    for exp in experience:
        for hire in HIRING_PHRASES:
            for loc in locations:
                if domains == ["any"] and roles == ["any"]:
                    intents.append(
                        SearchIntent(
                            experience_term=exp,
                            hiring_term=hire,
                            location=loc,
                            domain_term="any",
                            role_term="any",
                        )
                    )
                    if max_intents and len(intents) >= max_intents:
                        return intents
                else:
                    dom_iter = domains if domains != ["any"] else ["any"]
                    role_iter = roles if roles != ["any"] else ["any"]
                    for dom in dom_iter:
                        for role in role_iter:
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
