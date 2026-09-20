from __future__ import annotations

import re
from dataclasses import dataclass, field

from jobfinder.config import ProfileConfig, is_any
from jobfinder.freshness import freshness_bucket
from jobfinder.models import JobOpportunity


@dataclass
class ScoreBreakdown:
    total: float = 0.0
    factors: dict[str, float] = field(default_factory=dict)
    penalties: dict[str, float] = field(default_factory=dict)

    def add(self, name: str, value: float) -> None:
        self.factors[name] = value
        self.total += value

    def penalize(self, name: str, value: float) -> None:
        self.penalties[name] = value
        self.total -= value


SENIOR_PATTERN = re.compile(
    r"\b(senior|sr\.?|lead|principal|director|manager|head of|architect)\b",
    re.I,
)
YEARS_PATTERN = re.compile(r"\b(\d+)\s*\+\s*years?\b", re.I)


def _normalize_text(s: str | None) -> str:
    return (s or "").lower()


def _location_matches(job_loc: str | None, profile_locs: list[str]) -> bool:
    if not job_loc:
        return False
    jl = job_loc.lower()
    for loc in profile_locs:
        ll = loc.lower()
        if ll in jl or jl in ll:
            return True
        if "remote" in ll and "remote" in jl:
            return True
        if "india" in ll and "india" in jl:
            return True
    return False


def _text_contains_any(text: str, terms: list[str]) -> bool:
    t = text.lower()
    return any(term.lower() in t for term in terms if term)


def _fresher_signals(text: str) -> bool:
    signals = [
        "fresher",
        "freshers",
        "entry level",
        "entry-level",
        "graduate",
        "0-1",
        "0 to 1",
        "trainee",
        "campus",
        "no experience",
        "0 year",
    ]
    return any(s in text for s in signals)


class RelevanceEngine:
    """Transparent weighted scoring against profile — not a hiring decision."""

    def __init__(self, profile: ProfileConfig) -> None:
        self.profile = profile

    def score(self, job: JobOpportunity) -> tuple[float, float, ScoreBreakdown]:
        breakdown = ScoreBreakdown()
        text = " ".join(
            filter(
                None,
                [
                    job.job_title,
                    job.description,
                    job.hiring_signal,
                    job.location,
                    job.domain,
                ],
            )
        )
        text_l = _normalize_text(text)

        # Fresher / entry-level
        if job.is_fresher or _fresher_signals(text_l):
            breakdown.add("fresher_entry", 15.0)
            job.is_fresher = True
        if job.is_entry_level or "entry" in text_l or "junior" in text_l:
            breakdown.add("entry_level", 10.0)
            job.is_entry_level = True

        # Location
        if _location_matches(job.location, self.profile.candidate.locations):
            breakdown.add("location", 20.0)

        # Experience range
        if job.experience_max is not None and job.experience_max <= 1:
            breakdown.add("experience_max", 12.0)
        elif job.experience_min is not None and job.experience_min == 0:
            breakdown.add("experience_min", 10.0)

        # Role match
        roles = self.profile.candidate.preferred_roles
        if not is_any(roles):
            if _text_contains_any(text_l, roles) or (
                job.job_title and _text_contains_any(job.job_title, roles)
            ):
                breakdown.add("role", 15.0)
        else:
            breakdown.add("role_any", 5.0)

        # Domain match
        domains = self.profile.candidate.target_domains
        if not is_any(domains):
            if job.domain and _text_contains_any(job.domain, domains):
                breakdown.add("domain", 12.0)
            elif _text_contains_any(text_l, domains):
                breakdown.add("domain_text", 10.0)
        else:
            breakdown.add("domain_any", 3.0)

        # Education hint
        edu = self.profile.candidate.education
        if edu.degree and edu.degree.lower() in text_l:
            breakdown.add("education_degree", 4.0)
        if edu.branch and edu.branch.lower() in text_l:
            breakdown.add("education_branch", 4.0)
        if edu.graduation_year and str(edu.graduation_year) in text_l:
            breakdown.add("graduation_year", 5.0)

        # Hiring signal
        if job.hiring_signal:
            breakdown.add("hiring_signal", 8.0)
        hire_words = ["hiring", "opening", "vacancy", "walk-in", "walk in", "apply"]
        if any(w in text_l for w in hire_words):
            breakdown.add("hiring_language", 6.0)

        # Application method
        if job.application_url or job.contact_email or job.application_method:
            breakdown.add("application_available", 10.0)

        # Freshness (unknown posted time — no invented freshness boost)
        if job.posted_at:
            bucket = freshness_bucket(job.posted_at)
            job.freshness_bucket = bucket
            freshness_points = {
                "very_new": 15.0,
                "new": 12.0,
                "recent": 8.0,
                "older": 2.0,
            }
            breakdown.add("freshness", freshness_points.get(bucket.value, 0))
        else:
            job.freshness_bucket = None

        # LinkedIn primary source — small boost only
        if job.source and "linkedin" in job.source.lower():
            breakdown.add("source_linkedin", 3.0)

        # Penalties
        excluded = self.profile.candidate.excluded_keywords
        if _text_contains_any(text_l, excluded):
            breakdown.penalize("excluded_keyword", 40.0)

        if SENIOR_PATTERN.search(text_l):
            breakdown.penalize("senior_title", 25.0)

        years = YEARS_PATTERN.findall(text_l)
        for y in years:
            if int(y) >= 3:
                breakdown.penalize("years_required", 20.0)
                break

        if job.experience_min is not None and job.experience_min >= 3:
            breakdown.penalize("experience_min_high", 25.0)

        # Confidence: how much structured data we have
        confidence = 0.0
        if job.company_name:
            confidence += 15
        if job.job_title:
            confidence += 15
        if job.location:
            confidence += 15
        if job.posted_at:
            confidence += 10
        if job.application_url or job.contact_email:
            confidence += 20
        if job.description and len(job.description) > 40:
            confidence += 15
        if job.hiring_signal:
            confidence += 10
        confidence = min(100.0, confidence)

        relevance = max(0.0, min(100.0, breakdown.total))
        return relevance, confidence, breakdown
