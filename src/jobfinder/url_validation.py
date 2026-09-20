from __future__ import annotations

from urllib.parse import urlparse


def is_valid_http_url(url: str | None) -> bool:
    """Absolute http(s) URL suitable for Telegram inline buttons."""
    if url is None:
        return False
    u = url.strip()
    if not u:
        return False
    try:
        parsed = urlparse(u)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    if not parsed.netloc:
        return False
    if " " in u:
        return False
    return True


def is_valid_linkedin_url(url: str | None) -> bool:
    if not is_valid_http_url(url):
        return False
    host = urlparse(url.strip()).netloc.lower()
    return host.endswith("linkedin.com") or host == "lnkd.in"


def is_valid_apply_url(url: str | None) -> bool:
    if not is_valid_http_url(url):
        return False
    lower = url.strip().lower()
    if lower.startswith("mailto:") or lower.startswith("tel:"):
        return False
    return True
