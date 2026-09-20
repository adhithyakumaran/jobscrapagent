from datetime import datetime, timedelta, timezone

from jobfinder.extraction.posted_time import parse_posted_time, parse_relative_posted
from jobfinder.freshness import FreshnessGate, classify_freshness, is_fresh_opportunity


def _ref() -> datetime:
    return datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


def test_classify_one_day_fresh():
    ref = _ref()
    posted = ref - timedelta(days=1)
    assert classify_freshness(posted, 30, ref) == FreshnessGate.FRESH


def test_classify_29_days_fresh():
    ref = _ref()
    posted = ref - timedelta(days=29)
    assert classify_freshness(posted, 30, ref) == FreshnessGate.FRESH


def test_classify_30_days_fresh_inclusive():
    ref = _ref()
    posted = ref - timedelta(days=30)
    assert classify_freshness(posted, 30, ref) == FreshnessGate.FRESH


def test_classify_31_days_stale():
    ref = _ref()
    posted = ref - timedelta(days=31)
    assert classify_freshness(posted, 30, ref) == FreshnessGate.STALE


def test_classify_two_months_stale():
    ref = _ref()
    posted = ref - timedelta(days=60)
    assert classify_freshness(posted, 30, ref) == FreshnessGate.STALE


def test_classify_eleven_months_stale():
    ref = _ref()
    posted = ref - timedelta(days=11 * 30)
    assert classify_freshness(posted, 30, ref) == FreshnessGate.STALE


def test_unknown_when_missing_posted_at():
    assert classify_freshness(None, 30, _ref()) == FreshnessGate.UNKNOWN
    assert not is_fresh_opportunity(None, 30, _ref())


def test_parse_compact_relative_times():
    ref = _ref()
    assert parse_relative_posted("1h", ref) == ref - timedelta(hours=1)
    assert parse_relative_posted("5h ago", ref) == ref - timedelta(hours=5)
    assert parse_relative_posted("1d", ref) == ref - timedelta(days=1)
    assert parse_relative_posted("3d", ref) == ref - timedelta(days=3)
    assert parse_relative_posted("1w", ref) == ref - timedelta(weeks=1)
    assert parse_relative_posted("2w", ref) == ref - timedelta(weeks=2)
    assert parse_relative_posted("1mo", ref) == ref - timedelta(days=30)
    assert parse_relative_posted("2mo", ref) == ref - timedelta(days=60)
    assert parse_relative_posted("11mo", ref) == ref - timedelta(days=330)


def test_parse_absolute_date():
    ref = _ref()
    dt = parse_posted_time("September 15, 2026", ref)
    assert dt is not None
    assert dt.year == 2026 and dt.month == 9 and dt.day == 15


def test_parse_unknown_returns_none():
    assert parse_posted_time("unknown date", _ref()) is None
