from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class EducationConfig(BaseModel):
    degree: str = ""
    branch: str = ""
    graduation_year: int | None = None


class TelegramConfig(BaseModel):
    enabled: bool = False
    mode: str = "individual"  # individual | digest
    min_relevance: float = 40.0
    ui_url: str = "http://127.0.0.1:8765"
    bot_token: str = ""  # use TELEGRAM_BOT_TOKEN in .env
    chat_id: str = ""  # use TELEGRAM_CHAT_ID in .env


class NotificationsConfig(BaseModel):
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)


class CandidateConfig(BaseModel):
    experience_level: list[str] = Field(default_factory=list)
    education: EducationConfig = Field(default_factory=EducationConfig)
    locations: list[str] = Field(default_factory=list)
    target_domains: list[str] = Field(default_factory=lambda: ["any"])
    preferred_roles: list[str] = Field(default_factory=lambda: ["any"])
    excluded_keywords: list[str] = Field(default_factory=list)


class ProfileConfig(BaseModel):
    freshness_days: int = 30
    candidate: CandidateConfig = Field(default_factory=CandidateConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)


def default_profile_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / "config" / "profile.yaml"


def default_db_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "jobs.db"


def load_profile(path: Path | None = None) -> ProfileConfig:
    profile_path = path or default_profile_path()
    with open(profile_path, encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}
    return ProfileConfig.model_validate(raw)


def is_any(values: list[str]) -> bool:
    if not values:
        return True
    normalized = {v.strip().lower() for v in values}
    return "any" in normalized or "*" in normalized


class IntentMixConfig(BaseModel):
    hiring_post: float = 0.30
    job_listing: float = 0.40
    role_domain: float = 0.20
    experimental: float = 0.10


class LinkedInSourceConfig(BaseModel):
    enabled: bool = True
    max_pages_per_intent: int = 3
    max_results_per_intent: int = 50
    detail_fetch_limit_per_intent: int = 10
    max_post_pages_per_intent: int = 2
    max_posts_per_intent: int = 8
    delay_seconds: float = 2.0
    rate_limit_backoff_seconds: float = 8.0
    rate_limit_max_retries: int = 3
    intent_budget_per_run: int = 24
    intent_mix: IntentMixConfig = Field(default_factory=IntentMixConfig)
    source_relevance_boost: float = 3.0
    providers: list[str] = Field(
        default_factory=lambda: ["playwright", "session", "guest", "indexed"]
    )
    session_cookie_file: str = ""
    playwright_headless: bool = True
    indexed_search_engine: str = "duckduckgo"


class SourcesConfig(BaseModel):
    linkedin: LinkedInSourceConfig = Field(default_factory=LinkedInSourceConfig)


def default_sources_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / "config" / "sources.yaml"


def load_sources(path: Path | None = None) -> SourcesConfig:
    sources_path = path or default_sources_path()
    if not sources_path.exists():
        return SourcesConfig()
    with open(sources_path, encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}
    return SourcesConfig.model_validate(raw)
