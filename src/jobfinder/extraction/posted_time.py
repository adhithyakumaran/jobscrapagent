from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from dateutil import parser as date_parser

RELATIVE_PATTERNS = [
    (re.compile(r"(\d+)\s*minute", re.I), "minutes"),
    (re.compile(r"(\d+)\s*hour", re.I), "hours"),
    (re.compile(r"(\d+)\s*day", re.I), "days"),
    (re.compile(r"(\d+)\s*week", re.I), "weeks"),
    (re.compile(r"(\d+)\s*month", re.I), "months"),
]

# Compact: 1h, 5h, 1d, 3d, 1w, 2w, 1mo, 2mo, 11mo (optional trailing "ago")
COMPACT_RE = re.compile(
    r"(?:^|\b)(\d+)\s*"
    r"(h|hr|hrs|hour|hours|d|day|days|w|wk|wks|week|weeks|mo|mon|mos|month|months)"
    r"(?:\s*ago)?\b",
    re.I,
)


def _subtract_unit(ref: datetime, n: int, unit: str) -> datetime:
    if unit == "minutes":
        return ref - timedelta(minutes=n)
    if unit == "hours":
        return ref - timedelta(hours=n)
    if unit == "days":
        return ref - timedelta(days=n)
    if unit == "weeks":
        return ref - timedelta(weeks=n)
    if unit == "months":
        return ref - timedelta(days=n * 30)
    return ref


def _unit_from_token(token: str) -> str | None:
    t = token.lower()
    if t in {"h", "hr", "hrs", "hour", "hours"}:
        return "hours"
    if t in {"d", "day", "days"}:
        return "days"
    if t in {"w", "wk", "wks", "week", "weeks"}:
        return "weeks"
    if t in {"mo", "mon", "mos", "month", "months"}:
        return "months"
    return None


def parse_absolute_posted(text: str) -> datetime | None:
    t = text.strip()
    if not t:
        return None
    lowered = t.lower()
    if lowered in {"unknown", "n/a", "na", "—", "-"}:
        return None
    try:
        dt = date_parser.parse(t, fuzzy=True)
    except (ValueError, TypeError, OverflowError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def parse_relative_posted(text: str, reference: datetime | None = None) -> datetime | None:
    ref = reference or datetime.now(timezone.utc)
    t = text.strip().lower()
    if not t:
        return None
    if "just now" in t:
        return ref
    m = COMPACT_RE.search(t)
    if m:
        unit = _unit_from_token(m.group(2))
        if unit:
            return _subtract_unit(ref, int(m.group(1)), unit)
    for pattern, unit in RELATIVE_PATTERNS:
        m = pattern.search(t)
        if m:
            return _subtract_unit(ref, int(m.group(1)), unit)
    return None


def parse_posted_time(text: str, reference: datetime | None = None) -> datetime | None:
    """Parse LinkedIn-style relative or absolute posted time into UTC datetime."""
    if not text or not str(text).strip():
        return None
    rel = parse_relative_posted(str(text), reference)
    if rel is not None:
        return rel
    return parse_absolute_posted(str(text))
