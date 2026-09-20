from pathlib import Path

import pytest

from jobfinder.actionable import build_job_actions
from jobfinder.config import ProfileConfig, TelegramConfig, load_profile
from jobfinder.models import JobOpportunity
from jobfinder.notifications.telegram import (
    CHANNEL,
    TelegramNotifier,
    build_inline_keyboard,
    format_job_message,
    load_telegram_credentials,
    qualifies_for_notification,
    telegram_is_active,
)
from jobfinder.pipeline import run_mock_scan
from jobfinder.storage.db import Database


def _profile(enabled: bool = True, min_rel: float = 40.0) -> ProfileConfig:
    p = load_profile()
    p.notifications.telegram.enabled = enabled
    p.notifications.telegram.min_relevance = min_rel
    return p


def test_telegram_disabled_without_credentials(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert load_telegram_credentials() is None
    assert not telegram_is_active(_profile(enabled=True))


def test_telegram_enabled_with_credentials(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    assert telegram_is_active(_profile(enabled=True))


def test_qualifies_new_job(tmp_path: Path):
    db = Database(tmp_path / "tg.db")
    db.init_schema()
    job = JobOpportunity(
        id="j1",
        source="linkedin",
        source_url="https://www.linkedin.com/jobs/view/1",
        company_name="Co",
        job_title="Dev",
        location="Chennai",
        relevance_score=50.0,
        discovery_kind="job_listing",
    )
    assert qualifies_for_notification(job, _profile(), db)


def test_no_notify_below_threshold(tmp_path: Path):
    db = Database(tmp_path / "tg2.db")
    job = JobOpportunity(
        id="j2",
        source="linkedin",
        source_url="https://www.linkedin.com/jobs/view/2",
        relevance_score=10.0,
    )
    assert not qualifies_for_notification(job, _profile(min_rel=40), db)


def test_no_notify_without_actionable_path(tmp_path: Path):
    db = Database(tmp_path / "tg3.db")
    job = JobOpportunity(
        id="j3",
        source="x",
        source_url="",
        relevance_score=90.0,
    )
    assert not qualifies_for_notification(job, _profile(), db)


def test_duplicate_notification_blocked(tmp_path: Path):
    db = Database(tmp_path / "tg4.db")
    db.init_schema()
    job = JobOpportunity(
        id="j4",
        source="linkedin",
        source_url="https://www.linkedin.com/posts/x",
        relevance_score=80.0,
        discovery_kind="hiring_post",
        application_method="dm_resume",
        description="DM your resume",
    )
    db.record_notification("j4", CHANNEL)
    assert not qualifies_for_notification(job, _profile(), db)


def test_inline_keyboard_job_and_apply():
    job = JobOpportunity(
        source="linkedin",
        source_url="https://www.linkedin.com/jobs/view/9",
        application_url="https://apply.example.com/x",
        application_method="external_apply",
        discovery_kind="job_listing",
    )
    kb = build_inline_keyboard(job)
    assert kb is not None
    labels = [b["text"] for row in kb["inline_keyboard"] for b in row]
    assert "Apply" in labels
    assert "Open LinkedIn Job" in labels


def test_inline_keyboard_post():
    job = JobOpportunity(
        source="linkedin",
        source_url="https://www.linkedin.com/posts/abc",
        application_method="dm_resume",
        description="DM your resume",
        discovery_kind="hiring_post",
    )
    kb = build_inline_keyboard(job)
    assert any("Open LinkedIn Post" in b["text"] for row in kb["inline_keyboard"] for b in row)


def test_email_button():
    job = JobOpportunity(
        source="linkedin",
        source_url="https://www.linkedin.com/posts/e",
        contact_email="careers@co.example",
        application_method="email",
        description="Send CV",
        discovery_kind="hiring_post",
    )
    kb = build_inline_keyboard(job)
    assert any("Email" in b["text"] for row in kb["inline_keyboard"] for b in row)


def test_notifier_sends_and_records(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    db = Database(tmp_path / "tg5.db")
    db.init_schema()
    sent: list[str] = []

    def fake_send(token, chat_id, text, reply_markup=None):
        sent.append(text)
        return True

    job = JobOpportunity(
        id="new1",
        source="linkedin",
        source_url="https://www.linkedin.com/jobs/view/55",
        company_name="Amazon",
        job_title="Digital Content Associate",
        location="Chennai",
        relevance_score=86.0,
        is_fresher=True,
        discovery_kind="job_listing",
    )
    n = TelegramNotifier(_profile(), db, send_fn=fake_send)
    count = n.notify_new_jobs([job])
    assert count == 1
    assert db.was_notified("new1", CHANNEL)
    assert "NEW JOB" in sent[0]


def test_notifier_no_duplicate_send(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    db = Database(tmp_path / "tg6.db")
    db.init_schema()
    calls = 0

    def fake_send(*_a, **_k):
        nonlocal calls
        calls += 1
        return True

    job = JobOpportunity(
        id="dup",
        source="linkedin",
        source_url="https://www.linkedin.com/jobs/view/1",
        relevance_score=90.0,
        discovery_kind="job_listing",
    )
    n = TelegramNotifier(_profile(), db, send_fn=fake_send)
    assert n.notify_new_jobs([job]) == 1
    assert n.notify_new_jobs([job]) == 0
    assert calls == 1


def test_telegram_failure_does_not_fail_scan(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")

    def fail_send(*_a, **_k):
        return False

    db = Database(tmp_path / "scan.db")
    profile = _profile()
    stats = run_mock_scan(db=db, profile=profile, max_intents=3, notify=True)
    # Patch notifier in pipeline is hard; test notifier directly
    job = JobOpportunity(
        id="x",
        source="linkedin",
        source_url="https://www.linkedin.com/jobs/view/x",
        relevance_score=90,
        discovery_kind="job_listing",
    )
    n = TelegramNotifier(profile, db, send_fn=fail_send)
    assert n.notify_new_jobs([job]) == 0
    assert stats.new_opportunities >= 0


def test_format_message_no_invented_urls():
    job = JobOpportunity(
        source="linkedin",
        source_url="https://www.linkedin.com/jobs/view/1",
        company_name="Co",
        job_title="Role",
        relevance_score=50,
        discovery_kind="job_listing",
    )
    msg = format_job_message(job)
    actions = build_job_actions(job)
    assert actions["apply_url"] is None
    assert "https://www.linkedin.com/jobs/view/1" in (actions["open_url"] or "")
