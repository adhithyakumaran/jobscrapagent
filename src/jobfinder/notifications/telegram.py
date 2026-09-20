from __future__ import annotations

import html
import logging
import os
from dataclasses import dataclass
from typing import Any, Callable

import httpx
from dotenv import load_dotenv

from jobfinder.actionable import APPLICATION_METHOD_LABELS, build_job_actions
from jobfinder.config import ProfileConfig, TelegramConfig
from jobfinder.freshness import FRESHNESS_LABELS
from jobfinder.models import JobOpportunity
from jobfinder.storage.db import Database

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
CHANNEL = "telegram"


@dataclass
class TelegramCredentials:
    bot_token: str
    chat_id: str


def fetch_chat_ids_from_updates(bot_token: str) -> list[dict[str, Any]]:
    """Return recent chat ids from getUpdates (message your bot first)."""
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(url)
            if resp.status_code >= 400:
                logger.warning("getUpdates failed: %s", resp.text[:200])
                return []
            data = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("getUpdates error: %s", exc)
        return []
    if not data.get("ok"):
        return []
    seen: set[int] = set()
    out: list[dict[str, Any]] = []
    for item in data.get("result", []):
        msg = item.get("message") or item.get("edited_message")
        if not msg:
            continue
        chat = msg.get("chat") or {}
        cid = chat.get("id")
        if cid is None or cid in seen:
            continue
        seen.add(cid)
        out.append(
            {
                "chat_id": cid,
                "type": chat.get("type"),
                "title": chat.get("title"),
                "username": chat.get("username"),
                "first_name": chat.get("first_name"),
            }
        )
    return out


def _is_placeholder(value: str) -> bool:
    v = value.strip().upper()
    return not v or v.startswith("YOUR_") or v in {"CHANGEME", "REPLACE_ME"}


def load_telegram_credentials() -> TelegramCredentials | None:
    load_dotenv()
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
    if _is_placeholder(token) or _is_placeholder(chat_id):
        return None
    return TelegramCredentials(bot_token=token, chat_id=chat_id)


def telegram_is_active(profile: ProfileConfig) -> bool:
    if not profile.notifications.telegram.enabled:
        return False
    return load_telegram_credentials() is not None


def _esc(text: str | None) -> str:
    return html.escape(text or "—")


def _experience_line(job: JobOpportunity) -> str:
    if job.is_fresher and job.is_entry_level:
        return "Fresher / Entry Level"
    if job.is_fresher:
        return "Fresher"
    if job.is_entry_level:
        return "Entry Level"
    if job.experience_min is not None or job.experience_max is not None:
        mn = job.experience_min if job.experience_min is not None else "?"
        mx = job.experience_max if job.experience_max is not None else "?"
        return f"{mn}-{mx} years"
    return "—"


def _posted_line(job: JobOpportunity) -> str:
    if not job.posted_at:
        return "Unknown"
    from datetime import datetime, timezone

    dt = job.posted_at
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    hours = int((datetime.now(timezone.utc) - dt).total_seconds() // 3600)
    if hours < 1:
        return "Just now"
    if hours < 24:
        return f"{hours} hours ago"
    days = hours // 24
    return f"{days} days ago"


def _source_label(job: JobOpportunity) -> str:
    actions = build_job_actions(job)
    if "Post" in actions["open_label"]:
        return "LinkedIn Post"
    if "Job" in actions["open_label"]:
        return "LinkedIn Job"
    return job.source or "LinkedIn"


def _headline(job: JobOpportunity) -> str:
    is_post = job.discovery_kind == "hiring_post" or (
        job.source_url and "/posts/" in job.source_url
    )
    if is_post:
        return "🔥 NEW HIRING POST"
    if job.discovery_kind == "job_listing" or (job.source_url and "/jobs/view/" in job.source_url):
        return "🔥 NEW JOB"
    return "🔥 NEW HIRING"


def _snippet(job: JobOpportunity, max_len: int = 120) -> str:
    if not job.description:
        return ""
    text = " ".join(job.description.split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def format_job_message(job: JobOpportunity) -> str:
    actions = build_job_actions(job)
    lines = [
        _headline(job),
        "",
        _esc(job.company_name or "Unknown company"),
        _esc(job.job_title or "(Hiring opportunity)"),
        "",
        f"📍 {_esc(job.location)}",
        f"🎓 {_esc(_experience_line(job))}",
    ]
    if job.posted_at:
        lines.append(f"🕐 Posted: {_esc(_posted_line(job))}")
    if job.freshness_bucket:
        lines.append(f"⏱ {_esc(FRESHNESS_LABELS.get(job.freshness_bucket, str(job.freshness_bucket)))}")
    lines.append(f"Match: {job.relevance_score:.0f}%")
    if job.hiring_signal_strength:
        sig = job.hiring_signal_strength.replace("_hiring_signal", "").upper()
        lines.append(f"🔥 Hiring signal: {sig}")
    snippet = _snippet(job)
    if snippet and "Post" in _headline(job):
        lines.extend(["", f'"{_esc(snippet)}"'])
    lines.extend(
        [
            "",
            f"Source: {_esc(_source_label(job))}",
            "",
            actions["application_summary"],
        ]
    )
    if job.contact_email and actions["mailto"]:
        lines.append(f"📧 Email: {_esc(job.contact_email)}")
    return "\n".join(lines)


def build_inline_keyboard(job: JobOpportunity) -> dict[str, Any] | None:
    actions = build_job_actions(job)
    row1: list[dict[str, str]] = []
    row2: list[dict[str, str]] = []

    if actions["show_apply"] and actions["apply_url"]:
        row1.append({"text": "Apply", "url": actions["apply_url"]})
    if actions["open_url"]:
        row1.append({"text": actions["open_label"], "url": actions["open_url"]})
    if actions["mailto"] and actions["email_label"]:
        row2.append({"text": actions["email_label"], "url": actions["mailto"]})
    if job.source_url and actions["open_url"] and job.source_url != actions["open_url"]:
        row2.append({"text": "Original", "url": job.source_url})

    buttons = [r for r in (row1, row2) if r]
    if not buttons:
        return None
    return {"inline_keyboard": buttons}


def format_digest_message(jobs: list[JobOpportunity], ui_url: str = "http://127.0.0.1:8765") -> str:
    lines = [f"🔥 {len(jobs)} NEW JOBS FOUND", ""]
    for i, job in enumerate(jobs[:15], start=1):
        title = job.job_title or "Hiring post"
        loc = job.location or "—"
        comp = job.company_name or "—"
        lines.append(f"{i}. {_esc(comp)} — {_esc(title)} — {_esc(loc)}")
    if len(jobs) > 15:
        lines.append(f"... and {len(jobs) - 15} more")
    lines.append("")
    lines.append(f'<a href="{_esc(ui_url)}">Open Job Finder</a>')
    return "\n".join(lines)


def qualifies_for_notification(
    job: JobOpportunity,
    profile: ProfileConfig,
    db: Database,
) -> bool:
    from jobfinder.actionable import has_actionable_path

    cfg = profile.notifications.telegram
    if not has_actionable_path(job):
        return False
    if job.relevance_score < cfg.min_relevance:
        return False
    if not job.id:
        return False
    if db.was_notified(job.id, CHANNEL):
        return False
    return True


class TelegramNotifier:
    def __init__(
        self,
        profile: ProfileConfig,
        db: Database,
        *,
        send_fn: Callable[..., bool] | None = None,
    ) -> None:
        self.profile = profile
        self.db = db
        self._send_fn = send_fn or self._default_send

    def _default_send(
        self,
        token: str,
        chat_id: str,
        text: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> bool:
        url = TELEGRAM_API.format(token=token)
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(url, json=payload)
                if resp.status_code >= 400:
                    logger.warning("Telegram API error %s: %s", resp.status_code, resp.text[:200])
                    return False
                return True
        except httpx.HTTPError as exc:
            logger.warning("Telegram send failed: %s", exc)
            return False

    def notify_new_jobs(self, jobs: list[JobOpportunity]) -> int:
        if not telegram_is_active(self.profile):
            return 0
        creds = load_telegram_credentials()
        if not creds:
            return 0

        cfg = self.profile.notifications.telegram
        eligible = [j for j in jobs if qualifies_for_notification(j, self.profile, self.db)]
        if not eligible:
            return 0

        sent = 0
        if cfg.mode == "digest":
            text = format_digest_message(eligible, ui_url=cfg.ui_url)
            ok = self._send_fn(creds.bot_token, creds.chat_id, text, None)
            if ok:
                for job in eligible:
                    self.db.record_notification(job.id, CHANNEL)
                sent = len(eligible)
            return sent

        for job in eligible:
            text = format_job_message(job)
            keyboard = build_inline_keyboard(job)
            ok = self._send_fn(creds.bot_token, creds.chat_id, text, keyboard)
            if ok:
                self.db.record_notification(job.id, CHANNEL)
                sent += 1
            else:
                logger.warning("Skipped recording notification for %s after send failure", job.id)
        return sent

    def send_test_message(self) -> bool:
        if not telegram_is_active(self.profile):
            logger.info("Telegram disabled or credentials missing")
            return False
        creds = load_telegram_credentials()
        if not creds:
            return False
        from jobfinder.models import JobOpportunity

        sample = JobOpportunity(
            id="test",
            source="linkedin",
            source_url="https://www.linkedin.com/jobs/view/example",
            company_name="Test Company",
            job_title="Graduate Engineer",
            location="Chennai",
            is_fresher=True,
            is_entry_level=True,
            relevance_score=86.0,
            application_url="https://example.com/apply",
            application_method="careers_portal",
            discovery_kind="job_listing",
        )
        text = format_job_message(sample)
        text = "🧪 TEST\n\n" + text
        return self._send_fn(
            creds.bot_token,
            creds.chat_id,
            text,
            build_inline_keyboard(sample),
        )
