JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    source_url TEXT NOT NULL,
    company_name TEXT,
    job_title TEXT,
    description TEXT,
    location TEXT,
    experience_min INTEGER,
    experience_max INTEGER,
    employment_type TEXT,
    domain TEXT,
    skills TEXT,
    posted_at TEXT,
    discovered_at TEXT NOT NULL,
    application_url TEXT,
    application_method TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    is_fresher INTEGER,
    is_entry_level INTEGER,
    hiring_signal TEXT,
    relevance_score REAL NOT NULL DEFAULT 0,
    confidence_score REAL NOT NULL DEFAULT 0,
    duplicate_group_id TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    freshness_bucket TEXT,
    alternate_source_urls TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_posted ON jobs(posted_at);
CREATE INDEX IF NOT EXISTS idx_jobs_relevance ON jobs(relevance_score);
CREATE INDEX IF NOT EXISTS idx_jobs_dup_group ON jobs(duplicate_group_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_source_url ON jobs(source_url);
"""

SEARCH_RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS search_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    source TEXT,
    queries_attempted INTEGER DEFAULT 0,
    candidates_discovered INTEGER DEFAULT 0,
    parsed INTEGER DEFAULT 0,
    rejected INTEGER DEFAULT 0,
    duplicates INTEGER DEFAULT 0,
    new_opportunities INTEGER DEFAULT 0,
    high_confidence INTEGER DEFAULT 0,
    telegram_notifications INTEGER DEFAULT 0,
    notes TEXT
);
"""

NOTIFICATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    UNIQUE(job_id, channel)
);
"""
