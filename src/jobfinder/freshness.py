from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum

from jobfinder.models import FreshnessBucket


class FreshnessGate(str, Enum):
    FRESH = "fresh"
    STALE = "stale"
    UNKNOWN = "unknown"


DEFAULT_FRESHNESS_DAYS = 30


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


def classify_freshness(
    posted_at: datetime | None,
    freshness_days: int = DEFAULT_FRESHNESS_DAYS,
    reference: datetime | None = None,
) -> FreshnessGate:
    """30-day window: inclusive through freshness_days; unknown if no posted_at."""
    if posted_at is None:
        return FreshnessGate.UNKNOWN
    posted = ensure_aware(posted_at)
    ref = ensure_aware(reference or utc_now())
    cutoff = ref - timedelta(days=freshness_days)
    if posted < cutoff:
        return FreshnessGate.STALE
    return FreshnessGate.FRESH


def is_fresh_opportunity(
    posted_at: datetime | None,
    freshness_days: int = DEFAULT_FRESHNESS_DAYS,
    reference: datetime | None = None,
) -> bool:
    return classify_freshness(posted_at, freshness_days, reference) == FreshnessGate.FRESH
