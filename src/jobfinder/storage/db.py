from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from jobfinder.config import default_db_path
from jobfinder.freshness import utc_now
from jobfinder.models import JobOpportunity, JobStatus
from jobfinder.storage.schema import JOBS_TABLE, NOTIFICATIONS_TABLE, SEARCH_RUNS_TABLE


class Database:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(JOBS_TABLE)
            conn.executescript(SEARCH_RUNS_TABLE)
            conn.executescript(NOTIFICATIONS_TABLE)
            cols = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
            for col, ddl in (
                ("discovery_kind", "ALTER TABLE jobs ADD COLUMN discovery_kind TEXT"),
                ("hiring_signal_strength", "ALTER TABLE jobs ADD COLUMN hiring_signal_strength TEXT"),
                ("source_post_url", "ALTER TABLE jobs ADD COLUMN source_post_url TEXT"),
                ("recruiter_name", "ALTER TABLE jobs ADD COLUMN recruiter_name TEXT"),
                ("salary_text", "ALTER TABLE jobs ADD COLUMN salary_text TEXT"),
            ):
                if col not in cols:
                    conn.execute(ddl)
                    cols.add(col)
            conn.commit()

    def insert_job(self, job: JobOpportunity) -> JobOpportunity:
        if not job.id:
            job.id = str(uuid.uuid4())
        if not job.discovered_at:
            job.discovered_at = utc_now()
        row = job.to_db_row()
        cols = list(row.keys())
        placeholders = ", ".join("?" for _ in cols)
        sql = f"INSERT INTO jobs ({', '.join(cols)}) VALUES ({placeholders})"
        with self.connect() as conn:
            conn.execute(sql, [row[c] for c in cols])
            conn.commit()
        return job

    def update_job(self, job: JobOpportunity) -> None:
        row = job.to_db_row()
        job_id = row.pop("id")
        sets = ", ".join(f"{k} = ?" for k in row.keys())
        sql = f"UPDATE jobs SET {sets} WHERE id = ?"
        with self.connect() as conn:
            conn.execute(sql, list(row.values()) + [job_id])
            conn.commit()

    def get_job(self, job_id: str) -> JobOpportunity | None:
        with self.connect() as conn:
            cur = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cur.fetchone()
        if not row:
            return None
        return JobOpportunity.from_db_row(dict(row))

    def get_job_by_source_url(self, source_url: str) -> JobOpportunity | None:
        with self.connect() as conn:
            cur = conn.execute("SELECT * FROM jobs WHERE source_url = ?", (source_url,))
            row = cur.fetchone()
        if not row:
            return None
        return JobOpportunity.from_db_row(dict(row))

    def list_jobs(
        self,
        status: str | None = None,
        min_relevance: float | None = None,
        location: str | None = None,
        domain: str | None = None,
        source: str | None = None,
        fresher_only: bool = False,
        since_posted: datetime | None = None,
        limit: int = 500,
    ) -> list[JobOpportunity]:
        clauses: list[str] = []
        params: list[Any] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if min_relevance is not None:
            clauses.append("relevance_score >= ?")
            params.append(min_relevance)
        if location:
            clauses.append("LOWER(location) LIKE ?")
            params.append(f"%{location.lower()}%")
        if domain:
            clauses.append("LOWER(domain) LIKE ?")
            params.append(f"%{domain.lower()}%")
        if source:
            clauses.append("LOWER(source) = ?")
            params.append(source.lower())
        if fresher_only:
            clauses.append("(is_fresher = 1 OR is_entry_level = 1)")
        if since_posted:
            clauses.append("posted_at >= ?")
            params.append(since_posted.isoformat())
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM jobs{where} ORDER BY posted_at DESC, relevance_score DESC LIMIT ?"
        params.append(limit)
        with self.connect() as conn:
            cur = conn.execute(sql, params)
            rows = cur.fetchall()
        return [JobOpportunity.from_db_row(dict(r)) for r in rows]

    def all_jobs_for_dedup(self) -> list[JobOpportunity]:
        with self.connect() as conn:
            cur = conn.execute("SELECT * FROM jobs")
            rows = cur.fetchall()
        return [JobOpportunity.from_db_row(dict(r)) for r in rows]

    def create_search_run(self, source: str) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO search_runs (started_at, source) VALUES (?, ?)",
                (utc_now().isoformat(), source),
            )
            conn.commit()
            return int(cur.lastrowid)

    def finish_search_run(self, run_id: int, stats: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE search_runs SET
                    finished_at = ?,
                    queries_attempted = ?,
                    candidates_discovered = ?,
                    parsed = ?,
                    rejected = ?,
                    duplicates = ?,
                    new_opportunities = ?,
                    high_confidence = ?,
                    telegram_notifications = ?,
                    notes = ?
                WHERE id = ?
                """,
                (
                    utc_now().isoformat(),
                    stats.get("queries_attempted", 0),
                    stats.get("candidates_discovered", 0),
                    stats.get("parsed", 0),
                    stats.get("rejected", 0),
                    stats.get("duplicates", 0),
                    stats.get("new_opportunities", 0),
                    stats.get("high_confidence", 0),
                    stats.get("telegram_notifications", 0),
                    json.dumps(stats.get("notes")) if stats.get("notes") else None,
                    run_id,
                ),
            )
            conn.commit()

    def latest_search_run(self) -> dict[str, Any] | None:
        with self.connect() as conn:
            cur = conn.execute("SELECT * FROM search_runs ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
        return dict(row) if row else None

    def job_counts(self) -> dict[str, int]:
        with self.connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            new = conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'new'").fetchone()[0]
            seen = conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'seen'").fetchone()[0]
            ignored = conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'ignored'").fetchone()[0]
        return {"total": total, "new": new, "seen": seen, "ignored": ignored}

    def was_notified(self, job_id: str, channel: str) -> bool:
        with self.connect() as conn:
            cur = conn.execute(
                "SELECT 1 FROM notifications WHERE job_id = ? AND channel = ?",
                (job_id, channel),
            )
            return cur.fetchone() is not None

    def record_notification(self, job_id: str, channel: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO notifications (job_id, channel, sent_at) VALUES (?, ?, ?)",
                (job_id, channel, utc_now().isoformat()),
            )
            conn.commit()

    def set_job_status(self, job_id: str, status: JobStatus) -> bool:
        with self.connect() as conn:
            cur = conn.execute(
                "UPDATE jobs SET status = ? WHERE id = ?",
                (status.value, job_id),
            )
            conn.commit()
            return cur.rowcount > 0
