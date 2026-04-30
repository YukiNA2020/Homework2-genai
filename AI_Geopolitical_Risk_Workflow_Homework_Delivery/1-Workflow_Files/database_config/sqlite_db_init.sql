CREATE TABLE IF NOT EXISTS source_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL UNIQUE,
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    url TEXT,
    region TEXT,
    credibility_tier TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS news_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    published_at TEXT,
    author TEXT,
    language TEXT NOT NULL DEFAULT 'en',
    raw_content TEXT NOT NULL,
    cleaned_content TEXT NOT NULL,
    summary TEXT NOT NULL,
    keywords TEXT NOT NULL,
    ingestion_method TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'monitored',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_news_items_source_id ON news_items(source_id);
CREATE INDEX IF NOT EXISTS idx_news_items_published_at ON news_items(published_at);
CREATE INDEX IF NOT EXISTS idx_news_items_status ON news_items(status);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL UNIQUE,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    input_mode TEXT NOT NULL,
    items_seen INTEGER NOT NULL,
    items_inserted INTEGER NOT NULL,
    duplicates_skipped INTEGER NOT NULL,
    errors INTEGER NOT NULL,
    notes TEXT
);
