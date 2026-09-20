from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    NEW = "new"
    SEEN = "seen"
    IGNORED = "ignored"
    APPLIED = "applied"


class FreshnessBucket(str, Enum):
    VERY_NEW = "very_new"
    NEW = "new"
    RECENT = "recent"
    OLDER = "older"


class JobOpportunity(BaseModel):
    id: Optional[str] = None
    source: str
    source_url: str

    company_name: Optional[str] = None
    job_title: Optional[str] = None

    description: Optional[str] = None
    location: Optional[str] = None

    experience_min: Optional[int] = None
    experience_max: Optional[int] = None

    employment_type: Optional[str] = None

    domain: Optional[str] = None
    skills: Optional[list[str]] = None

    posted_at: Optional[datetime] = None
    discovered_at: Optional[datetime] = None

    application_url: Optional[str] = None
    application_method: Optional[str] = None

    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None

    is_fresher: Optional[bool] = None
    is_entry_level: Optional[bool] = None

    hiring_signal: Optional[str] = None

    relevance_score: float = 0.0
    confidence_score: float = 0.0

    duplicate_group_id: Optional[str] = None

    status: JobStatus = JobStatus.NEW

    freshness_bucket: Optional[FreshnessBucket] = None

    alternate_source_urls: list[str] = Field(default_factory=list)

    def to_db_row(self) -> dict[str, Any]:
        data = self.model_dump()
        if data.get("skills"):
            data["skills"] = ",".join(data["skills"])
        else:
            data["skills"] = None
        if data.get("posted_at"):
            data["posted_at"] = data["posted_at"].isoformat()
        if data.get("discovered_at"):
            data["discovered_at"] = data["discovered_at"].isoformat()
        if data.get("status"):
            data["status"] = data["status"].value if isinstance(data["status"], JobStatus) else data["status"]
        if data.get("freshness_bucket"):
            data["freshness_bucket"] = (
                data["freshness_bucket"].value
                if isinstance(data["freshness_bucket"], FreshnessBucket)
                else data["freshness_bucket"]
            )
        if data.get("alternate_source_urls"):
            data["alternate_source_urls"] = "|".join(data["alternate_source_urls"])
        else:
            data["alternate_source_urls"] = None
        for bool_field in ("is_fresher", "is_entry_level"):
            if data.get(bool_field) is not None:
                data[bool_field] = 1 if data[bool_field] else 0
        return data

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> JobOpportunity:
        skills = row.get("skills")
        if skills and isinstance(skills, str):
            row["skills"] = [s.strip() for s in skills.split(",") if s.strip()]
        alt = row.get("alternate_source_urls")
        if alt and isinstance(alt, str):
            row["alternate_source_urls"] = [u for u in alt.split("|") if u]
        elif alt is None:
            row["alternate_source_urls"] = []
        for field in ("posted_at", "discovered_at"):
            if row.get(field) and isinstance(row[field], str):
                row[field] = datetime.fromisoformat(row[field])
        if row.get("status"):
            row["status"] = JobStatus(row["status"])
        if row.get("freshness_bucket"):
            row["freshness_bucket"] = FreshnessBucket(row["freshness_bucket"])
        for bool_field in ("is_fresher", "is_entry_level"):
            if row.get(bool_field) is not None:
                row[bool_field] = bool(row[bool_field])
        return cls(**{k: v for k, v in row.items() if k in cls.model_fields})


class RawCandidate(BaseModel):
    """Unnormalized item from a discovery provider."""

    source: str
    source_url: str
    raw_text: str
    title_hint: Optional[str] = None
    company_hint: Optional[str] = None
    location_hint: Optional[str] = None
    posted_at: Optional[datetime] = None
    application_url: Optional[str] = None
    application_method: Optional[str] = None
    contact_email: Optional[str] = None
    domain_hint: Optional[str] = None
