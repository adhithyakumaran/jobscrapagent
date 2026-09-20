from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

RELATIVE_PATTERNS = [
    (re.compile(r"(\d+)\s*minute", re.I), "minutes"),
    (re.compile(r"(\d+)\s*hour", re.I), "hours"),
    (re.compile(r"(\d+)\s*day", re.I), "days"),
    (re.compile(r"(\d+)\s*week", re.I), "weeks"),
    (re.compile(r"(\d+)\s*month", re.I), "months"),
]


def parse_relative_posted(text: str, reference: datetime | None = None) -> datetime | None:
    ref = reference or datetime.now(timezone.utc)
    t = text.strip().lower()
    if "just now" in t:
        return ref
    for pattern, unit in RELATIVE_PATTERNS:
        m = pattern.search(t)
        if m:
            n = int(m.group(1))
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
    return None
