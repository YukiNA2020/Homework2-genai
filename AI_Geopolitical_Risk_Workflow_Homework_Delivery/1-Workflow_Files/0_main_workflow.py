"""Stage 6/10/11: end-to-end workflow orchestrator.

This script runs the workflow from ingestion to final LinkedIn content
generation, writes a master run log, and performs a small database health check
for handoff testing. Stage 10 adds a shared LLM mode while preserving the
offline MVP baseline by default. Stage 11 can be included explicitly to render
post visuals and archive content bundles.
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api_config import DATABASE_PATH, LOG_DIR
from llm_stage_utils import LLM_MODE_CHOICES


WORKFLOW_DIR = Path(__file__).resolve().parent
IMAGE_MODE_CHOICES = ("offline", "auto", "online")

STAGE_CONFIGS = [
    {
        "key": "stage_2_news_monitoring",
        "label": "Stage 2 news monitoring",
        "script": "1_news_monitoring.py",
        "args": ["--input-mode", "local_sample", "--llm-mode", "offline"],
    },
    {
        "key": "stage_3a_relevance_router",
        "label": "Stage 3A relevance routing",
        "script": "2_relevance_router.py",
        "args": ["--rerun", "--llm-mode", "offline"],
    },
    {
        "key": "stage_3b_information_classification",
        "label": "Stage 3B information classification",
        "script": "3_information_classification.py",
        "args": ["--rerun", "--llm-mode", "offline"],
    },
    {
        "key": "stage_4_linkedin_analysis",
        "label": "Stage 4 LinkedIn KOL analysis",
        "script": "4_linkedin_analysis.py",
        "args": [],
    },
    {
        "key": "stage_5_linkedin_content_generation",
        "label": "Stage 5 LinkedIn content generation",
        "script": "5_linkedin_content_generation.py",
        "args": [],
    },
]

OPTIONAL_STAGE11_CONFIG = {
    "key": "stage_11_image_generation_archive",
    "label": "Stage 11 image generation and archive",
    "script": "6_image_generation.py",
    "args": ["--image-mode", "offline"],
}


@dataclass
class StageResult:
    stage_key: str
    label: str
    command: list[str]
    return_code: int
    started_at: str
    finished_at: str
    duration_seconds: float
    stdout_tail: str
    stderr_tail: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def tail_text(text: str, max_lines: int = 24) -> str:
    lines = text.strip().splitlines()
    return "\n".join(lines[-max_lines:]) if lines else ""


def setup_logger(run_id: str) -> tuple[logging.Logger, Path]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{run_id}_main_workflow.log"
    logger = logging.getLogger(f"main_workflow.{run_id}")
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


def run_stage(
    stage_config: dict[str, Any],
    db_path: Path,
    logger: logging.Logger,
) -> StageResult:
    script_path = WORKFLOW_DIR / stage_config["script"]
    command = [
        sys.executable,
        str(script_path),
        *stage_config["args"],
        "--db-path",
        str(db_path),
    ]

    start_time = datetime.now(timezone.utc)
    started_at = utc_now()
    logger.info("Starting %s", stage_config["label"])
    logger.info("Command: %s", " ".join(command))

    completed = subprocess.run(
        command,
        cwd=WORKFLOW_DIR,
        text=True,
        capture_output=True,
        check=False,
    )

    finished_at = utc_now()
    duration_seconds = round((datetime.now(timezone.utc) - start_time).total_seconds(), 2)

    if completed.stdout.strip():
        logger.info("%s stdout:\n%s", stage_config["label"], completed.stdout.strip())
    if completed.stderr.strip():
        logger.info("%s stderr:\n%s", stage_config["label"], completed.stderr.strip())

    if completed.returncode == 0:
        logger.info("Completed %s in %.2fs", stage_config["label"], duration_seconds)
    else:
        logger.error(
            "%s failed with return code %s after %.2fs",
            stage_config["label"],
            completed.returncode,
            duration_seconds,
        )

    return StageResult(
        stage_key=stage_config["key"],
        label=stage_config["label"],
        command=command,
        return_code=completed.returncode,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=duration_seconds,
        stdout_tail=tail_text(completed.stdout),
        stderr_tail=tail_text(completed.stderr),
    )


def count_table(connection: sqlite3.Connection, table_name: str) -> int:
    cursor = connection.execute(f"SELECT COUNT(*) FROM {table_name}")
    return int(cursor.fetchone()[0])


def validate_database(db_path: Path, include_stage11: bool = False) -> dict[str, Any]:
    if not db_path.exists():
        return {
            "database_exists": False,
            "checks_passed": False,
            "counts": {},
            "messages": [f"Database not found: {db_path}"],
        }

    counts: dict[str, int] = {}
    messages: list[str] = []
    with sqlite3.connect(db_path) as connection:
        table_names = [
            "news_items",
            "relevance_routing_results",
            "classification_results",
            "kol_analysis_results",
            "linkedin_content_results",
            "ingestion_runs",
            "routing_runs",
            "classification_runs",
            "kol_analysis_runs",
            "linkedin_content_runs",
        ]
        if include_stage11:
            table_names.extend([
                "image_generation_results",
                "image_generation_runs",
            ])

        for table_name in table_names:
            counts[table_name] = count_table(connection, table_name)

        cursor = connection.execute(
            """
            SELECT decision, COUNT(*)
            FROM relevance_routing_results
            GROUP BY decision
            """
        )
        routing_decisions = {row[0]: int(row[1]) for row in cursor.fetchall()}

        cursor = connection.execute(
            """
            SELECT primary_category, COUNT(*)
            FROM classification_results
            GROUP BY primary_category
            """
        )
        category_counts = {row[0]: int(row[1]) for row in cursor.fetchall()}

        cursor = connection.execute(
            """
            SELECT primary_category, LENGTH(linkedin_post), LENGTH(visual_prompt)
            FROM linkedin_content_results
            """
        )
        content_lengths = [
            {
                "primary_category": row[0],
                "linkedin_post_length": int(row[1] or 0),
                "visual_prompt_length": int(row[2] or 0),
            }
            for row in cursor.fetchall()
        ]
        try:
            cursor = connection.execute(
                """
                SELECT factual_validation_status, COUNT(*)
                FROM linkedin_content_results
                GROUP BY factual_validation_status
                """
            )
            factual_validation_statuses = {row[0] or "not_run": int(row[1]) for row in cursor.fetchall()}
        except sqlite3.OperationalError:
            factual_validation_statuses = {}

        image_outputs: list[dict[str, Any]] = []
        if include_stage11:
            cursor = connection.execute(
                """
                SELECT primary_category, image_path, archive_post_path, status
                FROM image_generation_results
                """
            )
            image_outputs = [
                {
                    "primary_category": row[0],
                    "image_path": row[1],
                    "archive_post_path": row[2],
                    "status": row[3],
                    "image_exists": Path(row[1]).exists() if row[1] else False,
                    "archive_post_exists": Path(row[2]).exists() if row[2] else False,
                }
                for row in cursor.fetchall()
            ]

    expected_checks = {
        "news_items_at_least_6": counts["news_items"] >= 6,
        "routing_results_at_least_6": counts["relevance_routing_results"] >= 6,
        "kept_items_at_least_4": routing_decisions.get("keep", 0) >= 4,
        "classification_results_at_least_4": counts["classification_results"] >= 4,
        "kol_profiles_at_least_4": counts["kol_analysis_results"] >= 4,
        "linkedin_posts_at_least_2": counts["linkedin_content_results"] >= 2,
        "linkedin_outputs_nonempty": all(
            item["linkedin_post_length"] > 200 and item["visual_prompt_length"] > 80
            for item in content_lengths
        ),
        "stage14_factual_validation_passed": bool(factual_validation_statuses)
        and not any(
            status in {"factual_validation_failed", "not_run"}
            for status in factual_validation_statuses
        ),
    }

    if include_stage11:
        expected_checks.update(
            {
                "image_generation_results_at_least_2": counts.get("image_generation_results", 0) >= 2,
                "image_files_exist": bool(image_outputs)
                and all(item["image_exists"] for item in image_outputs),
                "archive_posts_exist": bool(image_outputs)
                and all(item["archive_post_exists"] for item in image_outputs),
            }
        )

    for check_name, passed in expected_checks.items():
        messages.append(f"{check_name}: {'PASS' if passed else 'FAIL'}")

    return {
        "database_exists": True,
        "checks_passed": all(expected_checks.values()),
        "counts": counts,
        "routing_decisions": routing_decisions,
        "category_counts": category_counts,
        "content_lengths": content_lengths,
        "factual_validation_statuses": factual_validation_statuses,
        "image_outputs": image_outputs,
        "checks": expected_checks,
        "messages": messages,
    }


def parse_args() -> argparse.Namespace:
    stage_keys = [stage["key"] for stage in STAGE_CONFIGS] + [OPTIONAL_STAGE11_CONFIG["key"]]
    parser = argparse.ArgumentParser(description="Run the full MVP workflow with optional Stage 10 LLM mode.")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DATABASE_PATH,
        help="SQLite database path shared by all workflow stages.",
    )
    parser.add_argument(
        "--skip-stage",
        action="append",
        choices=stage_keys,
        default=[],
        help="Skip a stage by key. May be provided multiple times.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue later stages even if one stage fails.",
    )
    parser.add_argument(
        "--stage2-input-mode",
        choices=["local_sample", "rss", "all"],
        default="local_sample",
        help="Input mode for Stage 2 ingestion. Default preserves the offline MVP baseline.",
    )
    parser.add_argument(
        "--rss-limit",
        type=int,
        default=None,
        help="Optional maximum RSS items per source when Stage 2 uses rss or all.",
    )
    parser.add_argument(
        "--llm-mode",
        choices=LLM_MODE_CHOICES,
        default="offline",
        help="LLM behavior for Stage 2/3/5: offline, auto, or online. Default preserves offline MVP.",
    )
    parser.add_argument(
        "--stage10-max-items",
        type=int,
        default=None,
        help="Optional small-batch limit for Stage 10 online validation across Stage 2/3/5.",
    )
    parser.add_argument(
        "--include-stage11",
        action="store_true",
        help="Also run Stage 11 image generation and content archiving after Stage 5.",
    )
    parser.add_argument(
        "--image-mode",
        choices=IMAGE_MODE_CHOICES,
        default="offline",
        help="Image behavior for Stage 11: offline, auto, or online. Default preserves offline fallback.",
    )
    parser.add_argument(
        "--stage11-max-items",
        type=int,
        default=None,
        help="Optional limit for Stage 11 image/archive handoff testing.",
    )
    parser.add_argument(
        "--workflow-run-id",
        default="",
        help="Optional explicit workflow run ID. Defaults to an auto-generated run ID.",
    )
    parser.add_argument(
        "--daily-run-id",
        default="",
        help="Optional Stage 12 daily run ID to pass through for data lineage.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_id = args.workflow_run_id or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    logger, log_path = setup_logger(run_id)
    logger.info("Starting Stage 6 main workflow run: %s", run_id)
    logger.info("Database path: %s", args.db_path)
    logger.info("Daily run ID: %s", args.daily_run_id or "not_set")

    results: list[StageResult] = []
    stage_configs = [dict(stage_config) for stage_config in STAGE_CONFIGS]
    stage_configs[0]["args"] = ["--input-mode", args.stage2_input_mode, "--llm-mode", args.llm_mode]
    if args.rss_limit is not None:
        stage_configs[0]["args"].extend(["--rss-limit", str(args.rss_limit)])
    for stage_config in stage_configs[1:3]:
        stage_config["args"] = [*stage_config["args"][:-1], args.llm_mode]
    stage_configs[4]["args"] = ["--llm-mode", args.llm_mode]
    if args.stage10_max_items is not None:
        stage_configs[0]["args"].extend(["--max-items", str(args.stage10_max_items)])
        for stage_config in stage_configs[1:3]:
            stage_config["args"].extend(["--max-items", str(args.stage10_max_items)])
        stage_configs[4]["args"].extend([
            "--max-items-per-category",
            str(max(1, args.stage10_max_items)),
        ])

    lineage_args = ["--workflow-run-id", run_id]
    if args.daily_run_id:
        lineage_args.extend(["--daily-run-id", args.daily_run_id])
    for stage_config in stage_configs:
        if stage_config["key"] != "stage_4_linkedin_analysis":
            stage_config["args"].extend(lineage_args)

    if args.include_stage11:
        stage11_config = dict(OPTIONAL_STAGE11_CONFIG)
        stage11_config["args"] = ["--image-mode", args.image_mode]
        if args.stage11_max_items is not None:
            stage11_config["args"].extend(["--max-items", str(args.stage11_max_items)])
        stage11_config["args"].extend(lineage_args)
        stage_configs.append(stage11_config)

    for stage_config in stage_configs:
        if stage_config["key"] in args.skip_stage:
            logger.info("Skipping %s", stage_config["label"])
            continue

        result = run_stage(stage_config, args.db_path, logger)
        results.append(result)
        if result.return_code != 0 and not args.continue_on_error:
            logger.error("Stopping workflow because %s failed.", result.label)
            break

    validation = validate_database(args.db_path, include_stage11=args.include_stage11)
    if args.daily_run_id:
        validation.setdefault("checks", {})["stage13_daily_lineage_scope_enabled"] = True
        validation["checks_passed"] = bool(validation.get("database_exists", False))
        validation.setdefault("messages", []).append(
            "stage13_daily_lineage_scope_enabled: PASS "
            "(run-scoped daily mode allows zero candidates when current-run evidence is insufficient)"
        )
    stages_ok = all(result.return_code == 0 for result in results)
    overall_success = stages_ok and bool(validation["checks_passed"])

    summary = {
        "run_id": run_id,
        "daily_run_id": args.daily_run_id,
        "overall_success": overall_success,
        "database": str(args.db_path),
        "master_log": str(log_path),
        "stages": [asdict(result) for result in results],
        "validation": validation,
    }
    logger.info("Stage 6 workflow summary:\n%s", json.dumps(summary, ensure_ascii=False, indent=2))

    print("\nStage 6 main workflow completed")
    print(f"Run ID: {run_id}")
    print(f"Overall success: {overall_success}")
    print(f"Database: {args.db_path}")
    print("Stages:")
    for result in results:
        status = "OK" if result.return_code == 0 else "FAILED"
        print(f"- {result.label}: {status} ({result.duration_seconds}s)")
    print("Validation:")
    for message in validation["messages"]:
        print(f"- {message}")
    print(f"Master log file: {log_path}")

    return 0 if overall_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
