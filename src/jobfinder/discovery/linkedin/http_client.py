from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import httpx

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


@dataclass
class FetchResult:
    html: str | None
    status_code: int | None = None
    rate_limited: bool = False


def load_cookie_header(cookie_file: str) -> dict[str, str]:
    path = Path(cookie_file)
    if not path.exists():
        return {}
    cookies: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" in line:
            parts = line.split("\t")
            if len(parts) >= 7:
                cookies.append(f"{parts[5]}={parts[6]}")
        elif "=" in line:
            cookies.append(line)
    if cookies:
        return {"Cookie": "; ".join(cookies)}
    return {}


def fetch_url(
    url: str,
    *,
    delay: float = 0,
    extra_headers: dict[str, str] | None = None,
    timeout: float = 25.0,
) -> FetchResult:
    if delay > 0:
        time.sleep(delay)
    headers = {**DEFAULT_HEADERS, **(extra_headers or {})}
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers) as client:
            resp = client.get(url)
            if resp.status_code == 429:
                return FetchResult(None, resp.status_code, rate_limited=True)
            if resp.status_code >= 400:
                return FetchResult(None, resp.status_code)
            return FetchResult(resp.text, resp.status_code)
    except httpx.HTTPError:
        return FetchResult(None, None)
