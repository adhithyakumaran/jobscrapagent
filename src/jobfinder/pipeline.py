from __future__ import annotations

import logging
from dataclasses import dataclass, field

from jobfinder.config import ProfileConfig, load_profile, load_sources
from jobfinder.deduplication.dedup import DeduplicationService
from jobfinder.discovery.base import DiscoveryContext
from jobfinder.discovery.linkedin.composite import LinkedInCompositeProvider
from jobfinder.discovery.mock import MockDiscoveryProvider
from jobfinder.discovery.planner import plan_search_intents
from jobfinder.extraction.hiring import analyze_hiring_text
from jobfinder.extraction.normalizer import raw_to_opportunity
from jobfinder.matching.intents import generate_search_intents
from jobfinder.matching.relevance import RelevanceEngine
from jobfinder.storage.db import Database

logger = logging.getLogger(__name__)

HIGH_CONFIDENCE_THRESHOLD = 60.0
MIN_RELEVANCE_TO_KEEP = 15.0


@dataclass
class ScanStats:
    queries_attempted: int = 0
    intents_generated: int = 0
    intents_deduplicated: int = 0
    candidates_discovered: int = 0
    parsed: int = 0
    rejected: int = 0
    duplicates: int = 0
    new_opportunities: int = 0
    high_confidence: int = 0
    telegram_notifications: int = 0
    provider_notes: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _ingest_candidates(
    raw_list: list,
    profile: ProfileConfig,
    db: Database,
    scorer: RelevanceEngine,
    dedup: DeduplicationService,
    stats: ScanStats,
    *,
    skip_non_hiring_linkedin_posts: bool = True,
) -> None:
    existing = db.all_jobs_for_dedup()

    for raw in raw_list:
        if skip_non_hiring_linkedin_posts and getattr(raw, "discovery_kind", None) == "hiring_post":
            if not analyze_hiring_text(raw.raw_text).is_hiring_related:
                stats.rejected += 1
                continue

        job = raw_to_opportunity(raw)
        stats.parsed += 1

        relevance, confidence, _breakdown = scorer.score(job)
        job.relevance_score = relevance
        job.confidence_score = confidence

        if relevance < MIN_RELEVANCE_TO_KEEP:
            stats.rejected += 1
            continue

        if db.get_job_by_source_url(job.source_url):
            stats.duplicates += 1
            continue

        dup = dedup.find_duplicate(job, existing)
        if dup.is_duplicate and dup.canonical:
            stats.duplicates += 1
            canonical = dup.canonical
            dedup.merge_duplicate(canonical, job)
            db.update_job(canonical)
            continue

        if confidence >= HIGH_CONFIDENCE_THRESHOLD:
            stats.high_confidence += 1

        db.insert_job(job)
        existing.append(job)
        stats.new_opportunities += 1


def _log_scan_summary(source: str, stats: ScanStats) -> None:
    logger.info("Scan started")
    logger.info("Source: %s", source)
    if stats.intents_generated:
        logger.info("Intents generated: %s", stats.intents_generated)
        logger.info("Intents deduplicated: %s", stats.intents_deduplicated)
    logger.info("Queries attempted: %s", stats.queries_attempted)
    logger.info("Candidates discovered: %s", stats.candidates_discovered)
    logger.info("Parsed: %s", stats.parsed)
    logger.info("Rejected: %s", stats.rejected)
    logger.info("Duplicates: %s", stats.duplicates)
    logger.info("New opportunities: %s", stats.new_opportunities)
    logger.info("High-confidence: %s", stats.high_confidence)
    logger.info("Telegram notifications: %s", stats.telegram_notifications)
    for note in stats.provider_notes:
        logger.info("  %s", note)


def run_mock_scan(
    db: Database | None = None,
    profile: ProfileConfig | None = None,
    max_intents: int | None = None,
) -> ScanStats:
    profile = profile or load_profile()
    db = db or Database()
    db.init_schema()

    intents = generate_search_intents(profile, max_intents=max_intents)
    provider = MockDiscoveryProvider()
    dedup = DeduplicationService()
    scorer = RelevanceEngine(profile)

    run_id = db.create_search_run(provider.name)
    stats = ScanStats(queries_attempted=len(intents))

    context = DiscoveryContext(intents=intents)
    raw_list = provider.discover(context)
    stats.candidates_discovered = len(raw_list)
    _ingest_candidates(raw_list, profile, db, scorer, dedup, stats, skip_non_hiring_linkedin_posts=False)
    _log_scan_summary(provider.name, stats)

    db.finish_search_run(
        run_id,
        {
            "queries_attempted": stats.queries_attempted,
            "candidates_discovered": stats.candidates_discovered,
            "parsed": stats.parsed,
            "rejected": stats.rejected,
            "duplicates": stats.duplicates,
            "new_opportunities": stats.new_opportunities,
            "high_confidence": stats.high_confidence,
            "telegram_notifications": stats.telegram_notifications,
        },
    )
    return stats


def run_linkedin_scan(
    db: Database | None = None,
    profile: ProfileConfig | None = None,
    max_intents: int | None = None,
) -> ScanStats:
    profile = profile or load_profile()
    sources = load_sources()
    li = sources.linkedin
    if not li.enabled:
        raise RuntimeError("LinkedIn discovery is disabled in config/sources.yaml")

    db = db or Database()
    db.init_schema()

    budget = max_intents if max_intents is not None else li.intent_budget_per_run
    if max_intents is not None and max_intents <= 5:
        # Controlled live validation — keep request volume small
        li = li.model_copy(
            update={
                "max_pages_per_intent": min(li.max_pages_per_intent, 1),
                "max_results_per_intent": min(li.max_results_per_intent, 12),
                "detail_fetch_limit_per_intent": min(li.detail_fetch_limit_per_intent, 5),
            }
        )
    planned = plan_search_intents(profile, budget=budget)
    provider = LinkedInCompositeProvider(li)
    dedup = DeduplicationService()
    scorer = RelevanceEngine(profile)

    run_id = db.create_search_run(provider.name)
    stats = ScanStats(
        intents_generated=planned.generated,
        intents_deduplicated=planned.deduplicated,
        queries_attempted=len(planned.selected),
    )

    context = DiscoveryContext(intents=planned.selected)
    raw_list, provider_stats = provider.discover(context)
    stats.candidates_discovered = len(raw_list)
    for ps in provider_stats:
        stats.provider_notes.append(
            f"{ps.provider}: success={ps.success} candidates={ps.candidates} pages={ps.pages_fetched}"
            + (f" error={ps.error}" if ps.error else "")
        )

    _ingest_candidates(raw_list, profile, db, scorer, dedup, stats)
    _log_scan_summary(provider.name, stats)

    db.finish_search_run(
        run_id,
        {
            "queries_attempted": stats.queries_attempted,
            "candidates_discovered": stats.candidates_discovered,
            "parsed": stats.parsed,
            "rejected": stats.rejected,
            "duplicates": stats.duplicates,
            "new_opportunities": stats.new_opportunities,
            "high_confidence": stats.high_confidence,
            "telegram_notifications": stats.telegram_notifications,
            "notes": {
                "intents_generated": stats.intents_generated,
                "intents_deduplicated": stats.intents_deduplicated,
                "providers": stats.provider_notes,
            },
        },
    )
    return stats


def run_scan(
    source: str = "linkedin",
    mock: bool = False,
    max_intents: int | None = None,
) -> ScanStats:
    if mock or source == "mock":
        return run_mock_scan(max_intents=max_intents)
    if source == "linkedin":
        return run_linkedin_scan(max_intents=max_intents)
    raise ValueError(f"Unknown source: {source}")
