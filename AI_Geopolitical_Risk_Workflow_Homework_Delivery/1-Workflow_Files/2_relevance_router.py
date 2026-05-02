"""Stage 3A/10: dual-layer relevance routing.

The router keeps the MVP fully testable offline. It first applies an
engineering rule gate, then optionally asks the unified LLM client for rubric
scoring while preserving deterministic fallback and the same database contract.
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


PROMPT_VERSION_BASE = "relevance_routing_v2_stage10"
KEEP_THRESHOLD = 7.0

ROUTING_RULES = {
    "keywords": {
        "ai_infrastructure_supply_chain": [
            "ai",
            "artificial intelligence",
            "data center",
            "compute",
            "gpu",
            "accelerator",
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
        ],
        "geopolitical_cross_border_risk": [
            "export control",
            "sanctions",
            "conflict",
            "regulation",
            "compliance",
            "trade restriction",
            "tariff",
            "china",
            "us",
            "eu",
            "taiwan",
            "middle east",
            "cross-border",
            "resource nationalism",
            "shipping",
            "permitting",
            "business continuity",
        ],
    },
    "required_terms": {
        "must_match_groups": [
            "ai_infrastructure_supply_chain",
            "geopolitical_cross_border_risk",
        ],
        "minimum_hits_per_group": 1,
    },
    "exclude_terms": [
        "without discussing infrastructure",
        "without discussing infrastructure investment",
        "without direct ai infrastructure implications",
        "does not connect the event to ai data centers",
        "does not connect",
        "product adoption",
        "model capability",
        "creative workflows",
        "pure technical update",
    ],
}


@dataclass
class RoutingStats:
    run_id: str
    started_at: str
    finished_at: str = ""
    items_seen: int = 0
    items_routed: int = 0
    items_kept: int = 0
    items_filtered: int = 0
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
    keywords = " ".join(parse_json_list(item["keywords"]))
    return normalize_text(
        " ".join(
            [
                item["title"],
                item["summary"],
                item["cleaned_content"],
                keywords,
                item["source_type"],
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
    log_path = LOG_DIR / f"{run_id}_relevance_router.log"
    logger = logging.getLogger(f"relevance_router.{run_id}")
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


def weighted_presence_score(text: str, terms: list[str], maximum: float, step: float) -> float:
    hits = find_terms(terms, text)
    return min(maximum, len(hits) * step)


def score_relevance(
    item: sqlite3.Row,
    text: str,
    rule_passed: bool,
    ai_terms: list[str],
    geopolitical_terms: list[str],
    exclude_terms: list[str],
) -> tuple[float, dict[str, float], str]:
    """Offline stand-in for the planned LLM relevance scoring step."""
    if not rule_passed:
        missing_parts = []
        if not ai_terms:
            missing_parts.append("AI infrastructure or supply-chain signal")
        if not geopolitical_terms:
            missing_parts.append("geopolitical or cross-border risk signal")
        if exclude_terms:
            missing_parts.append(f"exclude signal: {', '.join(exclude_terms)}")
        rationale = "Filtered by rule gate: " + "; ".join(missing_parts)
        return 0.0, {
            "business_impact": 0.0,
            "evidence_support": 0.0,
            "audience_fit": 0.0,
            "core_chain_relevance": 0.0,
        }, rationale

    business_terms = [
        "investment",
        "investor",
        "cost",
        "deployment",
        "business continuity",
        "capacity",
        "procurement",
        "customer allocation",
        "backup",
        "resilience",
        "planning",
    ]
    evidence_terms = [
        "report",
        "brief",
        "note",
        "announcement",
        "analyst",
        "executive",
        "company",
        "published",
        "says",
    ]
    audience_terms = [
        "investor",
        "cloud",
        "operator",
        "data center",
        "enterprise",
        "supply chain",
        "strategy",
        "compliance",
        "risk",
    ]
    core_chain_terms = [
        "data center",
        "compute",
        "gpu",
        "chip",
        "semiconductor",
        "power",
        "electricity",
        "grid",
        "energy",
        "copper",
        "lithium",
        "rare earths",
        "critical minerals",
    ]

    source_type = item["source_type"]
    source_bonus = {
        "institution_report": 0.8,
        "company_announcement": 0.55,
        "media": 0.45,
        "policy_brief": 0.4,
        "company_blog": 0.25,
    }.get(source_type, 0.25)

    business_impact = min(
        4.0,
        1.0
        + weighted_presence_score(text, business_terms, 1.3, 0.3)
        + weighted_presence_score(text, ai_terms + geopolitical_terms, 1.2, 0.15)
        + source_bonus,
    )
    evidence_support = min(
        2.5,
        0.5
        + weighted_presence_score(text, evidence_terms, 1.1, 0.25)
        + (0.4 if item["published_at"] else 0.0)
        + source_bonus,
    )
    audience_fit = min(
        2.0,
        0.5
        + weighted_presence_score(text, audience_terms, 1.1, 0.22)
        + (0.4 if {"data center", "cloud", "supply chain"} & set(ai_terms) else 0.0),
    )
    core_chain_relevance = min(
        1.5,
        0.35 + weighted_presence_score(text, core_chain_terms, 1.15, 0.2),
    )

    breakdown = {
        "business_impact": round(business_impact, 2),
        "evidence_support": round(evidence_support, 2),
        "audience_fit": round(audience_fit, 2),
        "core_chain_relevance": round(core_chain_relevance, 2),
    }
    total = round(sum(breakdown.values()), 2)
    rationale = (
        "Kept for semantic scoring because it links AI infrastructure or supply-chain "
        "signals with geopolitical, policy, or cross-border risk signals."
    )
    return total, breakdown, rationale


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


def coerce_string_list(value: Any, fallback: list[str], limit: int = 12) -> list[str]:
    if not isinstance(value, list):
        return fallback[:limit]
    items = [str(item).strip() for item in value if str(item).strip()]
    return items[:limit] if items else fallback[:limit]


def normalize_scoring_breakdown(value: Any, fallback: dict[str, float]) -> dict[str, float]:
    if not isinstance(value, dict):
        return fallback
    return {
        "business_impact": coerce_float(value.get("business_impact"), fallback["business_impact"], 0.0, 4.0),
        "evidence_support": coerce_float(value.get("evidence_support"), fallback["evidence_support"], 0.0, 2.5),
        "audience_fit": coerce_float(value.get("audience_fit"), fallback["audience_fit"], 0.0, 2.0),
        "core_chain_relevance": coerce_float(
            value.get("core_chain_relevance"),
            fallback["core_chain_relevance"],
            0.0,
            1.5,
        ),
    }


def build_relevance_fallback(
    item: sqlite3.Row,
    text: str,
    rule_passed: bool,
    ai_terms: list[str],
    geopolitical_terms: list[str],
    exclude_terms: list[str],
) -> dict[str, Any]:
    relevance_score, scoring_breakdown, rationale = score_relevance(
        item,
        text,
        rule_passed,
        ai_terms,
        geopolitical_terms,
        exclude_terms,
    )
    decision = "keep" if rule_passed and relevance_score >= KEEP_THRESHOLD else "filter"
    if decision == "filter" and rule_passed:
        rationale = (
            f"Filtered after semantic scoring because score {relevance_score} is below "
            f"the keep threshold {KEEP_THRESHOLD}."
        )
    return {
        "rule_passed": rule_passed,
        "ai_signal_terms": ai_terms,
        "geopolitical_signal_terms": geopolitical_terms,
        "exclude_terms": exclude_terms,
        "relevance_score": relevance_score,
        "decision": decision,
        "rationale": rationale,
        "scoring_breakdown": scoring_breakdown,
    }


def route_item(
    item: sqlite3.Row,
    llm_client: Any | None = None,
    require_online: bool = False,
) -> dict[str, Any]:
    text = build_analysis_text(item)
    ai_terms = find_terms(ROUTING_RULES["keywords"]["ai_infrastructure_supply_chain"], text)
    geopolitical_terms = find_terms(ROUTING_RULES["keywords"]["geopolitical_cross_border_risk"], text)
    exclude_terms = find_terms(ROUTING_RULES["exclude_terms"], text)
    rule_passed = bool(ai_terms and geopolitical_terms and not exclude_terms)
    fallback = build_relevance_fallback(
        item,
        text,
        rule_passed,
        ai_terms,
        geopolitical_terms,
        exclude_terms,
    )

    if not rule_passed or llm_client is None:
        return {
            "news_id": item["id"],
            **fallback,
            "prompt_version": f"{PROMPT_VERSION_BASE}_offline_rule_gate",
            "model_provider": "offline_rule_gate",
        }

    system_prompt = (
        "You are a strict JSON API for AI infrastructure geopolitical risk "
        "relevance scoring. Return only one valid JSON object. Do not include "
        "markdown fences or explanatory prose outside JSON."
    )
    user_prompt = json.dumps(
        {
            "task": "Score this monitored item from 0 to 10 using the provided rubric.",
            "project_domain": "AI infrastructure geopolitical risk and supply-chain decision intelligence.",
            "target_audience": [
                "AI infrastructure investors",
                "data center investors and operators",
                "cloud, AI chip, supply-chain, strategy, and risk leaders",
            ],
            "rule_gate_result": {
                "rule_passed": rule_passed,
                "ai_signal_terms": ai_terms,
                "geopolitical_signal_terms": geopolitical_terms,
                "exclude_terms": exclude_terms,
            },
            "rubric": {
                "business_impact": "0-4 points: impact on AI infrastructure investment, data center deployment, supply-chain cost, or cross-border continuity",
                "evidence_support": "0-2.5 points: real event, data, report, announcement, or credible case",
                "audience_fit": "0-2 points: decision relevance for the target audience",
                "core_chain_relevance": "0-1.5 points: compute infrastructure, critical minerals, power, chips, or AI supply-chain links",
                "keep_threshold": KEEP_THRESHOLD,
            },
            "output_schema": {
                "rule_passed": True,
                "ai_signal_terms": ["data center"],
                "geopolitical_signal_terms": ["export control"],
                "exclude_terms": [],
                "relevance_score": 8.2,
                "decision": "keep or filter",
                "scoring_breakdown": {
                    "business_impact": 3.4,
                    "evidence_support": 2.0,
                    "audience_fit": 1.6,
                    "core_chain_relevance": 1.2,
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
            },
        },
        ensure_ascii=False,
    )
    response = llm_client.complete_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        fallback_json=fallback,
        operation_name="stage_10_relevance_scoring",
    )
    require_online_success(response, require_online, "stage_10_relevance_scoring")

    data = response.json_data
    scoring_breakdown = normalize_scoring_breakdown(data.get("scoring_breakdown"), fallback["scoring_breakdown"])
    relevance_score = coerce_float(
        data.get("relevance_score"),
        sum(scoring_breakdown.values()),
        0.0,
        10.0,
    )
    if abs(relevance_score - round(sum(scoring_breakdown.values()), 2)) > 1.0:
        relevance_score = round(sum(scoring_breakdown.values()), 2)
    decision = "keep" if rule_passed and relevance_score >= KEEP_THRESHOLD else "filter"
    rationale = str(data.get("rationale") or fallback["rationale"]).strip()
    if not rationale:
        rationale = fallback["rationale"]
    if decision == "filter" and rule_passed and relevance_score < KEEP_THRESHOLD:
        rationale = (
            f"Filtered after semantic scoring because score {relevance_score} is below "
            f"the keep threshold {KEEP_THRESHOLD}. {rationale}"
        )

    return {
        "news_id": item["id"],
        "rule_passed": rule_passed,
        "ai_signal_terms": coerce_string_list(data.get("ai_signal_terms"), ai_terms),
        "geopolitical_signal_terms": coerce_string_list(data.get("geopolitical_signal_terms"), geopolitical_terms),
        "exclude_terms": coerce_string_list(data.get("exclude_terms"), exclude_terms),
        "relevance_score": relevance_score,
        "decision": decision,
        "rationale": rationale,
        "scoring_breakdown": scoring_breakdown,
        "prompt_version": prompt_version_label(PROMPT_VERSION_BASE, response),
        "model_provider": model_provider_label(response),
    }


def select_news_items(connection: sqlite3.Connection, rerun: bool) -> list[sqlite3.Row]:
    connection.row_factory = sqlite3.Row
    if rerun:
        cursor = connection.execute("SELECT * FROM news_items ORDER BY id")
    else:
        cursor = connection.execute(
            """
            SELECT news_items.*
            FROM news_items
            LEFT JOIN relevance_routing_results
                ON relevance_routing_results.news_id = news_items.id
            WHERE relevance_routing_results.news_id IS NULL
            ORDER BY news_items.id
            """
        )
    return list(cursor.fetchall())


def upsert_routing_result(connection: sqlite3.Connection, result: dict[str, Any]) -> None:
    now = utc_now()
    connection.execute(
        """
        INSERT INTO relevance_routing_results (
            news_id, rule_passed, ai_signal_terms, geopolitical_signal_terms,
            exclude_terms, relevance_score, decision, rationale, scoring_breakdown,
            prompt_version, model_provider, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(news_id) DO UPDATE SET
            rule_passed = excluded.rule_passed,
            ai_signal_terms = excluded.ai_signal_terms,
            geopolitical_signal_terms = excluded.geopolitical_signal_terms,
            exclude_terms = excluded.exclude_terms,
            relevance_score = excluded.relevance_score,
            decision = excluded.decision,
            rationale = excluded.rationale,
            scoring_breakdown = excluded.scoring_breakdown,
            prompt_version = excluded.prompt_version,
            model_provider = excluded.model_provider,
            updated_at = excluded.updated_at
        """,
        (
            result["news_id"],
            int(result["rule_passed"]),
            json.dumps(result["ai_signal_terms"], ensure_ascii=False),
            json.dumps(result["geopolitical_signal_terms"], ensure_ascii=False),
            json.dumps(result["exclude_terms"], ensure_ascii=False),
            result["relevance_score"],
            result["decision"],
            result["rationale"],
            json.dumps(result["scoring_breakdown"], ensure_ascii=False),
            result["prompt_version"],
            result["model_provider"],
            now,
            now,
        ),
    )
    status = "routed_relevant" if result["decision"] == "keep" else "routed_filtered"
    connection.execute(
        """
        UPDATE news_items
        SET status = ?, updated_at = ?
        WHERE id = ? AND status != 'classified'
        """,
        (status, now, result["news_id"]),
    )


def record_run(connection: sqlite3.Connection, stats: RoutingStats) -> None:
    connection.execute(
        """
        INSERT INTO routing_runs (
            run_id, started_at, finished_at, items_seen, items_routed,
            items_kept, items_filtered, errors, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            stats.run_id,
            stats.started_at,
            stats.finished_at,
            stats.items_seen,
            stats.items_routed,
            stats.items_kept,
            stats.items_filtered,
            stats.errors,
            stats.notes,
        ),
    )


def run_relevance_router(
    db_path: Path,
    rerun: bool = False,
    llm_mode: str = "offline",
    max_items: int | None = None,
) -> tuple[RoutingStats, Path]:
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    logger, log_path = setup_logger(run_id)
    stats = RoutingStats(run_id=run_id, started_at=utc_now())

    logger.info("Starting Stage 3A relevance routing run: %s", run_id)
    logger.info(
        "Rule config loaded with groups=%s exclude_terms=%s",
        list(ROUTING_RULES["keywords"].keys()),
        len(ROUTING_RULES["exclude_terms"]),
    )
    logger.info(
        "LLM provider placeholder: %s | enabled=%s",
        DEFAULT_LLM_CONFIG["provider"],
        DEFAULT_LLM_CONFIG["enabled"],
    )
    llm_client, require_online = build_llm_client(llm_mode, logger)
    logger.info(
        "Stage 10 relevance LLM mode: %s | available=%s | require_online=%s",
        llm_mode,
        llm_client.is_available,
        require_online,
    )

    apply_schema(db_path, SQLITE_SCHEMA_PATH)

    with sqlite3.connect(db_path) as connection:
        items = select_news_items(connection, rerun)
        if max_items is not None:
            items = items[:max_items]
            logger.info("Applied Stage 10 max item limit: %s", max_items)
        stats.items_seen = len(items)

        for item in items:
            try:
                result = route_item(item, llm_client, require_online)
                upsert_routing_result(connection, result)
                stats.items_routed += 1
                if result["decision"] == "keep":
                    stats.items_kept += 1
                else:
                    stats.items_filtered += 1
                logger.info(
                    "%s | score=%.2f | %s",
                    result["decision"].upper(),
                    result["relevance_score"],
                    item["title"],
                )
            except Exception as exc:  # noqa: BLE001 - keep stage run resilient.
                stats.errors += 1
                logger.error("Failed to route news_id=%s: %s", item["id"], exc)

        stats.finished_at = utc_now()
        stats.notes = (
            "Stage 10-enabled Stage 3A router completed. Rule gate uses keywords, "
            "required_terms, and exclude_terms; LLM rubric scoring is controlled by "
            f"llm_mode={llm_mode} with deterministic fallback."
        )
        record_run(connection, stats)

    logger.info(
        "Completed routing. seen=%s routed=%s kept=%s filtered=%s errors=%s",
        stats.items_seen,
        stats.items_routed,
        stats.items_kept,
        stats.items_filtered,
        stats.errors,
    )
    return stats, log_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Stage 3A relevance routing.")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DATABASE_PATH,
        help="SQLite database path.",
    )
    parser.add_argument(
        "--rerun",
        action="store_true",
        help="Recompute routing for all news items. This is the default for testing.",
    )
    parser.add_argument(
        "--only-new",
        action="store_true",
        help="Only route news items that do not already have routing results.",
    )
    parser.add_argument(
        "--llm-mode",
        choices=LLM_MODE_CHOICES,
        default="offline",
        help="LLM behavior for relevance scoring: offline, auto, or online. Default: offline.",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Optional maximum news items to route, useful for small online validation runs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rerun = args.rerun or not args.only_new
    stats, log_path = run_relevance_router(args.db_path, rerun, args.llm_mode, args.max_items)
    print("\nStage 3A relevance routing completed")
    print(f"Run ID: {stats.run_id}")
    print(f"Database: {args.db_path}")
    print(f"Items seen: {stats.items_seen}")
    print(f"Routed: {stats.items_routed}")
    print(f"Kept: {stats.items_kept}")
    print(f"Filtered: {stats.items_filtered}")
    print(f"Errors: {stats.errors}")
    print(f"Log file: {log_path}")


if __name__ == "__main__":
    main()
