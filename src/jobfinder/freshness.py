from __future__ import annotations

from datetime import datetime, timezone

from jobfinder.models import FreshnessBucket


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def freshness_bucket(
    posted_at: datetime | None,
    reference: datetime | None = None,
) -> FreshnessBucket:
    ref = reference or utc_now()
    if posted_at is None:
        return FreshnessBucket.OLDER

    posted = ensure_aware(posted_at)
    ref = ensure_aware(ref)
    age_hours = (ref - posted).total_seconds() / 3600.0

    if age_hours < 6:
        return FreshnessBucket.VERY_NEW
    if age_hours < 24:
        return FreshnessBucket.NEW
    if age_hours < 72:
        return FreshnessBucket.RECENT
    return FreshnessBucket.OLDER


FRESHNESS_LABELS = {
    FreshnessBucket.VERY_NEW: "Very New",
    FreshnessBucket.NEW: "New",
    FreshnessBucket.RECENT: "Recent",
    FreshnessBucket.OLDER: "Older",
}

FRESHNESS_EMOJI = {
    FreshnessBucket.VERY_NEW: "🔥",
    FreshnessBucket.NEW: "🟢",
    FreshnessBucket.RECENT: "🟡",
    FreshnessBucket.OLDER: "⚪",
}
