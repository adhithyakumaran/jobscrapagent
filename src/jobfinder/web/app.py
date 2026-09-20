from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from jobfinder.freshness import FRESHNESS_EMOJI, FRESHNESS_LABELS
from jobfinder.models import JobStatus
from jobfinder.storage.db import Database

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app = FastAPI(title="Job Finder", docs_url=None, redoc_url=None)
_db: Database | None = None


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
        _db.init_schema()
    return _db


def _format_posted(dt: datetime | None) -> str:
    if not dt:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = now - dt
    hours = int(delta.total_seconds() // 3600)
    if hours < 1:
        return "Just now"
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"


def _experience_label(job) -> str:
    if job.is_fresher:
        return "Fresher"
    if job.experience_min is not None or job.experience_max is not None:
        mn = job.experience_min if job.experience_min is not None else "?"
        mx = job.experience_max if job.experience_max is not None else "?"
        return f"{mn}-{mx} yrs"
    if job.is_entry_level:
        return "Entry level"
    return "—"


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    filter: str = Query("new", alias="filter"),
    location: str | None = None,
    domain: str | None = None,
    source: str | None = None,
    fresher: bool = False,
    min_relevance: float | None = None,
):
    db = get_db()
    since = None
    status = None
    if filter == "new":
        status = "new"
    elif filter == "all":
        status = None
    elif filter == "today":
        since = datetime.now(timezone.utc) - timedelta(days=1)
    elif filter == "3days":
        since = datetime.now(timezone.utc) - timedelta(days=3)

    jobs = db.list_jobs(
        status=status,
        since_posted=since,
        location=location or None,
        domain=domain or None,
        source=source or None,
        fresher_only=fresher,
        min_relevance=min_relevance,
    )

    rows = []
    for j in jobs:
        bucket = j.freshness_bucket
        rows.append(
            {
                "id": j.id,
                "company": j.company_name or "—",
                "title": j.job_title or "(Hiring post)",
                "location": j.location or "—",
                "experience": _experience_label(j),
                "source": j.source,
                "posted": _format_posted(j.posted_at),
                "relevance": round(j.relevance_score, 1),
                "confidence": round(j.confidence_score, 1),
                "application_method": j.application_method or j.contact_email or "—",
                "hiring_signal": j.hiring_signal or "—",
                "discovery_kind": j.discovery_kind or (
                    "job_listing" if j.source_url and "/jobs/view/" in j.source_url else "hiring_post"
                ),
                "posted_exact": j.posted_at.isoformat() if j.posted_at else "Unknown",
                "source_url": j.source_url,
                "application_url": j.application_url or j.source_url,
                "freshness": (
                    f"{FRESHNESS_EMOJI.get(bucket, '')} {FRESHNESS_LABELS.get(bucket, '')}"
                    if bucket
                    else "—"
                ),
                "status": j.status.value if hasattr(j.status, "value") else j.status,
            }
        )

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "jobs": rows,
            "filter": filter,
            "location": location or "",
            "domain": domain or "",
            "source": source or "",
            "fresher": fresher,
            "min_relevance": min_relevance if min_relevance is not None else "",
        },
    )


@app.post("/jobs/{job_id}/seen")
def mark_seen(job_id: str):
    get_db().set_job_status(job_id, JobStatus.SEEN)
    return RedirectResponse(url="/", status_code=303)


@app.post("/jobs/{job_id}/ignore")
def mark_ignore(job_id: str):
    get_db().set_job_status(job_id, JobStatus.IGNORED)
    return RedirectResponse(url="/", status_code=303)
