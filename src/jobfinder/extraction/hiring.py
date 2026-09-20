from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from jobfinder.extraction.experience import parse_experience
from jobfinder.extraction.patterns import EMAIL_RE, PHONE_RE

SignalStrength = Literal["high_hiring_signal", "medium_hiring_signal", "low_hiring_signal"]

HIRING_PHRASES = [
    r"we\s*'?re\s+hiring",
    r"we are hiring",
    r"\bis hiring\b",
    r"hiring\s+freshers?",
    r"looking for\s+graduates?",
    r"looking for\s+freshers?",
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

LOW_SIGNAL_PATTERNS = [
    r"career advice",
    r"job search tips",
    r"happy to announce(?!.*hiring)",
    r"celebrat",
    r"employee of the month",
    r"congratulations",
    r"repost if you",
    r"#opentowork",
    r"looking for job",
    r"seeking opportunities",
]

MEDIUM_SIGNAL_PATTERNS = [
    r"looking for candidates",
    r"openings available",
    r"hiring announcement",
    r"we are expanding",
]

HIGH_SIGNAL_PATTERNS = [
    r"we are hiring",
    r"we\s*'?re\s+hiring",
    r"send (your )?resume",
    r"send (your )?cv",
    r"dm (me )?your resume",
    r"dm resume",
    r"apply here",
    r"walk-?in",
    r"immediate (hiring|requirement|joiner)",
    r"urgent (hiring|requirement)",
    r"freshers can apply",
]

HIRING_REGEX = re.compile("|".join(f"({p})" for p in HIRING_PHRASES), re.I)
ROLE_LIST_RE = re.compile(
    r"(?:openings?|hiring|positions?)\s+for\s+(.+?)\s+roles?\b",
    re.I,
)
ROLE_LIST_LOOSE_RE = re.compile(
    r"(?:openings?|hiring|positions?)\s+for\s+([^.!?\n]{3,120})",
    re.I,
)
# Allow tech tokens like .NET, C++, etc. in role lists
ROLE_TOKEN_RE = re.compile(r"^[\w.#+\-]{2,40}$")
TITLE_RE = re.compile(
    r"(?:for|role[s]?:?)\s+([A-Za-z][A-Za-z0-9 /\-]{3,60})",
    re.I,
)
COMPANY_RE = re.compile(
    r"^([A-Z][A-Za-z0-9 &.\-]{2,60})(?:\s+is|\s+are|\s+has)",
    re.M,
)
RECRUITER_RE = re.compile(
    r"(?:I'm|I am)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),?\s+(?:talent|hr|recruiter)",
    re.I,
)
SALARY_RE = re.compile(
    r"(?:₹|rs\.?|inr|lpa|lakhs?|salary)\s*[\d,.]+\s*(?:lpa|lakhs?|per month|pm)?",
    re.I,
)
EMPLOYMENT_RE = re.compile(r"\b(full[\s-]?time|part[\s-]?time|contract|internship|wfh|remote)\b", re.I)

ROLE_STOPWORDS = {
    "multiple",
    "various",
    "several",
    "many",
    "all",
    "the",
    "our",
    "team",
}


@dataclass
class HiringAnalysis:
    is_hiring_related: bool
    hiring_signal: str | None = None
    hiring_signal_strength: SignalStrength | None = None
    company_name: str | None = None
    recruiter_name: str | None = None
    job_title: str | None = None
    location: str | None = None
    skills: list[str] = field(default_factory=list)
    salary_text: str | None = None
    employment_type: str | None = None
    application_method: str | None = None
    application_url: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    contact_instructions: str | None = None
    experience_min: int | None = None
    experience_max: int | None = None
    is_fresher: bool | None = None
    is_entry_level: bool | None = None


def classify_hiring_signal_strength(text: str) -> SignalStrength:
    lower = text.lower()
    for pat in LOW_SIGNAL_PATTERNS:
        if re.search(pat, lower):
            return "low_hiring_signal"
    for pat in HIGH_SIGNAL_PATTERNS:
        if re.search(pat, lower):
            return "high_hiring_signal"
    for pat in MEDIUM_SIGNAL_PATTERNS:
        if re.search(pat, lower):
            return "medium_hiring_signal"
    if HIRING_REGEX.search(lower):
        return "medium_hiring_signal"
    return "low_hiring_signal"


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


def _looks_like_role(token: str) -> bool:
    t = token.strip()
    if not t or t.lower() in ROLE_STOPWORDS:
        return False
    if len(t.split()) > 5:
        return False
    return bool(ROLE_TOKEN_RE.match(t))


def split_multi_role_post(text: str) -> list[str | None]:
    """Return role titles to split on, or [None] for single opportunity."""
    sm = ROLE_LIST_RE.search(text) or ROLE_LIST_LOOSE_RE.search(text)
    if not sm:
        return [None]
    chunk = sm.group(1)
    roles = [s.strip() for s in re.split(r",\s*|\s*/\s*|\s+and\s+", chunk) if s.strip()]
    cleaned = []
    for r in roles:
        r = re.sub(r"\s+roles?\s*$", "", r, flags=re.I).strip()
        if _looks_like_role(r):
            cleaned.append(r)
    roles = cleaned
    if len(roles) <= 1:
        return [None]
    return roles


def analyze_hiring_text(
    text: str,
    location_hints: list[str] | None = None,
    company_hint: str | None = None,
    title_hint: str | None = None,
    recruiter_hint: str | None = None,
) -> HiringAnalysis:
    lower = text.lower()
    strength = classify_hiring_signal_strength(text)
    signal = _detect_signal(lower)
    is_hiring = strength != "low_hiring_signal" and signal is not None

    exp_min, exp_max, is_fresher, is_entry = parse_experience(text)
    emails = EMAIL_RE.findall(text)
    email = emails[0] if emails else None
    phones = PHONE_RE.findall(text)
    phone = phones[0].strip() if phones else None

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

    recruiter = recruiter_hint
    if not recruiter:
        rm = RECRUITER_RE.search(text)
        if rm:
            recruiter = rm.group(1).strip()

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
    sm = ROLE_LIST_RE.search(text)
    if sm:
        chunk = sm.group(1)
        skills = [s.strip() for s in re.split(r",|/| and ", chunk) if s.strip()]

    salary_m = SALARY_RE.search(text)
    salary = salary_m.group(0) if salary_m else None
    emp_m = EMPLOYMENT_RE.search(text)
    employment = emp_m.group(1) if emp_m else None

    if strength == "low_hiring_signal":
        is_hiring = False

    return HiringAnalysis(
        is_hiring_related=is_hiring,
        hiring_signal=signal,
        hiring_signal_strength=strength,
        company_name=company,
        recruiter_name=recruiter,
        job_title=title,
        location=location,
        skills=skills,
        salary_text=salary,
        employment_type=employment,
        application_method=app_method,
        application_url=app_url,
        contact_email=email,
        contact_phone=phone,
        contact_instructions=None,
        experience_min=exp_min,
        experience_max=exp_max,
        is_fresher=is_fresher,
        is_entry_level=is_entry,
    )
