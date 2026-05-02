"""Stage 13 migration helpers for daily-run data lineage.

The existing workflow stores one latest result per news item/category. Stage 13
adds run-scoped metadata so daily review packages can tell whether a candidate
was produced from the current RSS run, the local sample baseline, or a fallback
state.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


def apply_schema_with_migrations(db_path: Path, schema_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.executescript(schema_path.read_text(encoding="utf-8"))
        ensure_stage13_schema(connection)


def ensure_columns(
    connection: sqlite3.Connection,
    table_name: str,
    column_definitions: dict[str, str],
) -> None:
    existing = {row[1] for row in connection.execute(f"PRAGMA table_info({table_name})")}
    for column_name, definition in column_definitions.items():
        if column_name not in existing:
            connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def ensure_stage13_schema(connection: sqlite3.Connection) -> None:
    ensure_columns(
        connection,
        "news_items",
        {
            "ingestion_run_id": "TEXT",
            "workflow_run_id": "TEXT",
            "daily_run_id": "TEXT",
        },
    )
    ensure_columns(
        connection,
        "ingestion_runs",
        {
            "workflow_run_id": "TEXT",
            "daily_run_id": "TEXT",
        },
    )
    ensure_columns(
        connection,
        "relevance_routing_results",
        {
            "routing_run_id": "TEXT",
            "workflow_run_id": "TEXT",
            "daily_run_id": "TEXT",
        },
    )
    ensure_columns(
        connection,
        "routing_runs",
        {
            "workflow_run_id": "TEXT",
            "daily_run_id": "TEXT",
        },
    )
    ensure_columns(
        connection,
        "classification_results",
        {
            "classification_run_id": "TEXT",
            "workflow_run_id": "TEXT",
            "daily_run_id": "TEXT",
        },
    )
    ensure_columns(
        connection,
        "classification_runs",
        {
            "workflow_run_id": "TEXT",
            "daily_run_id": "TEXT",
        },
    )
    ensure_columns(
        connection,
        "linkedin_content_results",
        {
            "content_run_id": "TEXT",
            "workflow_run_id": "TEXT",
            "daily_run_id": "TEXT",
            "lineage_mode": "TEXT NOT NULL DEFAULT 'legacy'",
        },
    )
    ensure_columns(
        connection,
        "linkedin_content_runs",
        {
            "workflow_run_id": "TEXT",
            "daily_run_id": "TEXT",
            "lineage_mode": "TEXT NOT NULL DEFAULT 'legacy'",
        },
    )
    ensure_columns(
        connection,
        "image_generation_results",
        {
            "image_generation_run_id": "TEXT",
            "workflow_run_id": "TEXT",
            "daily_run_id": "TEXT",
            "lineage_mode": "TEXT NOT NULL DEFAULT 'legacy'",
        },
    )
    ensure_columns(
        connection,
        "image_generation_runs",
        {
            "workflow_run_id": "TEXT",
            "daily_run_id": "TEXT",
            "lineage_mode": "TEXT NOT NULL DEFAULT 'legacy'",
        },
    )
    ensure_columns(
        connection,
        "daily_workflow_runs",
        {
            "lineage_mode": "TEXT NOT NULL DEFAULT 'legacy'",
            "no_candidate_reason": "TEXT NOT NULL DEFAULT ''",
        },
    )
    ensure_columns(
        connection,
        "review_queue_items",
        {
            "lineage_mode": "TEXT NOT NULL DEFAULT 'legacy'",
        },
    )

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS run_item_lineage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_id INTEGER NOT NULL,
            ingestion_run_id TEXT NOT NULL,
            workflow_run_id TEXT,
            daily_run_id TEXT,
            source_mode TEXT NOT NULL,
            ingestion_method TEXT NOT NULL,
            lineage_status TEXT NOT NULL,
            seen_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(ingestion_run_id, news_id),
            FOREIGN KEY(news_id) REFERENCES news_items(id)
        );

        CREATE INDEX IF NOT EXISTS idx_run_item_lineage_news_id
        ON run_item_lineage(news_id);

        CREATE INDEX IF NOT EXISTS idx_run_item_lineage_ingestion_run
        ON run_item_lineage(ingestion_run_id);

        CREATE INDEX IF NOT EXISTS idx_run_item_lineage_workflow_run
        ON run_item_lineage(workflow_run_id);

        CREATE INDEX IF NOT EXISTS idx_run_item_lineage_daily_run
        ON run_item_lineage(daily_run_id);

        CREATE INDEX IF NOT EXISTS idx_run_item_lineage_source_mode
        ON run_item_lineage(source_mode);

        CREATE INDEX IF NOT EXISTS idx_news_items_ingestion_run
        ON news_items(ingestion_run_id);

        CREATE INDEX IF NOT EXISTS idx_news_items_workflow_run
        ON news_items(workflow_run_id);

        CREATE INDEX IF NOT EXISTS idx_news_items_daily_run
        ON news_items(daily_run_id);

        CREATE INDEX IF NOT EXISTS idx_routing_results_workflow_run
        ON relevance_routing_results(workflow_run_id);

        CREATE INDEX IF NOT EXISTS idx_routing_results_daily_run
        ON relevance_routing_results(daily_run_id);

        CREATE INDEX IF NOT EXISTS idx_classification_results_workflow_run
        ON classification_results(workflow_run_id);

        CREATE INDEX IF NOT EXISTS idx_classification_results_daily_run
        ON classification_results(daily_run_id);

        CREATE INDEX IF NOT EXISTS idx_linkedin_content_workflow_run
        ON linkedin_content_results(workflow_run_id);

        CREATE INDEX IF NOT EXISTS idx_linkedin_content_daily_run
        ON linkedin_content_results(daily_run_id);

        CREATE INDEX IF NOT EXISTS idx_image_generation_workflow_run
        ON image_generation_results(workflow_run_id);

        CREATE INDEX IF NOT EXISTS idx_image_generation_daily_run
        ON image_generation_results(daily_run_id);
        """
    )


def source_mode_for_item(stage2_input_mode: str, ingestion_method: str) -> str:
    if ingestion_method == "rss":
        return "rss_current_run"
    if ingestion_method == "local_sample":
        return "local_sample_baseline"
    if stage2_input_mode == "rss":
        return "rss_current_run"
    return "fallback"


def classify_lineage_mode(source_modes: list[str]) -> str:
    unique_modes = {mode for mode in source_modes if mode}
    if not unique_modes:
        return "fallback"
    if unique_modes == {"rss_current_run"}:
        return "rss_current_run"
    if unique_modes == {"local_sample_baseline"}:
        return "local_sample_baseline"
    if "rss_current_run" in unique_modes and "local_sample_baseline" not in unique_modes:
        return "rss_current_run"
    if "rss_current_run" in unique_modes:
        return "mixed_current_run"
    return sorted(unique_modes)[0]


def row_value(row: sqlite3.Row, key: str, default: Any = "") -> Any:
    return row[key] if key in row.keys() else default
