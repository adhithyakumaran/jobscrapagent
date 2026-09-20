from __future__ import annotations

from urllib.parse import quote_plus

from jobfinder.models import JobOpportunity

APPLICATION_METHOD_LABELS = {
    "dm_resume": "LinkedIn DM",
    "email": "Email",
    "email_resume": "Email",
    "walk_in": "Walk-in",
    "comment": "Comment on post",
    "comment_interested": "Comment on post",
    "google_form": "Google Form",
    "application_form": "Application form",
    "linkedin_apply": "LinkedIn Easy Apply",
    "careers_portal": "Careers portal",
    "careers_page": "Careers page",
    "ats": "ATS",
    "phone": "Phone",
}


def _is_linkedin_job_url(url: str | None) -> bool:
    return bool(url and "/jobs/view/" in url)


def _is_linkedin_post_url(url: str | None) -> bool:
    return bool(url and "/posts/" in url)


def canonical_linkedin_url(job: JobOpportunity) -> str | None:
    """Best original LinkedIn URL for opening the listing or post."""
    if job.source_post_url:
        return job.source_post_url.split("#")[0]
    if job.source_url:
        base = job.source_url.split("#")[0]
        if _is_linkedin_job_url(base) or _is_linkedin_post_url(base):
            return base
    for alt in job.alternate_source_urls:
        if _is_linkedin_job_url(alt) or _is_linkedin_post_url(alt):
            return alt.split("#")[0]
    return job.source_url


def is_apply_link(job: JobOpportunity) -> bool:
    """True when application_url is a distinct apply target (not the same as open LinkedIn page)."""
    if not job.application_url:
        return False
    open_base = (canonical_linkedin_url(job) or job.source_url or "").split("#")[0].rstrip("/")
    app_base = job.application_url.split("#")[0].rstrip("/")
    return bool(app_base and app_base != open_base)


def search_fallback_url(job: JobOpportunity) -> str | None:
    parts = [job.company_name, job.job_title, job.location]
    q = " ".join(p for p in parts if p)
    if not q.strip():
        return None
    return f"https://www.google.com/search?q={quote_plus(q)}"


def has_actionable_path(job: JobOpportunity) -> bool:
    if canonical_linkedin_url(job):
        return True
    if job.source_url and job.source_url.startswith("http"):
        return True
    if is_apply_link(job):
        return True
    if job.contact_email:
        return True
    if job.contact_phone:
        return True
    if job.application_method in (
        "dm_resume",
        "walk_in",
        "comment",
        "comment_interested",
        "email",
        "email_resume",
    ):
        if canonical_linkedin_url(job) or job.source_url:
            return True
    if search_fallback_url(job):
        return True
    return False


def application_summary(job: JobOpportunity) -> str:
    method = job.application_method
    if method:
        label = APPLICATION_METHOD_LABELS.get(method, method.replace("_", " ").title())
        if method == "dm_resume":
            return f"Application: {label}"
        return f"Application: {label}"
    if job.contact_email:
        return f"Email: {job.contact_email}"
    if job.contact_phone:
        return f"Phone: {job.contact_phone}"
    if is_apply_link(job):
        return "Application: External link"
    if canonical_linkedin_url(job):
        return "Application: Via LinkedIn"
    return "Application: —"


def build_job_actions(job: JobOpportunity) -> dict:
    linkedin_url = canonical_linkedin_url(job)
    is_post = job.discovery_kind == "hiring_post" or _is_linkedin_post_url(linkedin_url or job.source_url or "")
    is_job = job.discovery_kind == "job_listing" or _is_linkedin_job_url(linkedin_url or job.source_url or "")

    if is_post:
        open_label = "Open LinkedIn Post"
    elif is_job:
        open_label = "Open LinkedIn Job"
    else:
        open_label = "Open Original"

    open_url = linkedin_url or job.source_url
    apply_url = job.application_url if is_apply_link(job) else None
    email = job.contact_email
    mailto = f"mailto:{email}" if email else None

    return {
        "open_label": open_label,
        "open_url": open_url,
        "apply_url": apply_url,
        "show_apply": bool(apply_url),
        "email": email,
        "mailto": mailto,
        "email_label": "Email Recruiter" if email else None,
        "application_summary": application_summary(job),
        "search_url": search_fallback_url(job) if not open_url and not apply_url and not email else None,
        "has_actionable": has_actionable_path(job),
        "alternate_urls": job.alternate_source_urls,
    }
