from __future__ import annotations

import logging
from dataclasses import dataclass, field

from jobfinder.config import ProfileConfig, load_profile
from jobfinder.deduplication.dedup import DeduplicationService
from jobfinder.discovery.mock import MockDiscoveryProvider
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
    candidates_discovered: int = 0
    parsed: int = 0
    rejected: int = 0
    duplicates: int = 0
    new_opportunities: int = 0
    high_confidence: int = 0
    telegram_notifications: int = 0
    notes: list[str] = field(default_factory=list)


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

    logger.info("Scan started")
    logger.info("Source: %s", provider.name)
    logger.info("Queries attempted: %s", stats.queries_attempted)

    raw_list = provider.discover(intents)
    stats.candidates_discovered = len(raw_list)
    logger.info("Candidates discovered: %s", stats.candidates_discovered)

    existing = db.all_jobs_for_dedup()

    for raw in raw_list:
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

    logger.info("Parsed: %s", stats.parsed)
    logger.info("Rejected: %s", stats.rejected)
    logger.info("Duplicates: %s", stats.duplicates)
    logger.info("New opportunities: %s", stats.new_opportunities)
    logger.info("High-confidence: %s", stats.high_confidence)
    logger.info("Telegram notifications: %s", stats.telegram_notifications)

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
