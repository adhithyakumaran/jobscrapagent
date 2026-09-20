from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field

from jobfinder.config import ProfileConfig, load_profile, load_sources
from jobfinder.deduplication.dedup import DeduplicationService
from jobfinder.discovery.base import DiscoveryContext
from jobfinder.discovery.linkedin.composite import LinkedInCompositeProvider
from jobfinder.discovery.mock import MockDiscoveryProvider
from jobfinder.discovery.planner import plan_search_intents
from jobfinder.extraction.hiring import analyze_hiring_text
from jobfinder.actionable import has_actionable_path
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
    listing_intents: int = 0
    post_intents: int = 0
    pages_searched: int = 0
    candidates_discovered: int = 0
    parsed: int = 0
    rejected: int = 0
    duplicates: int = 0
    new_opportunities: int = 0
    high_confidence: int = 0
    telegram_notifications: int = 0
    formal_jobs: int = 0
    hiring_posts: int = 0
    high_hiring_signal: int = 0
    fresher_entry: int = 0
    relevant: int = 0
    rate_limit_hits: int = 0
    provider_notes: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def print_linkedin_scan_report(stats: ScanStats) -> None:
    print("\nLinkedIn Scan\n")
    print(f"Listing intents:\n{stats.listing_intents}\n")
    print(f"Post intents:\n{stats.post_intents}\n")
    print(f"Pages searched:\n{stats.pages_searched}\n")
    print(f"Candidates:\n{stats.candidates_discovered}\n")
    print(f"Formal jobs:\n{stats.formal_jobs}\n")
    print(f"Hiring posts:\n{stats.hiring_posts}\n")
    print(f"High hiring signal:\n{stats.high_hiring_signal}\n")
    print(f"Fresher/entry-level:\n{stats.fresher_entry}\n")
    print(f"Relevant:\n{stats.relevant}\n")
    print(f"Rejected:\n{stats.rejected}\n")
    print(f"Duplicates:\n{stats.duplicates}\n")
    print(f"New opportunities:\n{stats.new_opportunities}\n")
    if stats.rate_limit_hits:
        print(f"Rate limit backoffs:\n{stats.rate_limit_hits}\n")


def _post_group_id(post_url: str | None) -> str | None:
    if not post_url:
        return None
    return hashlib.sha256(post_url.encode()).hexdigest()[:32]


def _ingest_candidates(
    raw_list: list,
    profile: ProfileConfig,
    db: Database,
    scorer: RelevanceEngine,
    dedup: DeduplicationService,
    stats: ScanStats,
) -> None:
    existing = db.all_jobs_for_dedup()

    for raw in raw_list:
        is_post = (
            getattr(raw, "discovery_kind", None) == "hiring_post"
            or (raw.source_url and "/posts/" in raw.source_url)
        )
        analysis = analyze_hiring_text(raw.raw_text)
        if is_post and analysis.hiring_signal_strength == "low_hiring_signal":
            stats.rejected += 1
            continue
        if is_post and not analysis.is_hiring_related:
            stats.rejected += 1
            continue

        job = raw_to_opportunity(raw)
        stats.parsed += 1

        if not has_actionable_path(job):
            stats.rejected += 1
            continue

        if job.discovery_kind == "job_listing" or (
            job.source_url and "/jobs/view/" in job.source_url
        ):
            stats.formal_jobs += 1
        elif job.discovery_kind == "hiring_post" or is_post:
            stats.hiring_posts += 1

        if job.hiring_signal_strength == "high_hiring_signal":
            stats.high_hiring_signal += 1
        if job.is_fresher or job.is_entry_level:
            stats.fresher_entry += 1

        relevance, confidence, _breakdown = scorer.score(job)
        job.relevance_score = relevance
        job.confidence_score = confidence

        if relevance < MIN_RELEVANCE_TO_KEEP:
            stats.rejected += 1
            continue

        stats.relevant += 1

        if job.source_post_url:
            gid = _post_group_id(job.source_post_url)
            job.duplicate_group_id = gid

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
    if max_intents is not None and max_intents <= 15:
        li = li.model_copy(
            update={
                "max_pages_per_intent": min(li.max_pages_per_intent, 1),
                "max_results_per_intent": min(li.max_results_per_intent, 12),
                "detail_fetch_limit_per_intent": min(li.detail_fetch_limit_per_intent, 4),
                "max_posts_per_intent": min(li.max_posts_per_intent, 5),
            }
        )
    planned = plan_search_intents(profile, budget=budget, mix=li.intent_mix)
    provider = LinkedInCompositeProvider(li)
    dedup = DeduplicationService()
    scorer = RelevanceEngine(profile)

    run_id = db.create_search_run(provider.name)
    stats = ScanStats(
        intents_generated=planned.generated,
        intents_deduplicated=planned.deduplicated,
        queries_attempted=len(planned.selected),
        listing_intents=planned.by_type_selected.get("job_listing", 0)
        + planned.by_type_selected.get("role_domain", 0),
        post_intents=planned.by_type_selected.get("hiring_post", 0)
        + planned.by_type_selected.get("experimental", 0),
    )

    context = DiscoveryContext(intents=planned.selected)
    raw_list, provider_stats = provider.discover(context)
    stats.candidates_discovered = len(raw_list)
    for ps in provider_stats:
        stats.pages_searched += ps.pages_fetched
        stats.rate_limit_hits += ps.rate_limit_hits
        stats.provider_notes.append(
            f"{ps.provider}: success={ps.success} candidates={ps.candidates} pages={ps.pages_fetched}"
            f" rate_limits={ps.rate_limit_hits}"
            + (f" error={ps.error}" if ps.error else "")
        )

    _ingest_candidates(raw_list, profile, db, scorer, dedup, stats)
    _log_scan_summary(provider.name, stats)
    print_linkedin_scan_report(stats)

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
                "listing_intents": stats.listing_intents,
                "post_intents": stats.post_intents,
                "formal_jobs": stats.formal_jobs,
                "hiring_posts": stats.hiring_posts,
                "rate_limit_hits": stats.rate_limit_hits,
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
