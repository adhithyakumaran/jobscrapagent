from __future__ import annotations

import uuid

from jobfinder.extraction.experience import parse_experience
from jobfinder.extraction.hiring import analyze_hiring_text
from jobfinder.extraction.patterns import EMAIL_RE, PHONE_RE
from jobfinder.freshness import freshness_bucket, utc_now
from jobfinder.models import JobOpportunity, RawCandidate


def detect_hiring_signal(text: str) -> str | None:
    return analyze_hiring_text(text).hiring_signal


def raw_to_opportunity(raw: RawCandidate) -> JobOpportunity:
    text = raw.raw_text
    analysis = analyze_hiring_text(
        text,
        company_hint=raw.company_hint,
        title_hint=raw.title_hint,
        recruiter_hint=raw.recruiter_hint,
        location_hints=[raw.location_hint] if raw.location_hint else None,
    )

    email = raw.contact_email or analysis.contact_email
    if not email:
        emails = EMAIL_RE.findall(text)
        email = emails[0] if emails else None

    phones = PHONE_RE.findall(text)
    phone = phones[0].strip() if phones else None

    exp_min, exp_max, is_fresher, is_entry = parse_experience(text)
    if analysis.experience_min is not None:
        exp_min = analysis.experience_min
    if analysis.experience_max is not None:
        exp_max = analysis.experience_max
    if analysis.is_fresher:
        is_fresher = True
    if analysis.is_entry_level:
        is_entry = True

    strength = raw.hiring_signal_strength or analysis.hiring_signal_strength
    signal = analysis.hiring_signal or detect_hiring_signal(text)

    kind = raw.discovery_kind
    if not kind:
        if raw.source_url and "/jobs/view/" in raw.source_url:
            kind = "job_listing"
        else:
            kind = "hiring_post" if signal else None

    posted = raw.posted_at
    skills = raw.skills_hint or analysis.skills or None

    post_url = raw.source_post_url or (
        raw.source_url.split("#")[0] if raw.source_url and "/posts/" in raw.source_url else None
    )

    job = JobOpportunity(
        id=str(uuid.uuid4()),
        source=raw.source,
        source_url=raw.source_url,
        company_name=raw.company_hint or analysis.company_name,
        job_title=raw.title_hint or analysis.job_title,
        description=text,
        location=raw.location_hint or analysis.location,
        experience_min=exp_min,
        experience_max=exp_max,
        employment_type=raw.employment_type_hint or analysis.employment_type,
        domain=raw.domain_hint,
        skills=skills,
        posted_at=posted,
        discovered_at=utc_now(),
        application_url=raw.application_url or analysis.application_url,
        application_method=raw.application_method or analysis.application_method,
        contact_email=email,
        contact_phone=phone,
        is_fresher=is_fresher,
        is_entry_level=is_entry,
        hiring_signal=signal,
        hiring_signal_strength=strength,
        discovery_kind=kind,
        source_post_url=post_url,
        recruiter_name=raw.recruiter_hint or analysis.recruiter_name,
        salary_text=raw.salary_hint or analysis.salary_text,
        freshness_bucket=freshness_bucket(posted) if posted else None,
    )
    return job
