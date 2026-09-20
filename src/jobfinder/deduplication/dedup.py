from __future__ import annotations

import re
import uuid
from urllib.parse import urlparse

from rapidfuzz import fuzz

from jobfinder.models import JobOpportunity

DESCRIPTION_SIMILARITY_THRESHOLD = 85


def normalize_company(name: str | None) -> str:
    if not name:
        return ""
    s = name.lower().strip()
    s = re.sub(r"\b(pvt|ltd|limited|inc|llc|technologies|technology|solutions)\b\.?", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_title(title: str | None) -> str:
    if not title:
        return ""
    s = title.lower().strip()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_location(loc: str | None) -> str:
    if not loc:
        return ""
    return re.sub(r"\s+", " ", loc.lower().strip())


def normalize_url(url: str | None) -> str:
    if not url:
        return ""
    parsed = urlparse(url.strip())
    path = parsed.path.rstrip("/")
    return f"{parsed.netloc.lower()}{path}".lower()


class DedupResult:
    def __init__(
        self,
        is_duplicate: bool,
        canonical: JobOpportunity | None = None,
        reason: str = "",
    ) -> None:
        self.is_duplicate = is_duplicate
        self.canonical = canonical
        self.reason = reason


class DeduplicationService:
    def find_duplicate(
        self,
        job: JobOpportunity,
        existing: list[JobOpportunity],
    ) -> DedupResult:
        job_url = normalize_url(job.source_url)
        app_url = normalize_url(job.application_url)
        comp = normalize_company(job.company_name)
        title = normalize_title(job.job_title)
        loc = normalize_location(job.location)

        for ex in existing:
            if normalize_url(ex.source_url) == job_url and job_url:
                return DedupResult(True, ex, "source_url")

            if app_url and normalize_url(ex.application_url) == app_url:
                return DedupResult(True, ex, "application_url")

            ex_comp = normalize_company(ex.company_name)
            ex_title = normalize_title(ex.job_title)
            ex_loc = normalize_location(ex.location)

            if comp and title and comp == ex_comp and title == ex_title:
                if not loc or not ex_loc or loc == ex_loc:
                    return DedupResult(True, ex, "company_title_location")

            if comp and comp == ex_comp and loc and loc == ex_loc:
                if job.description and ex.description:
                    ratio = fuzz.token_sort_ratio(
                        job.description[:500],
                        ex.description[:500],
                    )
                    if ratio >= DESCRIPTION_SIMILARITY_THRESHOLD:
                        return DedupResult(True, ex, "description_similarity")

        return DedupResult(False)

    def merge_duplicate(self, canonical: JobOpportunity, duplicate: JobOpportunity) -> JobOpportunity:
        if duplicate.source_url and duplicate.source_url not in (
            canonical.source_url,
            *canonical.alternate_source_urls,
        ):
            canonical.alternate_source_urls.append(duplicate.source_url)
        if not canonical.duplicate_group_id:
            canonical.duplicate_group_id = canonical.id or str(uuid.uuid4())
        duplicate.duplicate_group_id = canonical.duplicate_group_id
        return canonical
