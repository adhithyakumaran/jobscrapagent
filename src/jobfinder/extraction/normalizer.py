from __future__ import annotations

import re
import uuid
from datetime import datetime

from jobfinder.freshness import freshness_bucket, utc_now
from jobfinder.models import JobOpportunity, RawCandidate

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"\+?\d[\d\s\-]{8,14}\d")
EXP_RANGE_RE = re.compile(
    r"(\d+)\s*[-–to]+\s*(\d+)\s*years?",
    re.I,
)
EXP_MIN_RE = re.compile(r"(\d+)\s*\+\s*years?", re.I)
FRESHER_RE = re.compile(
    r"\b(fresher|freshers|entry\s*level|graduate|0\s*[-–]?\s*1\s*year|trainee|campus)\b",
    re.I,
)


def detect_hiring_signal(text: str) -> str | None:
    lower = text.lower()
    signals = [
        ("walk-in", "walk_in"),
        ("walk in", "walk_in"),
        ("dm your resume", "dm_resume"),
        ("dm resume", "dm_resume"),
        ("send resume", "email_resume"),
        ("send cv", "email_resume"),
        ("google form", "application_form"),
        ("apply using", "application_form"),
        ("we are hiring", "we_are_hiring"),
        ("we're hiring", "we_are_hiring"),
        ("immediate hiring", "immediate_hiring"),
        ("multiple openings", "multiple_openings"),
        ("openings for", "multiple_openings"),
        ("job opening", "formal_job"),
    ]
    for phrase, signal in signals:
        if phrase in lower:
            return signal
    if "hiring" in lower:
        return "hiring_post"
    return None


def parse_experience(text: str) -> tuple[int | None, int | None, bool, bool]:
    is_fresher = bool(FRESHER_RE.search(text))
    is_entry = is_fresher or "entry" in text.lower() or "junior" in text.lower()
    exp_min, exp_max = None, None
    m = EXP_RANGE_RE.search(text)
    if m:
        exp_min, exp_max = int(m.group(1)), int(m.group(2))
    else:
        m2 = EXP_MIN_RE.search(text)
        if m2:
            exp_min = int(m2.group(1))
    if is_fresher and exp_max is None:
        exp_max = 1
        exp_min = 0
    return exp_min, exp_max, is_fresher, is_entry


def raw_to_opportunity(raw: RawCandidate) -> JobOpportunity:
    text = raw.raw_text
    email = raw.contact_email
    if not email:
        emails = EMAIL_RE.findall(text)
        email = emails[0] if emails else None

    phones = PHONE_RE.findall(text)
    phone = phones[0].strip() if phones else None

    exp_min, exp_max, is_fresher, is_entry = parse_experience(text)
    signal = detect_hiring_signal(text)

    title = raw.title_hint
    if not title and signal == "formal_job":
        first_line = text.split("\n")[0].strip()
        if len(first_line) < 120:
            title = first_line

    posted = raw.posted_at or utc_now()
    job = JobOpportunity(
        id=str(uuid.uuid4()),
        source=raw.source,
        source_url=raw.source_url,
        company_name=raw.company_hint,
        job_title=title,
        description=text,
        location=raw.location_hint,
        experience_min=exp_min,
        experience_max=exp_max,
        domain=raw.domain_hint,
        posted_at=posted,
        discovered_at=utc_now(),
        application_url=raw.application_url,
        application_method=raw.application_method,
        contact_email=email,
        contact_phone=phone,
        is_fresher=is_fresher,
        is_entry_level=is_entry,
        hiring_signal=signal,
        freshness_bucket=freshness_bucket(posted),
    )
    return job
