"""Stage 12: daily workflow run and human review queue.

This stage wraps the existing end-to-end workflow, writes a daily handoff
package under daily_outputs/YYYY-MM-DD/, and records a review queue in SQLite.
It deliberately stops before any external publishing: every generated post is
marked pending human review.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api_config import (
    DAILY_OUTPUT_DIR,
    DATABASE_PATH,
    LOG_DIR,
    SQLITE_SCHEMA_PATH,
)
from llm_stage_utils import LLM_MODE_CHOICES
from lineage_utils import (
    apply_schema_with_migrations,
    classify_lineage_mode,
)


WORKFLOW_DIR = Path(__file__).resolve().parent
MAIN_WORKFLOW_PATH = WORKFLOW_DIR / "0_main_workflow.py"
IMAGE_MODE_CHOICES = ("offline", "auto", "online")
STAGE12_PROMPT_VERSION = "daily_review_queue_v2_stage13_lineage"


@dataclass
class DailyRunStats:
    run_id: str
    run_date: str
    started_at: str
    finished_at: str = ""
    stage2_input_mode: str = "rss"
    llm_mode: str = "offline"
    image_mode: str = "offline"
    lineage_mode: str = "legacy"
    no_candidate_reason: str = ""
    workflow_run_id: str = ""
    workflow_return_code: int = 0
    workflow_log_path: str = ""
    daily_log_path: str = ""
    output_dir: str = ""
    review_queue_path: str = ""
    manifest_path: str = ""
    items_seen: int = 0
    items_inserted: int = 0
    items_kept: int = 0
    items_classified: int = 0
    candidate_posts: int = 0
    images_generated: int = 0
    fallback_used: int = 0
    review_items: int = 0
    errors: int = 0
    notes: str = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def local_date_slug() -> str:
    return datetime.now().date().isoformat()


def tail_text(text: str, max_lines: int = 28) -> str:
    lines = text.strip().splitlines()
    return "\n".join(lines[-max_lines:]) if lines else ""


def safe_slug(value: str) -> str:
    category_slugs = {
        "AI算力基础设施地缘风险": "category_1_ai_infrastructure_risk",
        "AI关键矿产供应链与地缘政治": "category_2_ai_critical_minerals_supply_chain",
    }
    if value in category_slugs:
        return category_slugs[value]
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.lower()).strip("_")
    return cleaned or "candidate"


def parse_json_list(raw_value: str) -> list[str]:
    try:
        value = json.loads(raw_value or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def parse_json_any(raw_value: str, fallback: Any) -> Any:
    try:
        return json.loads(raw_value or "")
    except json.JSONDecodeError:
        return fallback


def apply_schema(db_path: Path) -> None:
    apply_schema_with_migrations(db_path, SQLITE_SCHEMA_PATH)


def setup_logger(run_id: str) -> tuple[logging.Logger, Path]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{run_id}_daily_review.log"
    logger = logging.getLogger(f"daily_review.{run_id}")
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


def build_main_workflow_command(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        str(MAIN_WORKFLOW_PATH),
        "--db-path",
        str(args.db_path),
        "--stage2-input-mode",
        args.stage2_input_mode,
        "--llm-mode",
        args.llm_mode,
        "--include-stage11",
        "--image-mode",
        args.image_mode,
        "--daily-run-id",
        getattr(args, "daily_run_id", ""),
    ]
    if args.rss_limit is not None:
        command.extend(["--rss-limit", str(args.rss_limit)])
    if args.stage10_max_items is not None:
        command.extend(["--stage10-max-items", str(args.stage10_max_items)])
    if args.stage11_max_items is not None:
        command.extend(["--stage11-max-items", str(args.stage11_max_items)])
    if args.continue_on_error:
        command.append("--continue-on-error")
    return command


def parse_workflow_stdout(stdout: str) -> dict[str, str]:
    run_match = re.search(r"^Run ID:\s*(\S+)\s*$", stdout, flags=re.MULTILINE)
    log_match = re.search(r"^Master log file:\s*(.+?)\s*$", stdout, flags=re.MULTILINE)
    return {
        "workflow_run_id": run_match.group(1) if run_match else "",
        "workflow_log_path": log_match.group(1) if log_match else "",
    }


def run_main_workflow(args: argparse.Namespace, logger: logging.Logger) -> subprocess.CompletedProcess[str]:
    command = build_main_workflow_command(args)
    logger.info("Starting Stage 12 wrapped workflow command: %s", " ".join(command))
    completed = subprocess.run(
        command,
        cwd=WORKFLOW_DIR,
        text=True,
        capture_output=True,
        timeout=args.workflow_timeout_seconds,
        check=False,
    )
    if completed.stdout.strip():
        logger.info("Wrapped workflow stdout:\n%s", completed.stdout.strip())
    if completed.stderr.strip():
        logger.info("Wrapped workflow stderr:\n%s", completed.stderr.strip())
    logger.info("Wrapped workflow return code: %s", completed.returncode)
    return completed


def latest_run(
    connection: sqlite3.Connection,
    table_name: str,
    workflow_run_id: str = "",
    daily_run_id: str = "",
) -> dict[str, Any]:
    filters = []
    params: list[Any] = []
    if workflow_run_id:
        filters.append("workflow_run_id = ?")
        params.append(workflow_run_id)
    if daily_run_id:
        filters.append("daily_run_id = ?")
        params.append(daily_run_id)
    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""
    cursor = connection.execute(
        f"SELECT * FROM {table_name} {where_sql} ORDER BY id DESC LIMIT 1",
        params,
    )
    row = cursor.fetchone()
    return dict(row) if row is not None else {}


def int_from(mapping: dict[str, Any], key: str) -> int:
    value = mapping.get(key, 0)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def collect_latest_metrics(
    connection: sqlite3.Connection,
    workflow_run_id: str = "",
    daily_run_id: str = "",
) -> dict[str, Any]:
    connection.row_factory = sqlite3.Row
    ingestion = latest_run(connection, "ingestion_runs", workflow_run_id, daily_run_id)
    routing = latest_run(connection, "routing_runs", workflow_run_id, daily_run_id)
    classification = latest_run(connection, "classification_runs", workflow_run_id, daily_run_id)
    content = latest_run(connection, "linkedin_content_runs", workflow_run_id, daily_run_id)
    images = latest_run(connection, "image_generation_runs", workflow_run_id, daily_run_id)
    return {
        "latest_runs": {
            "ingestion": ingestion,
            "routing": routing,
            "classification": classification,
            "content": content,
            "images": images,
        },
        "items_seen": int_from(ingestion, "items_seen"),
        "items_inserted": int_from(ingestion, "items_inserted"),
        "items_kept": int_from(routing, "items_kept"),
        "items_classified": int_from(classification, "items_classified"),
        "candidate_posts": int_from(content, "posts_generated"),
        "images_generated": int_from(images, "images_generated"),
        "fallback_used": int_from(images, "fallback_used"),
        "lineage_mode": (
            content.get("lineage_mode")
            or images.get("lineage_mode")
            or "fallback"
        ),
        "stage_errors": (
            int_from(ingestion, "errors")
            + int_from(routing, "errors")
            + int_from(classification, "errors")
            + int_from(content, "errors")
            + int_from(images, "errors")
        ),
    }


def select_review_candidates(
    connection: sqlite3.Connection,
    workflow_run_id: str = "",
    daily_run_id: str = "",
) -> list[sqlite3.Row]:
    connection.row_factory = sqlite3.Row
    filters = []
    params: list[Any] = []
    image_join_filters = []
    if workflow_run_id:
        filters.append("linkedin_content_results.workflow_run_id = ?")
        params.append(workflow_run_id)
        image_join_filters.append("image_generation_results.workflow_run_id = linkedin_content_results.workflow_run_id")
    if daily_run_id:
        filters.append("linkedin_content_results.daily_run_id = ?")
        params.append(daily_run_id)
        image_join_filters.append("image_generation_results.daily_run_id = linkedin_content_results.daily_run_id")
    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""
    image_join_sql = ""
    if image_join_filters:
        image_join_sql = " AND " + " AND ".join(image_join_filters)
    cursor = connection.execute(
        f"""
        SELECT
            linkedin_content_results.id AS source_content_id,
            linkedin_content_results.workflow_run_id,
            linkedin_content_results.daily_run_id,
            linkedin_content_results.lineage_mode,
            linkedin_content_results.primary_category,
            linkedin_content_results.target_audience,
            linkedin_content_results.tone_positioning,
            linkedin_content_results.source_news_ids,
            linkedin_content_results.source_titles,
            linkedin_content_results.evidence_basis,
            linkedin_content_results.linkedin_post,
            linkedin_content_results.visual_prompt,
            linkedin_content_results.output_path,
            linkedin_content_results.prompt_version,
            linkedin_content_results.model_provider,
            linkedin_content_results.updated_at,
            image_generation_results.image_path,
            image_generation_results.image_mime_type,
            image_generation_results.archive_dir,
            image_generation_results.archive_post_path,
            image_generation_results.status AS image_status,
            image_generation_results.image_provider,
            image_generation_results.image_model
        FROM linkedin_content_results
        LEFT JOIN image_generation_results
            ON image_generation_results.primary_category = linkedin_content_results.primary_category
            {image_join_sql}
        {where_sql}
        ORDER BY linkedin_content_results.primary_category ASC
        """,
        params,
    )
    return list(cursor.fetchall())


def relative_markdown_path(target: Path, base_file: Path) -> str:
    try:
        return target.resolve().relative_to(base_file.parent.resolve()).as_posix()
    except ValueError:
        return os.path.relpath(target, start=base_file.parent).replace(os.sep, "/")


def copy_candidate_image(row: sqlite3.Row, assets_dir: Path, logger: logging.Logger) -> Path | None:
    raw_path = row["image_path"]
    if not raw_path:
        return None
    source = Path(raw_path)
    if not source.exists():
        logger.warning("Candidate image path does not exist: %s", source)
        return None
    assets_dir.mkdir(parents=True, exist_ok=True)
    target = assets_dir / source.name
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return target


def render_evidence_table(evidence_basis: Any) -> str:
    if not isinstance(evidence_basis, list) or not evidence_basis:
        return "_No structured evidence basis was available._"

    lines = [
        "| News ID | Source mode | Source | Published | Relevance | Title |",
        "|---:|---|---|---|---:|---|",
    ]
    for item in evidence_basis:
        if not isinstance(item, dict):
            continue
        lines.append(
            "| {news_id} | {source_mode} | {source_name} | {published_at} | {relevance_score} | {title} |".format(
                news_id=item.get("news_id", ""),
                source_mode=str(item.get("source_mode", "legacy")).replace("|", "/"),
                source_name=str(item.get("source_name", item.get("source_type", ""))).replace("|", "/"),
                published_at=str(item.get("published_at", "")).replace("|", "/"),
                relevance_score=item.get("relevance_score", ""),
                title=str(item.get("title", "")).replace("|", "/"),
            )
        )
    return "\n".join(lines)


def render_candidate_markdown(
    row: sqlite3.Row,
    *,
    daily_run_id: str,
    run_date: str,
    candidate_path: Path,
    copied_image_path: Path | None,
) -> str:
    evidence_basis = parse_json_any(row["evidence_basis"], [])
    source_titles = parse_json_list(row["source_titles"])
    source_news_ids = parse_json_list(row["source_news_ids"])
    if copied_image_path:
        image_section = "\n".join(
            [
                f"![Candidate visual]({relative_markdown_path(copied_image_path, candidate_path)})",
                "",
                f"- Copied image file: `{copied_image_path}`",
                f"- Source image file: `{row['image_path']}`",
                f"- Image status: `{row['image_status'] or 'not_available'}`",
                f"- Image provider/model: `{row['image_provider'] or 'not_available'}` / `{row['image_model'] or 'not_available'}`",
            ]
        )
    else:
        image_section = "_No image file was available for this candidate._"

    return "\n".join(
        [
            f"# Daily Candidate Review: {row['primary_category']}",
            "",
            "> Stage 12 output. This is a candidate package for human review only.",
            "> Do not publish externally until the checklist below is completed by a human reviewer.",
            "",
            "## Review Metadata",
            "",
            f"- Daily run ID: `{daily_run_id}`",
            f"- Wrapped workflow run ID: `{row['workflow_run_id'] or ''}`",
            f"- Run date: `{run_date}`",
            f"- Review status: `pending_review`",
            f"- Lineage mode: `{row['lineage_mode'] or 'legacy'}`",
            f"- Primary category: {row['primary_category']}",
            f"- Target audience: {row['target_audience']}",
            f"- Tone and positioning: {row['tone_positioning']}",
            f"- Source content ID: `{row['source_content_id']}`",
            f"- Source news IDs: {', '.join(source_news_ids)}",
            f"- Source titles: {'; '.join(source_titles)}",
            f"- Prompt version: `{row['prompt_version']}`",
            f"- Model provider: `{row['model_provider']}`",
            f"- Original post path: `{row['output_path']}`",
            f"- Stage 11 archive: `{row['archive_dir'] or ''}`",
            "",
            "## Human Review Checklist",
            "",
            "- [ ] Facts and source titles match the evidence table.",
            "- [ ] No unsupported numbers, quotes, claims, or source names were introduced.",
            "- [ ] Tone is suitable for AI infrastructure investors and enterprise strategy/supply-chain leaders.",
            "- [ ] Business implications are specific enough for decision review.",
            "- [ ] Image is professional, relevant, and free of logos or text overlays.",
            "- [ ] Final decision recorded as approved, revise, or reject before external posting.",
            "",
            "## Source Evidence",
            "",
            render_evidence_table(evidence_basis),
            "",
            "## Candidate LinkedIn Post",
            "",
            row["linkedin_post"],
            "",
            "## Candidate Visual",
            "",
            image_section,
            "",
            "## Image Generation Prompt",
            "",
            row["visual_prompt"],
            "",
        ]
    )


def render_review_queue(
    *,
    stats: DailyRunStats,
    candidate_records: list[dict[str, Any]],
    workflow_stdout_tail: str,
    workflow_stderr_tail: str,
) -> str:
    candidate_lines = [
        "| Review | Category | Lineage | Status | Image | Candidate file |",
        "|---|---|---|---|---|---|",
    ]
    for item in candidate_records:
        candidate_path = Path(item["candidate_post_path"])
        output_dir = Path(stats.output_dir)
        candidate_link = candidate_path.resolve().relative_to(output_dir.resolve()).as_posix()
        image_status = item.get("image_status") or "not_available"
        candidate_lines.append(
            f"| Manual required | {item['primary_category']} | {item.get('lineage_mode', 'legacy')} | pending_review | {image_status} | [{candidate_path.name}]({candidate_link}) |"
        )
    if not candidate_records:
        candidate_lines.append(
            "| No candidate generated today | all categories | "
            f"{stats.lineage_mode} | no_candidate_generated_today | not_available | {stats.no_candidate_reason or 'No current-run classified items reached content generation.'} |"
        )

    return "\n".join(
        [
            f"# Stage 12 Daily Review Queue - {stats.run_date}",
            "",
            "This folder contains candidate LinkedIn content generated by the workflow.",
            "Nothing in this package has been published externally; every item requires human review first.",
            "",
            "## Daily Metrics",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| News items seen | {stats.items_seen} |",
            f"| News items inserted | {stats.items_inserted} |",
            f"| Items kept after routing | {stats.items_kept} |",
            f"| Items classified | {stats.items_classified} |",
            f"| Candidate posts generated | {stats.candidate_posts} |",
            f"| Images generated | {stats.images_generated} |",
            f"| Image fallback used | {stats.fallback_used} |",
            f"| Review queue items | {stats.review_items} |",
            f"| Errors | {stats.errors} |",
            "",
            "## Run Metadata",
            "",
            f"- Stage 12 daily run ID: `{stats.run_id}`",
            f"- Wrapped workflow run ID: `{stats.workflow_run_id}`",
            f"- Stage 2 input mode: `{stats.stage2_input_mode}`",
            f"- Lineage mode: `{stats.lineage_mode}`",
            f"- No-candidate reason: `{stats.no_candidate_reason or 'not_applicable'}`",
            f"- LLM mode: `{stats.llm_mode}`",
            f"- Image mode: `{stats.image_mode}`",
            f"- Workflow return code: `{stats.workflow_return_code}`",
            f"- Workflow log: `{stats.workflow_log_path}`",
            f"- Daily review log: `{stats.daily_log_path}`",
            "",
            "## Candidate Review Items",
            "",
            "\n".join(candidate_lines),
            "",
            "## Failure Review Pointers",
            "",
            "- RSS/source failures are recorded in the Stage 2 section of the wrapped workflow log.",
            "- Prompt/LLM failures are recorded in the relevant Stage 2/3/5 logs and surfaced through fallback metadata.",
            "- Image generation failures are recorded in Stage 11 logs; auto mode may fallback to a deterministic SVG.",
            "",
            "## Wrapped Workflow Output Tail",
            "",
            "```text",
            workflow_stdout_tail or "(no stdout)",
            "```",
            "",
            "## Wrapped Workflow Error Tail",
            "",
            "```text",
            workflow_stderr_tail or "(no stderr)",
            "```",
            "",
        ]
    )


def write_daily_outputs(
    *,
    stats: DailyRunStats,
    candidates: list[sqlite3.Row],
    output_root: Path,
    workflow_stdout_tail: str,
    workflow_stderr_tail: str,
    logger: logging.Logger,
) -> list[dict[str, Any]]:
    output_dir = output_root / stats.run_date
    candidates_dir = output_dir / "candidates"
    assets_dir = output_dir / "assets"
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    candidate_records: list[dict[str, Any]] = []
    for row in candidates:
        slug = safe_slug(row["primary_category"])
        candidate_path = candidates_dir / f"{slug}_candidate.md"
        copied_image_path = copy_candidate_image(row, assets_dir, logger)
        evidence_basis = parse_json_any(row["evidence_basis"], [])
        source_modes = [
            str(item.get("source_mode", row["lineage_mode"] or "legacy"))
            for item in evidence_basis
            if isinstance(item, dict)
        ]
        source_mode_counts = {
            mode: source_modes.count(mode)
            for mode in sorted(set(source_modes))
        }
        candidate_path.write_text(
            render_candidate_markdown(
                row,
                daily_run_id=stats.run_id,
                run_date=stats.run_date,
                candidate_path=candidate_path,
                copied_image_path=copied_image_path,
            ),
            encoding="utf-8",
        )
        candidate_records.append(
            {
                "daily_run_id": stats.run_id,
                "run_date": stats.run_date,
                "workflow_run_id": row["workflow_run_id"] or stats.workflow_run_id,
                "primary_category": row["primary_category"],
                "lineage_mode": row["lineage_mode"] or classify_lineage_mode(source_modes),
                "source_mode_counts": source_mode_counts,
                "source_content_id": int(row["source_content_id"]),
                "source_news_ids": parse_json_list(row["source_news_ids"]),
                "source_titles": parse_json_list(row["source_titles"]),
                "candidate_post_path": str(candidate_path),
                "image_path": str(copied_image_path or row["image_path"] or ""),
                "archive_dir": row["archive_dir"] or "",
                "review_status": "pending_review",
                "review_priority": "P1",
                "prompt_version": row["prompt_version"],
                "model_provider": row["model_provider"],
                "image_status": row["image_status"] or "",
            }
        )

    stats.output_dir = str(output_dir)
    stats.review_queue_path = str(output_dir / "review_queue.md")
    stats.manifest_path = str(output_dir / "manifest.json")
    stats.review_items = len(candidate_records)
    if candidate_records:
        stats.lineage_mode = classify_lineage_mode([item["lineage_mode"] for item in candidate_records])
    else:
        stats.lineage_mode = "fallback"
        stats.no_candidate_reason = stats.no_candidate_reason or "no_candidate_generated_today"

    review_queue = render_review_queue(
        stats=stats,
        candidate_records=candidate_records,
        workflow_stdout_tail=workflow_stdout_tail,
        workflow_stderr_tail=workflow_stderr_tail,
    )
    Path(stats.review_queue_path).write_text(review_queue, encoding="utf-8")

    csv_path = output_dir / "review_queue.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "daily_run_id",
                "run_date",
                "workflow_run_id",
                "primary_category",
                "lineage_mode",
                "source_mode_counts",
                "source_content_id",
                "source_news_ids",
                "source_titles",
                "candidate_post_path",
                "image_path",
                "archive_dir",
                "review_status",
                "review_priority",
                "prompt_version",
                "model_provider",
                "image_status",
            ],
        )
        writer.writeheader()
        for item in candidate_records:
            writer.writerow({
                **item,
                "source_mode_counts": json.dumps(item["source_mode_counts"], ensure_ascii=False),
                "source_news_ids": json.dumps(item["source_news_ids"], ensure_ascii=False),
                "source_titles": json.dumps(item["source_titles"], ensure_ascii=False),
            })

    manifest = {
        "stage": "stage_12_daily_run_and_human_review",
        "prompt_version": STAGE12_PROMPT_VERSION,
        "stats": asdict(stats),
        "candidate_records": candidate_records,
        "artifacts": {
            "review_queue": stats.review_queue_path,
            "review_queue_csv": str(csv_path),
            "candidates_dir": str(candidates_dir),
            "assets_dir": str(assets_dir),
        },
        "lineage_policy": {
            "candidate_sources_must_match_daily_run": True,
            "no_candidate_success_state": "no_candidate_generated_today",
            "allowed_source_modes": [
                "rss_current_run",
                "local_sample_baseline",
                "fallback",
            ],
        },
        "publishing_policy": "manual_review_required_no_auto_publish",
    }
    Path(stats.manifest_path).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return candidate_records


def record_daily_run(connection: sqlite3.Connection, stats: DailyRunStats) -> None:
    connection.execute(
        """
        INSERT INTO daily_workflow_runs (
            run_id, run_date, started_at, finished_at, stage2_input_mode,
            llm_mode, image_mode, lineage_mode, no_candidate_reason,
            workflow_run_id, workflow_return_code, workflow_log_path,
            daily_log_path, output_dir, review_queue_path, manifest_path,
            items_seen, items_inserted, items_kept, items_classified,
            candidate_posts, images_generated, fallback_used, review_items,
            errors, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            stats.run_id,
            stats.run_date,
            stats.started_at,
            stats.finished_at,
            stats.stage2_input_mode,
            stats.llm_mode,
            stats.image_mode,
            stats.lineage_mode,
            stats.no_candidate_reason,
            stats.workflow_run_id,
            stats.workflow_return_code,
            stats.workflow_log_path,
            stats.daily_log_path,
            stats.output_dir,
            stats.review_queue_path,
            stats.manifest_path,
            stats.items_seen,
            stats.items_inserted,
            stats.items_kept,
            stats.items_classified,
            stats.candidate_posts,
            stats.images_generated,
            stats.fallback_used,
            stats.review_items,
            stats.errors,
            stats.notes,
        ),
    )


def upsert_review_items(connection: sqlite3.Connection, candidate_records: list[dict[str, Any]]) -> None:
    now = utc_now()
    for item in candidate_records:
        connection.execute(
            """
            INSERT INTO review_queue_items (
                daily_run_id, run_date, primary_category, lineage_mode,
                source_content_id, source_news_ids, source_titles,
                candidate_post_path, image_path, archive_dir, review_status,
                review_priority, reviewer_notes, prompt_version, model_provider,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(daily_run_id, primary_category) DO UPDATE SET
                lineage_mode = excluded.lineage_mode,
                source_content_id = excluded.source_content_id,
                source_news_ids = excluded.source_news_ids,
                source_titles = excluded.source_titles,
                candidate_post_path = excluded.candidate_post_path,
                image_path = excluded.image_path,
                archive_dir = excluded.archive_dir,
                review_priority = excluded.review_priority,
                prompt_version = excluded.prompt_version,
                model_provider = excluded.model_provider,
                updated_at = excluded.updated_at
            """,
            (
                item["daily_run_id"],
                item["run_date"],
                item["primary_category"],
                item["lineage_mode"],
                item["source_content_id"],
                json.dumps(item["source_news_ids"], ensure_ascii=False),
                json.dumps(item["source_titles"], ensure_ascii=False),
                item["candidate_post_path"],
                item["image_path"],
                item["archive_dir"],
                item["review_status"],
                item["review_priority"],
                "",
                item["prompt_version"],
                item["model_provider"],
                now,
                now,
            ),
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Stage 12 daily workflow and human review queue.")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DATABASE_PATH,
        help="SQLite database path shared by all workflow stages.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DAILY_OUTPUT_DIR,
        help="Root directory for daily_outputs/YYYY-MM-DD review packages.",
    )
    parser.add_argument(
        "--run-date",
        default=local_date_slug(),
        help="Daily output date folder in YYYY-MM-DD format. Defaults to today's local date.",
    )
    parser.add_argument(
        "--stage2-input-mode",
        choices=["local_sample", "rss", "all"],
        default="rss",
        help="Input mode for the wrapped daily run. Default: rss.",
    )
    parser.add_argument(
        "--rss-limit",
        type=int,
        default=2,
        help="Optional maximum RSS items per source for daily runs. Default: 2.",
    )
    parser.add_argument(
        "--llm-mode",
        choices=LLM_MODE_CHOICES,
        default="offline",
        help="LLM behavior for text stages: offline, auto, or online. Default: offline.",
    )
    parser.add_argument(
        "--image-mode",
        choices=IMAGE_MODE_CHOICES,
        default="offline",
        help="Image behavior for Stage 11: offline, auto, or online. Default: offline.",
    )
    parser.add_argument(
        "--stage10-max-items",
        type=int,
        default=None,
        help="Optional small-batch limit for LLM validation across Stage 2/3/5.",
    )
    parser.add_argument(
        "--stage11-max-items",
        type=int,
        default=None,
        help="Optional limit for Stage 11 image/archive processing.",
    )
    parser.add_argument(
        "--skip-workflow",
        action="store_true",
        help="Only regenerate the review package from current database results.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Pass through to the wrapped workflow so later stages still run after a stage failure.",
    )
    parser.add_argument(
        "--workflow-timeout-seconds",
        type=int,
        default=900,
        help="Timeout for the wrapped workflow subprocess.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_id = f"daily_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    args.daily_run_id = run_id
    logger, daily_log_path = setup_logger(run_id)
    stats = DailyRunStats(
        run_id=run_id,
        run_date=args.run_date,
        started_at=utc_now(),
        stage2_input_mode=args.stage2_input_mode,
        llm_mode=args.llm_mode,
        image_mode=args.image_mode,
        daily_log_path=str(daily_log_path),
    )

    logger.info("Starting Stage 12 daily review run: %s", run_id)
    logger.info("Database path: %s", args.db_path)
    logger.info("Output root: %s", args.output_root)
    apply_schema(args.db_path)

    workflow_stdout = ""
    workflow_stderr = ""
    if args.skip_workflow:
        logger.info("Skipping wrapped workflow; generating review package from current database state.")
        completed_return_code = 0
    else:
        try:
            completed = run_main_workflow(args, logger)
            completed_return_code = completed.returncode
            workflow_stdout = completed.stdout
            workflow_stderr = completed.stderr
            parsed = parse_workflow_stdout(completed.stdout)
            stats.workflow_run_id = parsed["workflow_run_id"]
            stats.workflow_log_path = parsed["workflow_log_path"]
        except subprocess.TimeoutExpired as exc:
            completed_return_code = 124
            workflow_stdout = exc.stdout or ""
            workflow_stderr = exc.stderr or ""
            logger.error("Wrapped workflow timed out after %s seconds.", args.workflow_timeout_seconds)

    stats.workflow_return_code = completed_return_code

    with sqlite3.connect(args.db_path) as connection:
        connection.row_factory = sqlite3.Row
        metrics = collect_latest_metrics(connection, stats.workflow_run_id, stats.run_id)
        candidates = select_review_candidates(connection, stats.workflow_run_id, stats.run_id)

        stats.items_seen = int(metrics["items_seen"])
        stats.items_inserted = int(metrics["items_inserted"])
        stats.items_kept = int(metrics["items_kept"])
        stats.items_classified = int(metrics["items_classified"])
        stats.candidate_posts = int(metrics["candidate_posts"])
        stats.images_generated = int(metrics["images_generated"])
        stats.fallback_used = int(metrics["fallback_used"])
        stats.lineage_mode = str(metrics.get("lineage_mode") or "fallback")
        stats.errors = int(metrics["stage_errors"]) + (0 if stats.workflow_return_code == 0 else 1)
        if not candidates:
            stats.no_candidate_reason = (
                "no_candidate_generated_today: the current workflow/daily run did not produce "
                "classified content records for review. Historical sample content was not reused."
            )
        stats.finished_at = utc_now()
        stats.notes = (
            "Stage 12 generated a daily candidate review package and SQLite review queue. "
            "No LinkedIn publishing or external posting was performed."
        )

        candidate_records = write_daily_outputs(
            stats=stats,
            candidates=candidates,
            output_root=args.output_root,
            workflow_stdout_tail=tail_text(workflow_stdout),
            workflow_stderr_tail=tail_text(workflow_stderr),
            logger=logger,
        )
        record_daily_run(connection, stats)
        upsert_review_items(connection, candidate_records)

    overall_success = stats.workflow_return_code == 0 and stats.errors == 0
    logger.info("Stage 12 completed. success=%s stats=%s", overall_success, asdict(stats))

    print("\nStage 12 daily run and human review queue completed")
    print(f"Daily run ID: {stats.run_id}")
    print(f"Run date: {stats.run_date}")
    print(f"Overall success: {overall_success}")
    print(f"Wrapped workflow run ID: {stats.workflow_run_id or 'skipped/not parsed'}")
    print(f"News seen: {stats.items_seen}")
    print(f"News inserted: {stats.items_inserted}")
    print(f"Items kept: {stats.items_kept}")
    print(f"Items classified: {stats.items_classified}")
    print(f"Candidate posts: {stats.candidate_posts}")
    print(f"Images generated: {stats.images_generated}")
    print(f"Review items: {stats.review_items}")
    print(f"Lineage mode: {stats.lineage_mode}")
    print(f"No-candidate reason: {stats.no_candidate_reason or 'not_applicable'}")
    print(f"Errors: {stats.errors}")
    print(f"Daily output dir: {stats.output_dir}")
    print(f"Review queue: {stats.review_queue_path}")
    print(f"Manifest: {stats.manifest_path}")
    print(f"Daily log file: {stats.daily_log_path}")
    return 0 if overall_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
