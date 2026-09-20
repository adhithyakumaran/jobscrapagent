from __future__ import annotations

import re
from dataclasses import dataclass, field

from jobfinder.extraction.experience import parse_experience
from jobfinder.extraction.patterns import EMAIL_RE

HIRING_PHRASES = [
    r"we\s*'?re\s+hiring",
    r"we are hiring",
    r"hiring\s+freshers?",
    r"looking for\s+graduates?",
    r"immediate hiring",
    r"urgent hiring",
    r"walk-?in",
    r"send your resume",
    r"send resume",
    r"send your cv",
    r"send cv",
    r"dm\s+(me\s+)?your resume",
    r"dm resume",
    r"comment interested",
    r"apply here",
    r"multiple openings",
    r"urgent requirement",
    r"freshers can apply",
    r"interested candidates",
    r"openings for",
    r"job opening",
]

HIRING_REGEX = re.compile("|".join(f"({p})" for p in HIRING_PHRASES), re.I)
SKILL_LIST_RE = re.compile(
    r"openings?\s+for\s+([^.!\n]+)",
    re.I,
)
TITLE_RE = re.compile(
    r"(?:for|role[s]?:?)\s+([A-Za-z][A-Za-z0-9 /\-]{3,60})",
    re.I,
)
COMPANY_RE = re.compile(
    r"^([A-Z][A-Za-z0-9 &.\-]{2,60})(?:\s+is|\s+are|\s+has)",
    re.M,
)


@dataclass
class HiringAnalysis:
    is_hiring_related: bool
    hiring_signal: str | None = None
    company_name: str | None = None
    job_title: str | None = None
    location: str | None = None
    skills: list[str] = field(default_factory=list)
    application_method: str | None = None
    application_url: str | None = None
    contact_email: str | None = None
    contact_instructions: str | None = None
    experience_min: int | None = None
    experience_max: int | None = None
    is_fresher: bool | None = None
    is_entry_level: bool | None = None


def _detect_signal(lower: str) -> str | None:
    mapping = [
        ("walk-in", "walk_in"),
        ("walk in", "walk_in"),
        ("dm your resume", "dm_resume"),
        ("dm resume", "dm_resume"),
        ("comment interested", "comment_interested"),
        ("send your cv", "email_resume"),
        ("send cv", "email_resume"),
        ("send resume", "email_resume"),
        ("apply here", "apply_link"),
        ("google form", "application_form"),
        ("multiple openings", "multiple_openings"),
        ("openings for", "multiple_openings"),
        ("we are hiring", "we_are_hiring"),
        ("we're hiring", "we_are_hiring"),
        ("urgent requirement", "urgent_requirement"),
        ("freshers can apply", "fresher_apply"),
    ]
    for phrase, sig in mapping:
        if phrase in lower:
            return sig
    if HIRING_REGEX.search(lower):
        return "hiring_post"
    return None


def analyze_hiring_text(
    text: str,
    location_hints: list[str] | None = None,
    company_hint: str | None = None,
    title_hint: str | None = None,
) -> HiringAnalysis:
    lower = text.lower()
    signal = _detect_signal(lower)
    is_hiring = signal is not None

    exp_min, exp_max, is_fresher, is_entry = parse_experience(text)
    emails = EMAIL_RE.findall(text)
    email = emails[0] if emails else None

    app_method = None
    if signal == "dm_resume":
        app_method = "dm_resume"
    elif signal == "email_resume" or email:
        app_method = "email"
    elif signal == "walk_in":
        app_method = "walk_in"
    elif signal == "comment_interested":
        app_method = "comment"
    elif "forms.gle" in lower or "google form" in lower:
        app_method = "google_form"

    url_match = re.search(r"https?://[^\s\])>\"']+", text)
    app_url = url_match.group(0) if url_match else None

    company = company_hint
    if not company:
        cm = COMPANY_RE.search(text)
        if cm:
            company = cm.group(1).strip()

    title = title_hint
    if not title:
        tm = TITLE_RE.search(text)
        if tm:
            title = tm.group(1).strip()

    location = None
    if location_hints:
        for loc in location_hints:
            if loc.lower() in lower:
                location = loc
                break
    if not location:
        loc_m = re.search(r"\b(?:in|at)\s+([A-Za-z][A-Za-z\s]{2,40})", text)
        if loc_m:
            location = loc_m.group(1).strip()

    skills: list[str] = []
    sm = SKILL_LIST_RE.search(text)
    if sm:
        chunk = sm.group(1)
        skills = [s.strip() for s in re.split(r",| and ", chunk) if s.strip()]

    return HiringAnalysis(
        is_hiring_related=is_hiring,
        hiring_signal=signal,
        company_name=company,
        job_title=title,
        location=location,
        skills=skills,
        application_method=app_method,
        application_url=app_url,
        contact_email=email,
        contact_instructions=None,
        experience_min=exp_min,
        experience_max=exp_max,
        is_fresher=is_fresher,
        is_entry_level=is_entry,
    )


def split_multi_role_post(text: str, base_url: str, source: str) -> list[tuple[str, str | None]]:
    """Return (snippet, optional role title) for multiple openings in one post."""
    sm = SKILL_LIST_RE.search(text)
    if not sm:
        return [(text, None)]
    chunk = sm.group(1)
    roles = [s.strip() for s in re.split(r",| and ", chunk) if s.strip()]
    if len(roles) <= 1:
        return [(text, None)]
    return [(text, role) for role in roles]
