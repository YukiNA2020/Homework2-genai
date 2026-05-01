"""Stage 2/8: MVP news monitoring pipeline.

This script ingests local sample items or configured RSS feeds, cleans and
summarizes them with a deterministic offline fallback, extracts domain
keywords, and stores structured records in SQLite. LLM calls are still reserved
as explicit extension points for later stages.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import logging
import re
import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from api_config import (
    DATABASE_PATH,
    DEFAULT_INGESTION_MODE,
    DEFAULT_LLM_CONFIG,
    LOG_DIR,
    RSS_CONFIG_PATH,
    SAMPLE_DATA_PATH,
    SQLITE_SCHEMA_PATH,
)


DOMAIN_KEYWORDS = [
    "ai",
    "artificial intelligence",
    "data center",
    "compute",
    "gpu",
    "chip",
    "semiconductor",
    "cloud",
    "power",
    "electricity",
    "grid",
    "energy",
    "copper",
    "lithium",
    "rare earths",
    "critical minerals",
    "supply chain",
    "export control",
    "sanctions",
    "conflict",
    "regulation",
    "trade restriction",
    "shipping",
    "permitting",
    "resource nationalism",
    "business continuity",
]

RSS_USER_AGENT = "AI-Geopolitical-Risk-Workflow/1.0 (+student-homework-rss-ingestion)"
RSS_FETCH_TIMEOUT_SECONDS = 15
DEFAULT_RSS_ITEMS_PER_SOURCE = 8


@dataclass
class IngestionStats:
    run_id: str
    started_at: str
    finished_at: str = ""
    input_mode: str = DEFAULT_INGESTION_MODE
    items_seen: int = 0
    items_inserted: int = 0
    duplicates_skipped: int = 0
    errors: int = 0
    notes: str = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def strip_html_markup(text: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text or "")
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return normalize_whitespace(html.unescape(text))


def split_sentences(text: str) -> list[str]:
    pieces = re.split(r"(?<=[.!?])\s+", text)
    return [piece.strip() for piece in pieces if piece.strip()]


def extract_keywords(title: str, content: str) -> list[str]:
    haystack = f"{title} {content}".lower()
    matched = [keyword for keyword in DOMAIN_KEYWORDS if keyword in haystack]
    return matched[:12]


def summarize_offline(title: str, content: str, keywords: list[str]) -> str:
    sentences = split_sentences(content)
    base_summary = " ".join(sentences[:2]) if sentences else title
    keyword_hint = ", ".join(keywords[:5]) if keywords else "general AI/business signals"
    return (
        f"{base_summary} Decision relevance signals: {keyword_hint}. "
        "This record is prepared for later relevance routing and classification."
    )


def content_hash(item: dict[str, Any], cleaned_content: str) -> str:
    stable_payload = {
        "title": normalize_whitespace(item.get("title", "")).lower(),
        "url": normalize_whitespace(item.get("url", "")).lower(),
        "content": cleaned_content.lower(),
    }
    encoded = json.dumps(stable_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def apply_schema(db_path: Path, schema_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.executescript(schema_path.read_text(encoding="utf-8"))


def setup_logger(run_id: str, log_dir: Path) -> tuple[logging.Logger, Path]:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{run_id}_news_monitoring.log"
    logger = logging.getLogger(f"news_monitoring.{run_id}")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger, log_path


def load_local_sample_items(sample_path: Path) -> list[dict[str, Any]]:
    if not sample_path.exists():
        raise FileNotFoundError(f"Sample data file not found: {sample_path}")
    data = read_json(sample_path)
    if not isinstance(data, list):
        raise ValueError("Sample data must be a JSON list.")
    return data


def child_by_name(element: ElementTree.Element, names: set[str]) -> ElementTree.Element | None:
    for child in list(element):
        if local_name(child.tag) in names:
            return child
    return None


def child_text(element: ElementTree.Element, names: set[str]) -> str:
    child = child_by_name(element, names)
    if child is None:
        return ""
    return normalize_whitespace("".join(child.itertext()))


def extract_rss_link(item: ElementTree.Element) -> str:
    link_text = child_text(item, {"link"})
    if link_text:
        return link_text

    for child in list(item):
        if local_name(child.tag) == "link":
            href = normalize_whitespace(child.attrib.get("href", ""))
            rel = child.attrib.get("rel", "alternate")
            if href and rel in {"alternate", ""}:
                return href
    return ""


def normalize_published_at(raw_value: str) -> str:
    raw_value = normalize_whitespace(raw_value)
    if not raw_value:
        return ""

    try:
        parsed = parsedate_to_datetime(raw_value)
    except (TypeError, ValueError, IndexError, OverflowError):
        return raw_value

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def fetch_url_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": RSS_USER_AGENT})
    with urlopen(request, timeout=RSS_FETCH_TIMEOUT_SECONDS) as response:  # noqa: S310 - configured public RSS URLs only.
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def parse_feed_entries(feed_text: str, source: dict[str, Any]) -> list[dict[str, Any]]:
    root = ElementTree.fromstring(feed_text)
    root_name = local_name(root.tag)

    if root_name == "rss":
        channel = child_by_name(root, {"channel"})
        entry_nodes = [
            child for child in list(channel)
            if local_name(child.tag) == "item"
        ] if channel is not None else []
    elif root_name == "feed":
        entry_nodes = [child for child in list(root) if local_name(child.tag) == "entry"]
    else:
        entry_nodes = [node for node in root.iter() if local_name(node.tag) in {"item", "entry"}]

    entries: list[dict[str, Any]] = []
    for node in entry_nodes:
        title = child_text(node, {"title"})
        url = extract_rss_link(node)
        published_at = normalize_published_at(
            child_text(node, {"pubdate", "published", "updated", "date"})
        )
        author = child_text(node, {"creator", "author"})
        if not author:
            author_node = child_by_name(node, {"author"})
            author = child_text(author_node, {"name"}) if author_node is not None else ""

        raw_content = (
            child_text(node, {"encoded"})
            or child_text(node, {"content"})
            or child_text(node, {"summary"})
            or child_text(node, {"description"})
        )
        cleaned_content = strip_html_markup(raw_content)
        if not cleaned_content and title:
            cleaned_content = title

        if not title or not cleaned_content:
            continue

        entries.append(
            {
                "source_id": source["source_id"],
                "source_name": source["source_name"],
                "source_type": source.get("source_type", "rss"),
                "title": strip_html_markup(title),
                "url": normalize_whitespace(url),
                "published_at": published_at,
                "author": strip_html_markup(author),
                "language": source.get("language", "en"),
                "content": cleaned_content,
            }
        )
    return entries


def enabled_rss_sources(config: dict[str, Any]) -> list[dict[str, Any]]:
    sources = config.get("rss_sources", [])
    if not isinstance(sources, list):
        raise ValueError("rss_sources.json must contain a list under 'rss_sources'.")
    return [
        source for source in sources
        if source.get("enabled", True) and source.get("url") and source.get("source_id")
    ]


def fetch_rss_items(
    rss_config_path: Path,
    logger: logging.Logger,
    max_items_per_source: int | None = None,
) -> list[dict[str, Any]]:
    if not rss_config_path.exists():
        logger.warning("RSS config file not found; skipping RSS fetch.")
        return []

    config = read_json(rss_config_path)
    sources = enabled_rss_sources(config)
    logger.info("Loaded %s enabled RSS sources from %s.", len(sources), rss_config_path)

    all_items: list[dict[str, Any]] = []
    for source in sources:
        source_limit = int(source.get("max_items", max_items_per_source or DEFAULT_RSS_ITEMS_PER_SOURCE))
        if max_items_per_source is not None:
            source_limit = min(source_limit, max_items_per_source)

        started = time.monotonic()
        try:
            feed_text = fetch_url_text(source["url"])
            parsed_items = parse_feed_entries(feed_text, source)
            selected_items = parsed_items[:source_limit]
            all_items.extend(selected_items)
            logger.info(
                "Fetched RSS source '%s': parsed=%s selected=%s url=%s duration=%.2fs",
                source["source_name"],
                len(parsed_items),
                len(selected_items),
                source["url"],
                time.monotonic() - started,
            )
        except (HTTPError, URLError, TimeoutError, ElementTree.ParseError, ValueError) as exc:
            logger.warning(
                "RSS source failed but run will continue: source=%s url=%s error=%s",
                source.get("source_name", source.get("source_id", "unknown")),
                source.get("url", ""),
                exc,
            )
    return all_items


def normalize_item(item: dict[str, Any], ingestion_method: str) -> dict[str, Any]:
    title = normalize_whitespace(item.get("title", ""))
    raw_content = normalize_whitespace(item.get("content", ""))
    cleaned_content = normalize_whitespace(raw_content)

    if not title:
        raise ValueError("News item is missing a title.")
    if not cleaned_content:
        raise ValueError(f"News item '{title}' is missing content.")

    keywords = extract_keywords(title, cleaned_content)
    summary = summarize_offline(title, cleaned_content, keywords)
    now = utc_now()

    return {
        "source_id": normalize_whitespace(item.get("source_id", "unknown_source")),
        "source_name": normalize_whitespace(item.get("source_name", "Unknown source")),
        "source_type": normalize_whitespace(item.get("source_type", "unknown")),
        "title": title,
        "url": normalize_whitespace(item.get("url", "")),
        "published_at": normalize_whitespace(item.get("published_at", "")),
        "author": normalize_whitespace(item.get("author", "")),
        "language": normalize_whitespace(item.get("language", "en")) or "en",
        "raw_content": raw_content,
        "cleaned_content": cleaned_content,
        "summary": summary,
        "keywords": keywords,
        "ingestion_method": ingestion_method,
        "content_hash": content_hash(item, cleaned_content),
        "status": "monitored",
        "created_at": now,
        "updated_at": now,
    }


def upsert_source(connection: sqlite3.Connection, item: dict[str, Any]) -> None:
    now = utc_now()
    source_home = item["url"]
    parsed_url = urlparse(item["url"])
    if parsed_url.scheme and parsed_url.netloc:
        source_home = f"{parsed_url.scheme}://{parsed_url.netloc}"

    connection.execute(
        """
        INSERT INTO source_registry (
            source_id, source_name, source_type, url, region, credibility_tier,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_id) DO UPDATE SET
            source_name = excluded.source_name,
            source_type = excluded.source_type,
            url = excluded.url,
            updated_at = excluded.updated_at
        """,
        (
            item["source_id"],
            item["source_name"],
            item["source_type"],
            source_home,
            "",
            "sample_or_configured",
            now,
            now,
        ),
    )


def insert_news_item(connection: sqlite3.Connection, item: dict[str, Any]) -> bool:
    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO news_items (
            source_id, source_name, source_type, title, url, published_at, author,
            language, raw_content, cleaned_content, summary, keywords,
            ingestion_method, content_hash, status, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item["source_id"],
            item["source_name"],
            item["source_type"],
            item["title"],
            item["url"],
            item["published_at"],
            item["author"],
            item["language"],
            item["raw_content"],
            item["cleaned_content"],
            item["summary"],
            json.dumps(item["keywords"], ensure_ascii=False),
            item["ingestion_method"],
            item["content_hash"],
            item["status"],
            item["created_at"],
            item["updated_at"],
        ),
    )
    return cursor.rowcount == 1


def record_run(connection: sqlite3.Connection, stats: IngestionStats) -> None:
    connection.execute(
        """
        INSERT INTO ingestion_runs (
            run_id, started_at, finished_at, input_mode, items_seen,
            items_inserted, duplicates_skipped, errors, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            stats.run_id,
            stats.started_at,
            stats.finished_at,
            stats.input_mode,
            stats.items_seen,
            stats.items_inserted,
            stats.duplicates_skipped,
            stats.errors,
            stats.notes,
        ),
    )


def collect_items(
    input_mode: str,
    logger: logging.Logger,
    rss_limit: int | None = None,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    if input_mode in {"local_sample", "all"}:
        sample_items = load_local_sample_items(SAMPLE_DATA_PATH)
        logger.info("Loaded %s local sample items from %s.", len(sample_items), SAMPLE_DATA_PATH)
        for item in sample_items:
            item["_ingestion_method"] = "local_sample"
        items.extend(sample_items)

    if input_mode in {"rss", "rss_placeholder", "all"}:
        if input_mode == "rss_placeholder":
            logger.warning("'rss_placeholder' is deprecated; using real RSS fetch mode.")
        rss_items = fetch_rss_items(RSS_CONFIG_PATH, logger, rss_limit)
        for item in rss_items:
            item["_ingestion_method"] = "rss"
        items.extend(rss_items)

    return items


def run_monitoring(
    input_mode: str,
    db_path: Path,
    rss_limit: int | None = None,
) -> tuple[IngestionStats, Path]:
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    logger, log_path = setup_logger(run_id, LOG_DIR)
    stats = IngestionStats(run_id=run_id, started_at=utc_now(), input_mode=input_mode)

    logger.info("Starting Stage 2 news monitoring run: %s", run_id)
    logger.info("LLM provider placeholder: %s | enabled=%s", DEFAULT_LLM_CONFIG["provider"], DEFAULT_LLM_CONFIG["enabled"])

    apply_schema(db_path, SQLITE_SCHEMA_PATH)
    items = collect_items(input_mode, logger, rss_limit)
    stats.items_seen = len(items)

    with sqlite3.connect(db_path) as connection:
        for item in items:
            ingestion_method = item.get("_ingestion_method", input_mode)
            try:
                normalized = normalize_item(item, ingestion_method)
                upsert_source(connection, normalized)
                inserted = insert_news_item(connection, normalized)
                if inserted:
                    stats.items_inserted += 1
                    logger.info("Inserted: %s", normalized["title"])
                else:
                    stats.duplicates_skipped += 1
                    logger.info("Duplicate skipped: %s", normalized["title"])
            except Exception as exc:  # noqa: BLE001 - keep stage run resilient.
                stats.errors += 1
                logger.error("Failed to process item: %s", exc)

        stats.finished_at = utc_now()
        if input_mode in {"rss", "all", "rss_placeholder"}:
            stats.notes = (
                "Stage 8 RSS ingestion completed with resilient per-source failure "
                "handling. Local sample mode remains available as offline fallback."
            )
        else:
            stats.notes = (
                "Offline MVP ingestion completed. Real RSS mode is available through "
                "--input-mode rss; LLM calls are reserved for later extension."
            )
        record_run(connection, stats)

    logger.info(
        "Completed run. seen=%s inserted=%s duplicates=%s errors=%s",
        stats.items_seen,
        stats.items_inserted,
        stats.duplicates_skipped,
        stats.errors,
    )
    return stats, log_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Stage 2 news monitoring ingestion.")
    parser.add_argument(
        "--input-mode",
        choices=["local_sample", "rss", "rss_placeholder", "all"],
        default=DEFAULT_INGESTION_MODE,
        help="Input mode for this run. Default: local_sample.",
    )
    parser.add_argument(
        "--rss-limit",
        type=int,
        default=None,
        help="Optional maximum RSS items per source for quick tests.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DATABASE_PATH,
        help="SQLite database path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stats, log_path = run_monitoring(args.input_mode, args.db_path, args.rss_limit)
    print("\nStage 2 news monitoring completed")
    print(f"Run ID: {stats.run_id}")
    print(f"Database: {args.db_path}")
    print(f"Items seen: {stats.items_seen}")
    print(f"Inserted: {stats.items_inserted}")
    print(f"Duplicates skipped: {stats.duplicates_skipped}")
    print(f"Errors: {stats.errors}")
    print(f"Log file: {log_path}")


if __name__ == "__main__":
    main()
