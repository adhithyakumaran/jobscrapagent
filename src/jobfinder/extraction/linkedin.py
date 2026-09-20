from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup

from jobfinder.extraction.hiring import analyze_hiring_text, split_multi_role_post
from jobfinder.extraction.posted_time import parse_relative_posted
from jobfinder.models import RawCandidate

JOB_CARD_RE = re.compile(r"base-card|job-search-card|jobs-search__results-list")
JOB_URL_RE = re.compile(r"https?://(?:www\.)?linkedin\.com/jobs/view/[^\s\"'<>]+")
POST_URL_RE = re.compile(r"https?://(?:www\.)?linkedin\.com/posts/[^\s\"'<>]+")


def build_jobs_search_url(keywords: str, location: str, start: int = 0) -> str:
    kw = quote_plus(keywords)
    loc = quote_plus(location)
    return (
        f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        f"?keywords={kw}&location={loc}&start={start}"
    )


def build_content_search_url(keywords: str) -> str:
    q = quote_plus(f"{keywords} site:linkedin.com/posts")
    return f"https://html.duckduckgo.com/html/?q={q}"


def parse_job_listing_html(html: str, source: str = "linkedin") -> list[RawCandidate]:
    soup = BeautifulSoup(html, "lxml")
    results: list[RawCandidate] = []
    for card in soup.select("li"):
        link = card.select_one("a[href*='/jobs/view/']")
        if not link:
            continue
        href = link.get("href", "")
        if href.startswith("/"):
            href = urljoin("https://www.linkedin.com", href)
        title_el = card.select_one("h3, .base-search-card__title")
        company_el = card.select_one("h4, .base-search-card__subtitle, .hidden-nested-link")
        loc_el = card.select_one(".job-search-card__location, .job-search-card__location")
        title = title_el.get_text(strip=True) if title_el else None
        company = company_el.get_text(strip=True) if company_el else None
        location = loc_el.get_text(strip=True) if loc_el else None
        time_el = card.select_one("time")
        posted = None
        if time_el:
            dt_attr = time_el.get("datetime")
            if dt_attr:
                try:
                    posted = datetime.fromisoformat(dt_attr.replace("Z", "+00:00"))
                except ValueError:
                    posted = parse_relative_posted(time_el.get_text(strip=True))
            else:
                posted = parse_relative_posted(time_el.get_text(strip=True))
        desc = card.get_text(" ", strip=True)
        results.append(
            RawCandidate(
                source=source,
                source_url=href.split("?")[0],
                raw_text=desc,
                title_hint=title,
                company_hint=company,
                location_hint=location,
                posted_at=posted,
                discovery_kind="job_listing",
                html_kind="job_listing",
            )
        )
    if not results:
        for m in JOB_URL_RE.finditer(html):
            url = m.group(0).split("?")[0]
            results.append(
                RawCandidate(
                    source=source,
                    source_url=url,
                    raw_text=html[:500],
                    discovery_kind="job_listing",
                    html_kind="search_results",
                )
            )
    return results


def parse_job_detail_html(html: str, url: str, source: str = "linkedin") -> RawCandidate | None:
    soup = BeautifulSoup(html, "lxml")
    title_el = soup.select_one("h1, .top-card-layout__title, .job-details-jobs-unified-top-card__job-title")
    company_el = soup.select_one(
        ".topcard__org-name-link, .job-details-jobs-unified-top-card__company-name a, a[data-tracking-control-name='public_jobs_topcard-org-name']"
    )
    loc_el = soup.select_one(
        ".topcard__flavor--bullet, .job-details-jobs-unified-top-card__bullet, .job-details-jobs-unified-top-card__primary-description-container"
    )
    desc_el = soup.select_one(
        ".description__text, .jobs-description__content, .show-more-less-html__markup"
    )
    criteria = soup.select(".description__job-criteria-item, .jobs-unified-top-card__job-insight")
    employment_type = None
    for c in criteria:
        t = c.get_text(" ", strip=True).lower()
        if "employment" in t or "full-time" in t or "part-time" in t or "contract" in t:
            employment_type = c.get_text(" ", strip=True)

    posted = None
    time_el = soup.select_one("time")
    if time_el:
        if time_el.get("datetime"):
            try:
                posted = datetime.fromisoformat(time_el["datetime"].replace("Z", "+00:00"))
            except ValueError:
                posted = parse_relative_posted(time_el.get_text(strip=True))
        else:
            posted = parse_relative_posted(time_el.get_text(strip=True))

    apply_el = soup.select_one("a[data-tracking-control-name='public_jobs_apply-link'], a.jobs-apply-button")
    app_url = None
    app_method = None
    if apply_el and apply_el.get("href"):
        href = apply_el.get("href", "")
        if href.startswith("/"):
            href = urljoin("https://www.linkedin.com", href)
        app_url = href
        if "linkedin.com" in href.lower():
            app_method = "linkedin_apply"
        else:
            app_method = "external_apply"

    description = desc_el.get_text("\n", strip=True) if desc_el else soup.get_text("\n", strip=True)[:4000]
    ld = soup.find("script", type="application/ld+json")
    if ld and ld.string:
        try:
            data = json.loads(ld.string)
            if isinstance(data, dict) and data.get("@type") == "JobPosting":
                title_el = title_el or type("X", (), {"get_text": lambda *a, **k: data.get("title", "")})()
        except json.JSONDecodeError:
            pass

    title = title_el.get_text(strip=True) if title_el else None
    company = company_el.get_text(strip=True) if company_el else None
    location = loc_el.get_text(strip=True) if loc_el else None

    return RawCandidate(
        source=source,
        source_url=url.split("#")[0] if url else url,
        raw_text=description,
        title_hint=title,
        company_hint=company,
        location_hint=location,
        posted_at=posted,
        application_url=app_url,
        application_method=app_method,
        discovery_kind="job_listing",
        employment_type_hint=employment_type,
        html_kind="job_listing",
    )


def parse_hiring_post_html(
    html: str,
    url: str,
    location_hints: list[str] | None = None,
    source: str = "linkedin",
) -> list[RawCandidate]:
    soup = BeautifulSoup(html, "lxml")
    text_el = soup.select_one(
        ".feed-shared-update-v2__description, .update-components-text, article, .main-content"
    )
    text = text_el.get_text("\n", strip=True) if text_el else soup.get_text("\n", strip=True)[:5000]
    author_el = soup.select_one(".update-components-actor__name, .feed-shared-actor__name")
    company_hint = author_el.get_text(strip=True) if author_el else None
    time_el = soup.select_one("time")
    posted = None
    if time_el:
        if time_el.get("datetime"):
            try:
                posted = datetime.fromisoformat(time_el["datetime"].replace("Z", "+00:00"))
            except ValueError:
                posted = parse_relative_posted(time_el.get_text(strip=True))
        else:
            posted = parse_relative_posted(time_el.get_text(strip=True))

    analysis = analyze_hiring_text(text, location_hints=location_hints, company_hint=company_hint)
    if not analysis.is_hiring_related:
        return []

    roles = split_multi_role_post(text)
    out: list[RawCandidate] = []
    for role in roles:
        a = analyze_hiring_text(
            text,
            location_hints=location_hints,
            company_hint=company_hint,
            title_hint=role,
        )
        if not a.is_hiring_related:
            continue
        from urllib.parse import quote

        suffix = f"#role={quote(role)}" if role else ""
        out.append(
            RawCandidate(
                source=source,
                source_url=f"{url.split('#')[0]}{suffix}" if suffix else url,
                raw_text=text,
                title_hint=a.job_title or role,
                company_hint=a.company_name,
                location_hint=a.location,
                posted_at=posted,
                application_url=a.application_url,
                application_method=a.application_method,
                contact_email=a.contact_email,
                skills_hint=a.skills or None,
                discovery_kind="hiring_post",
                html_kind="hiring_post",
                recruiter_hint=a.recruiter_name,
                salary_hint=a.salary_text,
                hiring_signal_strength=a.hiring_signal_strength,
                employment_type_hint=a.employment_type,
                source_post_url=url.split("#")[0],
            )
        )
    return out


def parse_indexed_links(html: str, source: str = "linkedin") -> list[RawCandidate]:
    soup = BeautifulSoup(html, "lxml")
    found: list[RawCandidate] = []
    seen: set[str] = set()
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if "uddg=" in href:
            m = re.search(r"uddg=([^&]+)", href)
            if m:
                from urllib.parse import unquote

                href = unquote(m.group(1))
        for pattern, kind in ((JOB_URL_RE, "job_listing"), (POST_URL_RE, "hiring_post")):
            if pattern.search(href):
                clean = href.split("?")[0]
                if clean in seen:
                    continue
                seen.add(clean)
                found.append(
                    RawCandidate(
                        source=source,
                        source_url=clean,
                        raw_text=a.get_text(" ", strip=True) or clean,
                        title_hint=a.get_text(strip=True)[:120] or None,
                        discovery_kind=kind,
                        html_kind="search_results",
                    )
                )
                break
    return found
