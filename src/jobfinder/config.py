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
    bot_token: str = ""
    chat_id: str = ""


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


class LinkedInSourceConfig(BaseModel):
    enabled: bool = True
    max_pages_per_intent: int = 3
    max_results_per_intent: int = 50
    detail_fetch_limit_per_intent: int = 10
    delay_seconds: float = 2.0
    intent_budget_per_run: int = 24
    source_relevance_boost: float = 3.0
    providers: list[str] = Field(default_factory=lambda: ["guest", "playwright", "indexed"])
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
