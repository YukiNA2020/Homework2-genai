"""Stage 3B/10: business-relevant information classification.

This script classifies routed and retained news into the two project categories
defined in the roadmap, then assigns optional auxiliary tags. It can use the
unified LLM client while retaining the deterministic offline MVP contract.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api_config import DATABASE_PATH, DEFAULT_LLM_CONFIG, LOG_DIR, SQLITE_SCHEMA_PATH
from llm_stage_utils import (
    LLM_MODE_CHOICES,
    build_llm_client,
    model_provider_label,
    prompt_version_label,
    require_online_success,
)


PROMPT_VERSION_BASE = "information_classification_v2_stage10"

CATEGORY_RULES = {
    "AI算力基础设施地缘风险": {
        "definition": (
            "Regional conflict, policy controls, energy constraints, data center "
            "site selection, subsea cable, cloud, and compute infrastructure risk."
        ),
        "keywords": [
            "data center",
            "compute",
            "cloud",
            "gpu",
            "accelerator",
            "power",
            "electricity",
            "grid",
            "energy",
            "export control",
            "regional",
            "network",
            "business continuity",
            "deployment",
            "capacity",
        ],
    },
    "AI关键矿产供应链与地缘政治": {
        "definition": (
            "Critical mineral supply shifts affecting AI infrastructure cost, "
            "chip production, data center construction, and investment pacing."
        ),
        "keywords": [
            "copper",
            "lithium",
            "rare earths",
            "critical minerals",
            "mine",
            "mining",
            "mineral",
            "resource nationalism",
            "producing regions",
            "supply concentration",
            "shipping constraints",
            "semiconductor manufacturing",
            "transmission",
        ],
    },
}

AUXILIARY_TAG_RULES = {
    "AI芯片出口管制": [
        "export control",
        "export-control",
        "gpu",
        "accelerator",
        "advanced accelerators",
        "compliance controls",
        "advanced process restrictions",
    ],
    "区域冲突影响": [
        "conflict",
        "regional conflict",
        "shipping disruption",
        "shipping insurance",
        "energy security",
        "energy-security",
        "backup fuel",
        "logistics",
        "supplier concentration",
    ],
    "全球AI治理": [
        "regulation",
        "policy",
        "governance",
        "cross-border",
        "compliance",
        "trade restriction",
        "tariff",
        "guidance",
    ],
}


@dataclass
class ClassificationStats:
    run_id: str
    started_at: str
    finished_at: str = ""
    items_seen: int = 0
    items_classified: int = 0
    errors: int = 0
    notes: str = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_text(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text or "").strip().lower()
    return normalized.replace("‑", "-").replace("–", "-").replace("—", "-")


def parse_json_list(raw_value: str) -> list[str]:
    try:
        value = json.loads(raw_value or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def build_analysis_text(item: sqlite3.Row) -> str:
    keyword_text = " ".join(parse_json_list(item["keywords"]))
    routing_terms = " ".join(
        parse_json_list(item["ai_signal_terms"])
        + parse_json_list(item["geopolitical_signal_terms"])
    )
    return normalize_text(
        " ".join(
            [
                item["title"],
                item["summary"],
                item["cleaned_content"],
                keyword_text,
                routing_terms,
            ]
        )
    )


def find_terms(terms: list[str], text: str) -> list[str]:
    matched = []
    for term in terms:
        normalized_term = normalize_text(term)
        if normalized_term and normalized_term in text:
            matched.append(term)
    return matched


def apply_schema(db_path: Path, schema_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.executescript(schema_path.read_text(encoding="utf-8"))


def setup_logger(run_id: str) -> tuple[logging.Logger, Path]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{run_id}_information_classification.log"
    logger = logging.getLogger(f"information_classification.{run_id}")
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


def choose_primary_category(text: str) -> tuple[str, dict[str, list[str]], float]:
    category_hits: dict[str, list[str]] = {}
    weighted_scores: dict[str, float] = {}

    for category_name, rule in CATEGORY_RULES.items():
        hits = find_terms(rule["keywords"], text)
        category_hits[category_name] = hits
        weighted_scores[category_name] = float(len(hits))

    mineral_terms = set(category_hits["AI关键矿产供应链与地缘政治"])
    if mineral_terms & {"copper", "lithium", "rare earths", "critical minerals", "mine", "mining", "mineral"}:
        weighted_scores["AI关键矿产供应链与地缘政治"] += 2.0

    infra_terms = set(category_hits["AI算力基础设施地缘风险"])
    if infra_terms & {"data center", "compute", "cloud", "gpu", "power", "electricity", "grid"}:
        weighted_scores["AI算力基础设施地缘风险"] += 1.5

    primary_category = max(weighted_scores, key=weighted_scores.get)
    sorted_scores = sorted(weighted_scores.values(), reverse=True)
    margin = sorted_scores[0] - sorted_scores[1] if len(sorted_scores) > 1 else sorted_scores[0]
    hit_count = len(category_hits[primary_category])
    confidence = min(0.95, 0.62 + hit_count * 0.04 + margin * 0.03)

    return primary_category, category_hits, round(confidence, 2)


def choose_auxiliary_tags(text: str) -> tuple[list[str], dict[str, list[str]]]:
    tag_hits = {
        tag: find_terms(terms, text)
        for tag, terms in AUXILIARY_TAG_RULES.items()
    }
    ranked_tags = sorted(
        [tag for tag, hits in tag_hits.items() if hits],
        key=lambda tag: len(tag_hits[tag]),
        reverse=True,
    )
    return ranked_tags[:2], tag_hits


def truncate_for_prompt(text: str, max_chars: int = 5000) -> str:
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars].rstrip()}... [truncated for LLM prompt]"


def coerce_float(value: Any, default: float, lower: float, upper: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return round(max(lower, min(upper, parsed)), 2)


def normalize_category_signal_terms(value: Any, fallback: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return fallback
    primary_hits = value.get("primary_category_hits", fallback["primary_category_hits"])
    if not isinstance(primary_hits, dict):
        primary_hits = fallback["primary_category_hits"]
    normalized_primary_hits = {
        category: [
            str(term).strip()
            for term in (primary_hits.get(category, []) if isinstance(primary_hits, dict) else [])
            if str(term).strip()
        ]
        for category in CATEGORY_RULES
    }

    auxiliary_hits = value.get("auxiliary_tag_hits", fallback["auxiliary_tag_hits"])
    if not isinstance(auxiliary_hits, dict):
        auxiliary_hits = fallback["auxiliary_tag_hits"]
    normalized_auxiliary_hits = {
        tag: [
            str(term).strip()
            for term in (auxiliary_hits.get(tag, []) if isinstance(auxiliary_hits, dict) else [])
            if str(term).strip()
        ]
        for tag in AUXILIARY_TAG_RULES
    }
    return {
        "primary_category_hits": normalized_primary_hits,
        "auxiliary_tag_hits": normalized_auxiliary_hits,
    }


def build_classification_fallback(item: sqlite3.Row) -> dict[str, Any]:
    text = build_analysis_text(item)
    primary_category, category_hits, confidence = choose_primary_category(text)
    auxiliary_tags, tag_hits = choose_auxiliary_tags(text)

    category_terms = category_hits[primary_category]
    rationale = (
        f"Classified into {primary_category} because the item most strongly matches "
        f"these category signals: {', '.join(category_terms[:8]) or 'general project signals'}."
    )

    return {
        "news_id": item["id"],
        "primary_category": primary_category,
        "auxiliary_tags": auxiliary_tags,
        "confidence": confidence,
        "rationale": rationale,
        "category_signal_terms": {
            "primary_category_hits": category_hits,
            "auxiliary_tag_hits": tag_hits,
        },
    }


def classify_item(
    item: sqlite3.Row,
    llm_client: Any | None = None,
    require_online: bool = False,
) -> dict[str, Any]:
    fallback = build_classification_fallback(item)
    if llm_client is None:
        return {
            **fallback,
            "prompt_version": f"{PROMPT_VERSION_BASE}_offline_fallback",
            "model_provider": "offline_fallback",
        }

    system_prompt = (
        "You are a strict JSON API for classifying AI infrastructure geopolitical "
        "risk information. Return only one valid JSON object. Do not include "
        "markdown fences or explanatory prose outside JSON."
    )
    user_prompt = json.dumps(
        {
            "task": "Classify a retained high-relevance information item into exactly one main category and 0-2 auxiliary tags.",
            "allowed_primary_categories": CATEGORY_RULES,
            "allowed_auxiliary_tags": AUXILIARY_TAG_RULES,
            "instructions": [
                "Choose exactly one primary category from the allowed list.",
                "Use auxiliary tags only when directly supported by the item.",
                "Do not invent new categories or tags.",
                "Return confidence from 0 to 1.",
            ],
            "output_schema": {
                "primary_category": "AI算力基础设施地缘风险",
                "auxiliary_tags": ["AI芯片出口管制"],
                "confidence": 0.86,
                "category_signal_terms": {
                    "primary_category_hits": {
                        "AI算力基础设施地缘风险": ["data center"],
                        "AI关键矿产供应链与地缘政治": [],
                    },
                    "auxiliary_tag_hits": {
                        "AI芯片出口管制": ["export control"],
                        "区域冲突影响": [],
                        "全球AI治理": ["compliance"],
                    },
                },
                "rationale": "one concise explanation",
            },
            "item": {
                "news_id": item["id"],
                "title": item["title"],
                "source_name": item["source_name"],
                "source_type": item["source_type"],
                "published_at": item["published_at"],
                "summary": item["summary"],
                "content_excerpt": truncate_for_prompt(item["cleaned_content"]),
                "keywords": parse_json_list(item["keywords"]),
                "routing": {
                    "ai_signal_terms": parse_json_list(item["ai_signal_terms"]),
                    "geopolitical_signal_terms": parse_json_list(item["geopolitical_signal_terms"]),
                    "relevance_score": item["relevance_score"],
                    "rationale": item["rationale"],
                },
            },
        },
        ensure_ascii=False,
    )
    response = llm_client.complete_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        fallback_json=fallback,
        operation_name="stage_10_information_classification",
    )
    require_online_success(response, require_online, "stage_10_information_classification")

    data = response.json_data
    primary_category = str(data.get("primary_category") or fallback["primary_category"]).strip()
    if primary_category not in CATEGORY_RULES:
        primary_category = fallback["primary_category"]

    raw_tags = data.get("auxiliary_tags", fallback["auxiliary_tags"])
    if not isinstance(raw_tags, list):
        raw_tags = fallback["auxiliary_tags"]
    auxiliary_tags = []
    for tag in raw_tags:
        tag = str(tag).strip()
        if tag in AUXILIARY_TAG_RULES and tag not in auxiliary_tags:
            auxiliary_tags.append(tag)
    auxiliary_tags = auxiliary_tags[:2]

    confidence = coerce_float(data.get("confidence"), fallback["confidence"], 0.0, 1.0)
    rationale = str(data.get("rationale") or fallback["rationale"]).strip() or fallback["rationale"]
    category_signal_terms = normalize_category_signal_terms(
        data.get("category_signal_terms"),
        fallback["category_signal_terms"],
    )

    return {
        "news_id": item["id"],
        "primary_category": primary_category,
        "auxiliary_tags": auxiliary_tags,
        "confidence": confidence,
        "rationale": rationale,
        "category_signal_terms": category_signal_terms,
        "prompt_version": prompt_version_label(PROMPT_VERSION_BASE, response),
        "model_provider": model_provider_label(response),
    }


def select_routed_items(connection: sqlite3.Connection, rerun: bool) -> list[sqlite3.Row]:
    connection.row_factory = sqlite3.Row
    base_query = """
        SELECT
            news_items.*,
            relevance_routing_results.ai_signal_terms,
            relevance_routing_results.geopolitical_signal_terms,
            relevance_routing_results.rationale,
            relevance_routing_results.relevance_score
        FROM news_items
        INNER JOIN relevance_routing_results
            ON relevance_routing_results.news_id = news_items.id
        {classification_join}
        WHERE relevance_routing_results.decision = 'keep'
        {unclassified_filter}
        ORDER BY news_items.id
    """
    query = base_query.format(
        classification_join=(
            ""
            if rerun
            else "LEFT JOIN classification_results ON classification_results.news_id = news_items.id"
        ),
        unclassified_filter="" if rerun else "AND classification_results.news_id IS NULL",
    )
    cursor = connection.execute(query)
    return list(cursor.fetchall())


def upsert_classification_result(connection: sqlite3.Connection, result: dict[str, Any]) -> None:
    now = utc_now()
    connection.execute(
        """
        INSERT INTO classification_results (
            news_id, primary_category, auxiliary_tags, confidence, rationale,
            category_signal_terms, prompt_version, model_provider, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(news_id) DO UPDATE SET
            primary_category = excluded.primary_category,
            auxiliary_tags = excluded.auxiliary_tags,
            confidence = excluded.confidence,
            rationale = excluded.rationale,
            category_signal_terms = excluded.category_signal_terms,
            prompt_version = excluded.prompt_version,
            model_provider = excluded.model_provider,
            updated_at = excluded.updated_at
        """,
        (
            result["news_id"],
            result["primary_category"],
            json.dumps(result["auxiliary_tags"], ensure_ascii=False),
            result["confidence"],
            result["rationale"],
            json.dumps(result["category_signal_terms"], ensure_ascii=False),
            result["prompt_version"],
            result["model_provider"],
            now,
            now,
        ),
    )
    connection.execute(
        """
        UPDATE news_items
        SET status = 'classified', updated_at = ?
        WHERE id = ?
        """,
        (now, result["news_id"]),
    )


def record_run(connection: sqlite3.Connection, stats: ClassificationStats) -> None:
    connection.execute(
        """
        INSERT INTO classification_runs (
            run_id, started_at, finished_at, items_seen, items_classified,
            errors, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            stats.run_id,
            stats.started_at,
            stats.finished_at,
            stats.items_seen,
            stats.items_classified,
            stats.errors,
            stats.notes,
        ),
    )


def run_information_classification(
    db_path: Path,
    rerun: bool = False,
    llm_mode: str = "offline",
    max_items: int | None = None,
) -> tuple[ClassificationStats, Path]:
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    logger, log_path = setup_logger(run_id)
    stats = ClassificationStats(run_id=run_id, started_at=utc_now())

    logger.info("Starting Stage 3B information classification run: %s", run_id)
    logger.info("Primary categories: %s", list(CATEGORY_RULES.keys()))
    logger.info(
        "LLM provider placeholder: %s | enabled=%s",
        DEFAULT_LLM_CONFIG["provider"],
        DEFAULT_LLM_CONFIG["enabled"],
    )
    llm_client, require_online = build_llm_client(
        llm_mode,
        logger,
        model_env_var="CLASSIFICATION_LLM_MODEL",
    )
    logger.info(
        "Stage 10 classification LLM mode: %s | available=%s | require_online=%s",
        llm_mode,
        llm_client.is_available,
        require_online,
    )

    apply_schema(db_path, SQLITE_SCHEMA_PATH)

    with sqlite3.connect(db_path) as connection:
        items = select_routed_items(connection, rerun)
        if max_items is not None:
            items = items[:max_items]
            logger.info("Applied Stage 10 max item limit: %s", max_items)
        stats.items_seen = len(items)

        for item in items:
            try:
                result = classify_item(item, llm_client, require_online)
                upsert_classification_result(connection, result)
                stats.items_classified += 1
                logger.info(
                    "CLASSIFIED | %s | confidence=%.2f | %s",
                    result["primary_category"],
                    result["confidence"],
                    item["title"],
                )
            except Exception as exc:  # noqa: BLE001 - keep stage run resilient.
                stats.errors += 1
                logger.error("Failed to classify news_id=%s: %s", item["id"], exc)

        stats.finished_at = utc_now()
        stats.notes = (
            "Stage 10-enabled Stage 3B classification completed. Categories and "
            "auxiliary tags can be classified by LLM with deterministic fallback; "
            f"llm_mode={llm_mode}."
        )
        record_run(connection, stats)

    logger.info(
        "Completed classification. seen=%s classified=%s errors=%s",
        stats.items_seen,
        stats.items_classified,
        stats.errors,
    )
    return stats, log_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Stage 3B information classification.")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DATABASE_PATH,
        help="SQLite database path.",
    )
    parser.add_argument(
        "--rerun",
        action="store_true",
        help="Recompute classification for all kept routed items. This is the default for testing.",
    )
    parser.add_argument(
        "--only-new",
        action="store_true",
        help="Only classify kept routed items that do not already have classification results.",
    )
    parser.add_argument(
        "--llm-mode",
        choices=LLM_MODE_CHOICES,
        default="offline",
        help="LLM behavior for classification: offline, auto, or online. Default: offline.",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Optional maximum routed items to classify, useful for small online validation runs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rerun = args.rerun or not args.only_new
    stats, log_path = run_information_classification(args.db_path, rerun, args.llm_mode, args.max_items)
    print("\nStage 3B information classification completed")
    print(f"Run ID: {stats.run_id}")
    print(f"Database: {args.db_path}")
    print(f"Items seen: {stats.items_seen}")
    print(f"Classified: {stats.items_classified}")
    print(f"Errors: {stats.errors}")
    print(f"Log file: {log_path}")
    return 0 if stats.errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
