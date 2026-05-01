"""Stage 5: LinkedIn decision-brief content generation.

This stage reads the classified high-relevance records from SQLite and turns
the two project categories into final LinkedIn-ready decision briefs. The MVP
keeps generation deterministic and offline, while preserving the same output
contract expected from a later DeepSeek V4 content-generation call.
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import textwrap
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api_config import (
    CATEGORY_1_POST_PATH,
    CATEGORY_2_POST_PATH,
    DATABASE_PATH,
    DEFAULT_LLM_CONFIG,
    IMAGE_GENERATION_PROMPT_PATH,
    LINKEDIN_POST_GENERATION_PROMPT_PATH,
    LOG_DIR,
    SQLITE_SCHEMA_PATH,
)


PROMPT_VERSION = "linkedin_content_generation_v1_offline_mvp"

TARGET_CATEGORIES = {
    "AI算力基础设施地缘风险": {
        "category_label": "Category 1: AI Infrastructure Geopolitical Risk",
        "target_audience": (
            "AI infrastructure investors, data center operators, cloud strategy teams, "
            "and multinational AI enterprise strategy leaders."
        ),
        "tone_positioning": (
            "Professional insight plus risk-warning decision brief, written for "
            "executives and investors who need infrastructure allocation signals."
        ),
        "output_path": CATEGORY_1_POST_PATH,
    },
    "AI关键矿产供应链与地缘政治": {
        "category_label": "Category 2: AI Critical Mineral Supply Chain Geopolitics",
        "target_audience": (
            "AI infrastructure investors, commodity investors, and AI enterprise "
            "supply-chain leaders."
        ),
        "tone_positioning": (
            "Deep-analysis executive brief that links mineral supply risk to AI "
            "infrastructure cost, timing, and investment decisions."
        ),
        "output_path": CATEGORY_2_POST_PATH,
    },
}


@dataclass
class ContentGenerationStats:
    run_id: str
    started_at: str
    finished_at: str = ""
    categories_seen: int = 0
    posts_generated: int = 0
    outputs_written: int = 0
    errors: int = 0
    notes: str = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_json_list(raw_value: str) -> list[str]:
    try:
        value = json.loads(raw_value or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def apply_schema(db_path: Path, schema_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.executescript(schema_path.read_text(encoding="utf-8"))


def setup_logger(run_id: str) -> tuple[logging.Logger, Path]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{run_id}_linkedin_content_generation.log"
    logger = logging.getLogger(f"linkedin_content_generation.{run_id}")
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


def select_category_items(
    connection: sqlite3.Connection,
    primary_category: str,
    max_items: int,
) -> list[sqlite3.Row]:
    connection.row_factory = sqlite3.Row
    cursor = connection.execute(
        """
        SELECT
            news_items.id AS news_id,
            news_items.title,
            news_items.url,
            news_items.published_at,
            news_items.source_name,
            news_items.source_type,
            news_items.summary,
            news_items.cleaned_content,
            news_items.keywords,
            relevance_routing_results.relevance_score,
            relevance_routing_results.rationale AS routing_rationale,
            classification_results.primary_category,
            classification_results.auxiliary_tags,
            classification_results.confidence AS classification_confidence,
            classification_results.rationale AS classification_rationale
        FROM classification_results
        INNER JOIN news_items
            ON news_items.id = classification_results.news_id
        INNER JOIN relevance_routing_results
            ON relevance_routing_results.news_id = news_items.id
        WHERE classification_results.primary_category = ?
          AND relevance_routing_results.decision = 'keep'
        ORDER BY
            relevance_routing_results.relevance_score DESC,
            classification_results.confidence DESC,
            news_items.published_at DESC,
            news_items.id ASC
        LIMIT ?
        """,
        (primary_category, max_items),
    )
    return list(cursor.fetchall())


def build_evidence_basis(items: list[sqlite3.Row]) -> list[dict[str, Any]]:
    evidence = []
    for item in items:
        evidence.append(
            {
                "news_id": item["news_id"],
                "title": item["title"],
                "source_name": item["source_name"],
                "source_type": item["source_type"],
                "published_at": item["published_at"],
                "relevance_score": item["relevance_score"],
                "classification_confidence": item["classification_confidence"],
                "auxiliary_tags": parse_json_list(item["auxiliary_tags"]),
                "routing_rationale": item["routing_rationale"],
            }
        )
    return evidence


def render_evidence_signal(items: list[sqlite3.Row]) -> str:
    titles = [item["title"] for item in items]
    if len(titles) == 1:
        return titles[0]
    return "; ".join(titles[:-1]) + "; and " + titles[-1]


def generate_infrastructure_post(items: list[sqlite3.Row]) -> str:
    evidence_signal = render_evidence_signal(items)
    return textwrap.dedent(
        f"""
        AI compute risk is no longer only about chip supply. It is becoming a site-selection and resilience problem.

        What happened:
        The current monitored set points to three connected signals: {evidence_signal}.

        Why it matters for AI infrastructure:
        Power access, GPU procurement, logistics, and cross-border customer allocation now interact. A data center plan that looks attractive on latency, incentives, or land cost can change quickly if grid queues, export-control compliance, or indirect energy and shipping shocks tighten at the same time.

        Business implications:
        - Site selection needs geopolitical and energy-risk scoring, not just land and power-price screens.
        - GPU and accelerator deployment plans should include compliance scenarios for where high-end compute can be placed and served.
        - Continuity planning should treat energy, shipping, backup fuel, network redundancy, and component delivery as one operating-risk system.

        Signals to watch:
        - Grid connection delays, permitting changes, and power purchase agreement competition in AI data center markets.
        - Export-control guidance affecting advanced accelerators and cross-border cloud customers.
        - Shipping insurance, fuel-contract, and energy-security indicators around conflict-exposed regions.

        Closing question:
        For AI infrastructure investors and operators, which constraint should now move earliest in diligence: power availability, accelerator compliance, or regional continuity risk?

        #AIInfrastructure #Geopolitics #DataCenters
        """
    ).strip()


def generate_mineral_post(items: list[sqlite3.Row]) -> str:
    evidence_signal = render_evidence_signal(items)
    return textwrap.dedent(
        f"""
        Copper may be one of the quietest bottlenecks in the AI buildout story.

        What happened:
        The selected critical-minerals signal is: {evidence_signal}. It links rising demand from data centers, power transmission, and semiconductor manufacturing with political risk in key producing regions.

        Why it matters for AI infrastructure:
        AI compute expansion is physical infrastructure before it is only software. Copper availability can shape grid expansion, data center electrical systems, transmission capacity, and the upstream cost base behind AI infrastructure deployment.

        Business implications:
        - AI infrastructure cost models should stress-test mineral input inflation and construction delays, not only GPU pricing.
        - Investors need to compare compute capacity pipelines with copper, transmission, and permitting bottlenecks.
        - Supply-chain teams should monitor regional concentration risk alongside chip and accelerator availability.

        Signals to watch:
        - Permitting timelines and disruption risk in copper-producing regions.
        - Transmission equipment lead times and grid expansion plans in data center markets.
        - Policy signals around resource nationalism, export limits, or shipping constraints.

        Closing question:
        If AI demand keeps moving from model roadmaps into grid-scale construction, should copper risk be treated as a core AI infrastructure KPI rather than a commodity footnote?

        #AIInfrastructure #CriticalMinerals #SupplyChain
        """
    ).strip()


def generate_visual_prompt(primary_category: str, post: str) -> str:
    if primary_category == "AI算力基础设施地缘风险":
        return (
            "Create a professional 16:9 LinkedIn visual for an executive brief on AI "
            "infrastructure geopolitical risk. Show a modern data center connected to "
            "power-grid lines, cloud compute nodes, and subtle map-based regional risk "
            "markers. Use a clean editorial style, realistic lighting, restrained colors, "
            "no logos, no text overlays, no alarmist imagery."
        )
    return (
        "Create a professional 16:9 LinkedIn visual for an executive brief on critical "
        "minerals and AI infrastructure. Show copper supply, power transmission lines, "
        "semiconductor manufacturing, and data center construction as connected layers "
        "of one supply chain. Use a clean editorial business style, no logos, no text "
        "overlays, no sensational imagery."
    )


def quality_self_check(primary_category: str, item_count: int) -> dict[str, int]:
    credibility = 20 if item_count >= 2 else 18
    interaction_quality = 14
    if primary_category == "AI关键矿产供应链与地缘政治":
        interaction_quality = 15
    scores = {
        "domain_relevance": 25,
        "decision_value": 24,
        "credibility": credibility,
        "structure_clarity": 15,
        "interaction_quality": interaction_quality,
    }
    scores["total"] = sum(scores.values())
    return scores


def generate_category_brief(primary_category: str, items: list[sqlite3.Row]) -> dict[str, Any]:
    target = TARGET_CATEGORIES[primary_category]
    if primary_category == "AI算力基础设施地缘风险":
        linkedin_post = generate_infrastructure_post(items)
    else:
        linkedin_post = generate_mineral_post(items)

    return {
        "primary_category": primary_category,
        "category_label": target["category_label"],
        "target_audience": target["target_audience"],
        "tone_positioning": target["tone_positioning"],
        "source_news_ids": [item["news_id"] for item in items],
        "source_titles": [item["title"] for item in items],
        "evidence_basis": build_evidence_basis(items),
        "linkedin_post": linkedin_post,
        "visual_prompt": generate_visual_prompt(primary_category, linkedin_post),
        "quality_score_self_check": quality_self_check(primary_category, len(items)),
        "output_path": str(target["output_path"]),
    }


def render_markdown(brief: dict[str, Any], run_id: str, generated_at: str) -> str:
    evidence_lines = [
        "| News ID | Source type | Relevance | Classification confidence | Title |",
        "|---:|---|---:|---:|---|",
    ]
    for item in brief["evidence_basis"]:
        evidence_lines.append(
            "| {news_id} | {source_type} | {relevance_score:.2f} | "
            "{classification_confidence:.2f} | {title} |".format(**item)
        )

    score = brief["quality_score_self_check"]
    score_lines = [
        "| Dimension | Score |",
        "|---|---:|",
        f"| Domain relevance | {score['domain_relevance']} |",
        f"| Decision value | {score['decision_value']} |",
        f"| Credibility | {score['credibility']} |",
        f"| Structure clarity | {score['structure_clarity']} |",
        f"| Interaction quality | {score['interaction_quality']} |",
        f"| Total | {score['total']} |",
    ]

    return "\n".join(
        [
            f"# {brief['category_label']}",
            "",
            "> 使用环节：阶段五 - LinkedIn决策简报生成。  ",
            f"> Run ID: `{run_id}`  ",
            f"> Generated at: `{generated_at}`",
            "",
            "## Metadata",
            "",
            f"- Primary category: {brief['primary_category']}",
            f"- Target audience: {brief['target_audience']}",
            f"- Tone and positioning: {brief['tone_positioning']}",
            f"- Source news IDs: {', '.join(str(item) for item in brief['source_news_ids'])}",
            f"- Prompt version: {PROMPT_VERSION}",
            f"- Model provider placeholder: {DEFAULT_LLM_CONFIG['provider']}",
            "",
            "## Source Evidence",
            "",
            "\n".join(evidence_lines),
            "",
            "## LinkedIn Post",
            "",
            brief["linkedin_post"],
            "",
            "## Image Generation Prompt",
            "",
            brief["visual_prompt"],
            "",
            "## Quality Self-Check",
            "",
            "\n".join(score_lines),
            "",
        ]
    )


def render_post_generation_prompt() -> str:
    return textwrap.dedent(
        """
        Prompt name: Stage 5 LinkedIn post generation prompt
        Workflow step: Final LinkedIn decision-brief content generation
        Target model: DeepSeek V4 (`deepseek-v4-pro`) or equivalent reasoning model

        System role:
        You are an AI infrastructure geopolitical risk analyst writing concise
        LinkedIn decision briefs for investors, data center operators, cloud
        strategy teams, AI chip/supply-chain leaders, and cross-border risk
        managers.

        Project domain:
        AI infrastructure geopolitical risk and supply-chain decision intelligence.

        Required input:
        - Primary category
        - Target audience
        - Tone and positioning
        - News title
        - Summary
        - Source type and evidence basis
        - Relevance routing rationale
        - Classification rationale
        - Auxiliary tags
        - KOL-derived style checklist constraints

        Required structure:
        1. Hook
        2. What happened
        3. Why it matters for AI infrastructure
        4. Business implications
        5. Signals to watch
        6. Closing question

        Hard constraints:
        - Do not auto-publish or mention LinkedIn automation.
        - Do not imitate any KOL's voice directly.
        - Do not invent numbers, quotes, private facts, or source names.
        - Do not write a generic AI news summary.
        - Keep paragraphs short and mobile-readable.
        - Include exactly three business implications.
        - Include two or three signals to watch.
        - Close with a specific decision question tied to investment, supply chain,
          compliance, site selection, procurement, or business continuity.
        - Add no more than three hashtags.

        Output JSON:
        {
          "target_audience": "Specific audience segment",
          "tone_positioning": "Decision-brief tone description",
          "linkedin_post": "Full post body with section breaks",
          "visual_prompt": "Image generation prompt for a professional LinkedIn visual",
          "quality_score_self_check": {
            "domain_relevance": 0,
            "decision_value": 0,
            "credibility": 0,
            "structure_clarity": 0,
            "interaction_quality": 0,
            "total": 0
          }
        }
        """
    ).strip() + "\n"


def render_image_generation_prompt() -> str:
    return textwrap.dedent(
        """
        Prompt name: Stage 5 LinkedIn image generation prompt
        Workflow step: Image prompt for final LinkedIn decision brief
        Target image model: Any professional business-image generation model

        System role:
        You create image prompts for executive LinkedIn visuals about AI
        infrastructure geopolitical risk.

        Required input:
        - Primary category
        - Main post thesis
        - Business implications
        - Signals to watch

        Visual constraints:
        - 16:9 aspect ratio.
        - Professional editorial business style.
        - Represent actual infrastructure, supply chain, energy, chips, minerals,
          data centers, or maps relevant to the post.
        - No logos, no brand marks, no text overlays, no sensational crisis imagery.
        - Avoid abstract AI brains, generic glowing robots, or decorative gradients.

        Output:
        A single polished image-generation prompt that can be copied into a visual
        generation tool.
        """
    ).strip() + "\n"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def upsert_content_result(connection: sqlite3.Connection, brief: dict[str, Any]) -> None:
    now = utc_now()
    connection.execute(
        """
        INSERT INTO linkedin_content_results (
            primary_category, target_audience, tone_positioning, source_news_ids,
            source_titles, evidence_basis, linkedin_post, visual_prompt,
            quality_score_self_check, output_path, prompt_version, model_provider,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(primary_category) DO UPDATE SET
            target_audience = excluded.target_audience,
            tone_positioning = excluded.tone_positioning,
            source_news_ids = excluded.source_news_ids,
            source_titles = excluded.source_titles,
            evidence_basis = excluded.evidence_basis,
            linkedin_post = excluded.linkedin_post,
            visual_prompt = excluded.visual_prompt,
            quality_score_self_check = excluded.quality_score_self_check,
            output_path = excluded.output_path,
            prompt_version = excluded.prompt_version,
            model_provider = excluded.model_provider,
            updated_at = excluded.updated_at
        """,
        (
            brief["primary_category"],
            brief["target_audience"],
            brief["tone_positioning"],
            json.dumps(brief["source_news_ids"], ensure_ascii=False),
            json.dumps(brief["source_titles"], ensure_ascii=False),
            json.dumps(brief["evidence_basis"], ensure_ascii=False),
            brief["linkedin_post"],
            brief["visual_prompt"],
            json.dumps(brief["quality_score_self_check"], ensure_ascii=False),
            brief["output_path"],
            PROMPT_VERSION,
            DEFAULT_LLM_CONFIG["provider"],
            now,
            now,
        ),
    )


def record_run(connection: sqlite3.Connection, stats: ContentGenerationStats) -> None:
    connection.execute(
        """
        INSERT INTO linkedin_content_runs (
            run_id, started_at, finished_at, categories_seen, posts_generated,
            outputs_written, errors, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            stats.run_id,
            stats.started_at,
            stats.finished_at,
            stats.categories_seen,
            stats.posts_generated,
            stats.outputs_written,
            stats.errors,
            stats.notes,
        ),
    )


def run_linkedin_content_generation(
    db_path: Path,
    post_prompt_path: Path,
    image_prompt_path: Path,
    max_items_per_category: int,
) -> tuple[ContentGenerationStats, Path, list[Path]]:
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    logger, log_path = setup_logger(run_id)
    stats = ContentGenerationStats(run_id=run_id, started_at=utc_now())
    generated_at = utc_now()
    output_paths: list[Path] = []

    logger.info("Starting Stage 5 LinkedIn content generation run: %s", run_id)
    logger.info("Target categories configured: %s", list(TARGET_CATEGORIES.keys()))
    logger.info(
        "LLM provider placeholder: %s | enabled=%s",
        DEFAULT_LLM_CONFIG["provider"],
        DEFAULT_LLM_CONFIG["enabled"],
    )

    apply_schema(db_path, SQLITE_SCHEMA_PATH)

    with sqlite3.connect(db_path) as connection:
        for primary_category, target in TARGET_CATEGORIES.items():
            try:
                items = select_category_items(connection, primary_category, max_items_per_category)
                if not items:
                    stats.errors += 1
                    logger.error("No classified items found for category: %s", primary_category)
                    continue

                stats.categories_seen += 1
                brief = generate_category_brief(primary_category, items)
                output_path = Path(target["output_path"])
                write_text(output_path, render_markdown(brief, run_id, generated_at))
                upsert_content_result(connection, brief)
                output_paths.append(output_path)
                stats.posts_generated += 1
                stats.outputs_written += 1
                logger.info(
                    "GENERATED | %s | items=%s | output=%s",
                    primary_category,
                    len(items),
                    output_path,
                )
            except Exception as exc:  # noqa: BLE001 - keep stage run resilient.
                stats.errors += 1
                logger.error("Failed to generate category=%s: %s", primary_category, exc)

        try:
            write_text(post_prompt_path, render_post_generation_prompt())
            write_text(image_prompt_path, render_image_generation_prompt())
            output_paths.extend([post_prompt_path, image_prompt_path])
            stats.outputs_written += 2
            logger.info("WROTE | %s", post_prompt_path)
            logger.info("WROTE | %s", image_prompt_path)
        except Exception as exc:  # noqa: BLE001 - keep stage run resilient.
            stats.errors += 1
            logger.error("Failed to write Stage 5 prompt samples: %s", exc)

        stats.finished_at = utc_now()
        stats.notes = (
            "Offline Stage 5 content generation completed. The output uses "
            "classified SQLite records and the Stage 4 decision-brief constraints; "
            "DeepSeek V4 can later replace the deterministic generator."
        )
        record_run(connection, stats)

    logger.info(
        "Completed content generation. categories=%s posts=%s outputs=%s errors=%s",
        stats.categories_seen,
        stats.posts_generated,
        stats.outputs_written,
        stats.errors,
    )
    return stats, log_path, output_paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Stage 5 LinkedIn content generation.")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DATABASE_PATH,
        help="SQLite database path.",
    )
    parser.add_argument(
        "--post-prompt-path",
        type=Path,
        default=LINKEDIN_POST_GENERATION_PROMPT_PATH,
        help="Output path for the Stage 5 LinkedIn post generation prompt sample.",
    )
    parser.add_argument(
        "--image-prompt-path",
        type=Path,
        default=IMAGE_GENERATION_PROMPT_PATH,
        help="Output path for the Stage 5 image generation prompt sample.",
    )
    parser.add_argument(
        "--max-items-per-category",
        type=int,
        default=3,
        help="Maximum classified records used to generate each category brief.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stats, log_path, output_paths = run_linkedin_content_generation(
        args.db_path,
        args.post_prompt_path,
        args.image_prompt_path,
        args.max_items_per_category,
    )
    print("\nStage 5 LinkedIn content generation completed")
    print(f"Run ID: {stats.run_id}")
    print(f"Database: {args.db_path}")
    print(f"Categories seen: {stats.categories_seen}")
    print(f"Posts generated: {stats.posts_generated}")
    print(f"Outputs written: {stats.outputs_written}")
    print(f"Errors: {stats.errors}")
    print("Output files:")
    for output_path in output_paths:
        print(f"- {output_path}")
    print(f"Log file: {log_path}")


if __name__ == "__main__":
    main()
