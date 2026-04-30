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

CREATE TABLE IF NOT EXISTS relevance_routing_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    news_id INTEGER NOT NULL UNIQUE,
    rule_passed INTEGER NOT NULL,
    ai_signal_terms TEXT NOT NULL,
    geopolitical_signal_terms TEXT NOT NULL,
    exclude_terms TEXT NOT NULL,
    relevance_score REAL NOT NULL,
    decision TEXT NOT NULL,
    rationale TEXT NOT NULL,
    scoring_breakdown TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    model_provider TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(news_id) REFERENCES news_items(id)
);

CREATE INDEX IF NOT EXISTS idx_relevance_routing_news_id
ON relevance_routing_results(news_id);

CREATE INDEX IF NOT EXISTS idx_relevance_routing_decision
ON relevance_routing_results(decision);

CREATE TABLE IF NOT EXISTS routing_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL UNIQUE,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    items_seen INTEGER NOT NULL,
    items_routed INTEGER NOT NULL,
    items_kept INTEGER NOT NULL,
    items_filtered INTEGER NOT NULL,
    errors INTEGER NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS classification_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    news_id INTEGER NOT NULL UNIQUE,
    primary_category TEXT NOT NULL,
    auxiliary_tags TEXT NOT NULL,
    confidence REAL NOT NULL,
    rationale TEXT NOT NULL,
    category_signal_terms TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    model_provider TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(news_id) REFERENCES news_items(id)
);

CREATE INDEX IF NOT EXISTS idx_classification_news_id
ON classification_results(news_id);

CREATE INDEX IF NOT EXISTS idx_classification_primary_category
ON classification_results(primary_category);

CREATE TABLE IF NOT EXISTS classification_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL UNIQUE,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    items_seen INTEGER NOT NULL,
    items_classified INTEGER NOT NULL,
    errors INTEGER NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS kol_analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kol_name TEXT NOT NULL UNIQUE,
    focus_area TEXT NOT NULL,
    sample_basis TEXT NOT NULL,
    hook_pattern TEXT NOT NULL,
    structure_pattern TEXT NOT NULL,
    credibility_pattern TEXT NOT NULL,
    interaction_pattern TEXT NOT NULL,
    style_pattern TEXT NOT NULL,
    transferable_rules TEXT NOT NULL,
    limitations TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    model_provider TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_kol_analysis_name
ON kol_analysis_results(kol_name);

CREATE TABLE IF NOT EXISTS kol_analysis_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL UNIQUE,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    profiles_analyzed INTEGER NOT NULL,
    outputs_written INTEGER NOT NULL,
    errors INTEGER NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS linkedin_content_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    primary_category TEXT NOT NULL UNIQUE,
    target_audience TEXT NOT NULL,
    tone_positioning TEXT NOT NULL,
    source_news_ids TEXT NOT NULL,
    source_titles TEXT NOT NULL,
    evidence_basis TEXT NOT NULL,
    linkedin_post TEXT NOT NULL,
    visual_prompt TEXT NOT NULL,
    quality_score_self_check TEXT NOT NULL,
    output_path TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    model_provider TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_linkedin_content_primary_category
ON linkedin_content_results(primary_category);

CREATE TABLE IF NOT EXISTS linkedin_content_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL UNIQUE,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    categories_seen INTEGER NOT NULL,
    posts_generated INTEGER NOT NULL,
    outputs_written INTEGER NOT NULL,
    errors INTEGER NOT NULL,
    notes TEXT
);
