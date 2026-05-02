"""Stage 4: LinkedIn KOL style analysis and content constraints.

This stage turns representative KOL content patterns into a reusable checklist
for decision-brief LinkedIn posts. It stays offline and deterministic for the
MVP, while preserving the same output contract expected from a later LLM-based
KOL analysis workflow.
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
    DATABASE_PATH,
    DEFAULT_LLM_CONFIG,
    KOL_STYLE_ANALYSIS_PROMPT_PATH,
    KOL_STYLE_CHECKLIST_PATH,
    LINKEDIN_CONTENT_CONSTRAINTS_PROMPT_PATH,
    LOG_DIR,
    SQLITE_SCHEMA_PATH,
)


PROMPT_VERSION = "kol_linkedin_style_analysis_v1_offline_mvp"

KOL_PROFILES = [
    {
        "name": "Chris Miller",
        "focus_area": "Semiconductors, chip supply chains, industrial chokepoints, and technology power.",
        "sample_basis": (
            "Representative public-author style from long-form chip geopolitics analysis, "
            "book/interview themes, and supply-chain risk commentary."
        ),
        "observed_patterns": {
            "hook": "Starts from a strategic chokepoint: advanced chips, fabs, export controls, or supply concentration.",
            "structure": "Moves from a concrete supply-chain node to the larger balance-of-power implication.",
            "credibility": "Builds authority through industrial detail, historical context, and named supply-chain layers.",
            "interaction": "Frames discussion around strategic dependency rather than generic technology optimism.",
            "style": "Dense but clear. Uses sober risk language and avoids exaggerated AI hype.",
        },
        "transfer_rules": [
            "Treat chips and compute inputs as strategic infrastructure, not abstract technology.",
            "Show where the bottleneck sits in the chain: design, equipment, fabrication, packaging, power, or minerals.",
            "Translate geopolitical pressure into business exposure for investors and operators.",
        ],
        "limitations": "Do not imitate book-style historical length; compress the pattern into a LinkedIn brief.",
    },
    {
        "name": "Paul Triolo",
        "focus_area": "Technology geopolitics, AI regulation, US-China tech competition, and cross-border policy risk.",
        "sample_basis": (
            "Representative public policy-analysis style from tech geopolitics briefings, "
            "commentary, and regulatory interpretation."
        ),
        "observed_patterns": {
            "hook": "Opens with a policy shift or regulatory signal that changes operating assumptions.",
            "structure": "Separates what changed, who is affected, and how firms may adapt.",
            "credibility": "Uses policy context, jurisdictional nuance, and cross-border implementation details.",
            "interaction": "Asks whether firms should adjust strategy, compliance, or market access assumptions.",
            "style": "Measured, precise, and scenario-oriented. Avoids one-sided political framing.",
        },
        "transfer_rules": [
            "Connect policy language to concrete operating constraints.",
            "Separate immediate effects from second-order effects on procurement, deployment, and compliance.",
            "Use scenario language when outcomes remain uncertain.",
        ],
        "limitations": "Avoid becoming a policy memo; keep business implications visible in every section.",
    },
    {
        "name": "Gregory C. Allen",
        "focus_area": "AI national security, industrial policy, export controls, and governance design.",
        "sample_basis": (
            "Representative think-tank analysis style from AI policy, national security, "
            "and industrial strategy commentary."
        ),
        "observed_patterns": {
            "hook": "Starts with a national-security or policy-design consequence rather than a product update.",
            "structure": "Defines the strategic problem, explains the mechanism, then gives policy or industry implications.",
            "credibility": "Anchors claims in institutional reports, government actions, and clear causal reasoning.",
            "interaction": "Invites debate on trade-offs: competitiveness, security, innovation, and implementation risk.",
            "style": "Institutional, analytical, and evidence-led. Uses direct causal claims with caveats.",
        },
        "transfer_rules": [
            "Make the mechanism explicit: why a policy or risk signal changes AI infrastructure decisions.",
            "Use evidence hierarchy: official action, credible report, company response, market signal.",
            "Include trade-offs instead of presenting a single deterministic outcome.",
        ],
        "limitations": "Avoid overly academic framing; the final post must still be readable on mobile.",
    },
    {
        "name": "Jordan Schneider",
        "focus_area": "China technology policy, AI and semiconductor competition, and strategic industry narratives.",
        "sample_basis": (
            "Representative ChinaTalk-style public analysis: conversational framing, "
            "sharp synthesis, and bridge-building between policy and industry."
        ),
        "observed_patterns": {
            "hook": "Uses a sharp strategic question, counterintuitive comparison, or narrative tension.",
            "structure": "Breaks complex policy and industry dynamics into memorable, decision-relevant chunks.",
            "credibility": "Combines expert synthesis, primary-source awareness, and clear explanation of incentives.",
            "interaction": "Ends with a question that serious readers can actually debate.",
            "style": "More conversational than think-tank prose, but still analytical and grounded.",
        },
        "transfer_rules": [
            "Use one memorable tension to make the post readable without diluting substance.",
            "Explain incentives of governments, firms, and capital providers.",
            "Close with a specific decision question rather than a generic engagement prompt.",
        ],
        "limitations": "Do not over-copy the conversational tone; keep the project voice as a decision brief.",
    },
]


@dataclass
class KOLAnalysisStats:
    run_id: str
    started_at: str
    finished_at: str = ""
    profiles_analyzed: int = 0
    outputs_written: int = 0
    errors: int = 0
    notes: str = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def apply_schema(db_path: Path, schema_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.executescript(schema_path.read_text(encoding="utf-8"))


def setup_logger(run_id: str) -> tuple[logging.Logger, Path]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{run_id}_linkedin_analysis.log"
    logger = logging.getLogger(f"linkedin_analysis.{run_id}")
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


def analyze_profile(profile: dict[str, Any]) -> dict[str, Any]:
    patterns = profile["observed_patterns"]
    return {
        "kol_name": profile["name"],
        "focus_area": profile["focus_area"],
        "sample_basis": profile["sample_basis"],
        "hook_pattern": patterns["hook"],
        "structure_pattern": patterns["structure"],
        "credibility_pattern": patterns["credibility"],
        "interaction_pattern": patterns["interaction"],
        "style_pattern": patterns["style"],
        "transferable_rules": profile["transfer_rules"],
        "limitations": profile["limitations"],
    }


def build_collective_style_rules(results: list[dict[str, Any]]) -> dict[str, list[str]]:
    return {
        "opening_hook": [
            "Use a concrete risk signal, bottleneck, policy shift, key number, or counterintuitive judgment.",
            "Make the first two lines understandable without background context.",
            "Avoid opening with generic phrases such as 'AI is changing everything'.",
        ],
        "brief_structure": [
            "Hook",
            "What happened",
            "Why it matters for AI infrastructure",
            "Business implications",
            "Signals to watch",
            "Closing question",
        ],
        "credibility": [
            "Name the evidence type: institution report, company announcement, policy action, market data, or credible media report.",
            "State causal links clearly: event -> infrastructure constraint -> business decision.",
            "Do not invent numbers, quotes, or confidential market claims.",
        ],
        "decision_audience_fit": [
            "Write for AI infrastructure investors, data center operators, cloud strategy teams, and supply-chain risk leaders.",
            "Translate news into investment timing, site selection, procurement, compliance, or continuity implications.",
            "Keep the tone analytical, not promotional.",
        ],
        "mobile_readability": [
            "Use short paragraphs of one to three sentences.",
            "Prefer compact bullets for business implications and signals to watch.",
            "Keep hashtags optional and limited to three.",
        ],
        "avoid": [
            "Do not imitate any KOL voice directly.",
            "Do not turn the post into a generic news summary.",
            "Do not overstate certainty when the source only supports a scenario.",
        ],
    }


def render_bullet_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def render_checklist(results: list[dict[str, Any]], run_id: str, generated_at: str) -> str:
    rules = build_collective_style_rules(results)
    lines = [
        "# LinkedIn AI基建地缘风险帖子风格与结构清单",
        "",
        "> 使用环节：阶段四 - KOL内容拆解与风格指南。",
        "> 目标：把对标KOL的内容逻辑转化为本项目可复用的“决策简报式LinkedIn帖子”规范。",
        f"> Run ID: `{run_id}`",
        f"> Generated at: `{generated_at}`",
        "",
        "## 1. 写作定位",
        "",
        "本项目的LinkedIn内容不是泛AI新闻摘要，也不是自动发布工具。它面向AI基建投资者、数据中心与云厂商战略团队、芯片/算力供应链负责人，以及关注科技地缘政治的行业分析师。",
        "",
        "核心任务是把阶段二和阶段三筛出的高相关性信息，转化为对投资、供应链、合规、数据中心布局或业务连续性有启发的短篇决策简报。",
        "",
        "## 2. 对标KOL拆解总览",
        "",
        "| KOL | 关注重点 | 常见开篇方式 | 可迁移风格 |",
        "|---|---|---|---|",
    ]
    lines.extend(
        "| {kol_name} | {focus_area} | {hook_pattern} | {style_pattern} |".format(**result)
        for result in results
    )
    lines.extend(["", "## 3. 单个KOL可迁移规则", ""])

    for result in results:
        lines.extend(
            [
                f"### {result['kol_name']}",
                f"- Focus: {result['focus_area']}",
                f"- Hook pattern: {result['hook_pattern']}",
                f"- Structure pattern: {result['structure_pattern']}",
                f"- Credibility pattern: {result['credibility_pattern']}",
                f"- Interaction pattern: {result['interaction_pattern']}",
                "- Transfer rules:",
            ]
        )
        lines.extend(f"  - {rule}" for rule in result["transferable_rules"])
        lines.extend([f"- Boundary: {result['limitations']}", ""])

    lines.extend(
        [
            "## 4. 决策简报式帖子固定结构",
            "",
            "1. Hook  ",
            "用反直觉判断、关键数字、政策变化、供应瓶颈或风险信号开场。",
            "",
            "2. What happened  ",
            "用两到三句话说明事件或趋势，避免铺陈新闻背景。",
            "",
            "3. Why it matters for AI infrastructure  ",
            "解释它如何影响算力、数据中心、能源、电力、芯片、关键矿产或跨境运营。",
            "",
            "4. Business implications  ",
            "给出三个面向投资者或企业负责人的商业影响。",
            "",
            "5. Signals to watch  ",
            "给出两到三个后续观察指标。",
            "",
            "6. Closing question  ",
            "提出一个能引发目标受众讨论的决策问题。",
            "",
            "## 5. 内容生成约束",
            "",
            "### Opening hook",
            render_bullet_list(rules["opening_hook"]),
            "",
            "### Brief structure",
            render_bullet_list(rules["brief_structure"]),
            "",
            "### Credibility",
            render_bullet_list(rules["credibility"]),
            "",
            "### Decision audience fit",
            render_bullet_list(rules["decision_audience_fit"]),
            "",
            "### Mobile readability",
            render_bullet_list(rules["mobile_readability"]),
            "",
            "### Avoid",
            render_bullet_list(rules["avoid"]),
            "",
            "## 6. 质量检查清单",
            "",
            "- [ ] 开头两行是否已经出现清晰风险信号或反直觉判断？",
            "- [ ] 是否说明了事件对AI基建、算力、数据中心、能源、芯片或关键矿产的影响？",
            "- [ ] 是否至少包含一个可信证据类型，而不是空泛观点？",
            "- [ ] 是否给出三个商业或投资影响？",
            "- [ ] 是否给出两到三个后续观察信号？",
            "- [ ] 是否避免了泛AI宣传、情绪化判断和未经来源支持的数字？",
            "- [ ] 是否能被目标受众在手机上快速扫读？",
            "- [ ] 结尾问题是否具体到投资、供应链、合规、选址或业务连续性决策？",
            "",
            "## 7. 评分Rubric",
            "",
            "| 维度 | 分值 | 判断标准 |",
            "|---|---:|---|",
            "| 领域相关性 | 25 | 是否紧扣AI基建地缘风险和供应链决策 |",
            "| 决策价值 | 25 | 是否能帮助投资、选址、采购、合规或风控判断 |",
            "| 可信度 | 20 | 是否基于明确来源、事件、报告或可验证信号 |",
            "| 结构清晰度 | 15 | 是否符合决策简报式结构并适合移动端阅读 |",
            "| 互动质量 | 15 | 是否提出高质量决策问题，而非泛泛求评论 |",
            "",
            "低于80分的内容不进入最终LinkedIn帖子交付。",
        ]
    )

    return "\n".join(lines).strip() + "\n"


def render_analysis_prompt() -> str:
    return textwrap.dedent(
        """
        Prompt name: Stage 4 KOL style analysis prompt
        Workflow step: LinkedIn KOL content structure research
        Target model: DeepSeek V4 (`deepseek-v4-pro`) or equivalent reasoning model

        System role:
        You are a content strategist for AI infrastructure geopolitical risk analysis.
        Your task is to analyze professional LinkedIn-style public content patterns
        from selected KOLs and convert them into reusable writing rules.

        Project domain:
        AI infrastructure geopolitical risk and supply-chain decision intelligence.

        Target KOLs:
        1. Chris Miller - chips, semiconductor supply chains, and technology power.
        2. Paul Triolo - technology geopolitics, AI policy, and US-China tech competition.
        3. Gregory C. Allen - AI national security, industrial policy, and export controls.
        4. Jordan Schneider - China technology policy, AI, and semiconductor competition.

        Analysis dimensions:
        - Opening hook: risk signal, key number, counterintuitive judgment, or policy shift.
        - Structure: short paragraphs, logic chain, and mobile readability.
        - Credibility: data, reports, institutional sources, company examples, or policy actions.
        - Interaction: quality of the closing question or discussion prompt.
        - Style: executive/investor decision brief rather than generic news summary.

        Output JSON:
        {
          "kol_name": "Name",
          "focus_area": "One sentence",
          "hook_pattern": "One concise pattern",
          "structure_pattern": "One concise pattern",
          "credibility_pattern": "One concise pattern",
          "interaction_pattern": "One concise pattern",
          "style_pattern": "One concise pattern",
          "transferable_rules": ["rule 1", "rule 2", "rule 3"],
          "limitations": "What not to copy directly"
        }
        """
    ).strip() + "\n"


def render_constraints_prompt() -> str:
    return textwrap.dedent(
        """
        Prompt name: Stage 4 LinkedIn content constraints prompt
        Workflow step: Constraint layer for Stage 5 LinkedIn post generation
        Target model: DeepSeek V4 (`deepseek-v4-pro`) or equivalent reasoning model

        System role:
        You are an AI infrastructure geopolitical risk analyst writing a LinkedIn
        decision brief for investors, data center operators, cloud strategy teams,
        AI chip/supply-chain leaders, and cross-border risk managers.

        Required input:
        - News title
        - Summary
        - Source type and evidence basis
        - Relevance routing rationale
        - Primary category
        - Auxiliary tags

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
        - Use a decision-brief tone: analytical, concrete, and useful for business readers.
        - Include exactly three business implications.
        - Include two or three signals to watch.
        - Include a specific closing question tied to investment, supply chain, compliance,
          site selection, procurement, or business continuity.
        - Add no more than three hashtags.

        Output format:
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


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def upsert_kol_analysis_result(connection: sqlite3.Connection, result: dict[str, Any]) -> None:
    now = utc_now()
    connection.execute(
        """
        INSERT INTO kol_analysis_results (
            kol_name, focus_area, sample_basis, hook_pattern, structure_pattern,
            credibility_pattern, interaction_pattern, style_pattern,
            transferable_rules, limitations, prompt_version, model_provider,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(kol_name) DO UPDATE SET
            focus_area = excluded.focus_area,
            sample_basis = excluded.sample_basis,
            hook_pattern = excluded.hook_pattern,
            structure_pattern = excluded.structure_pattern,
            credibility_pattern = excluded.credibility_pattern,
            interaction_pattern = excluded.interaction_pattern,
            style_pattern = excluded.style_pattern,
            transferable_rules = excluded.transferable_rules,
            limitations = excluded.limitations,
            prompt_version = excluded.prompt_version,
            model_provider = excluded.model_provider,
            updated_at = excluded.updated_at
        """,
        (
            result["kol_name"],
            result["focus_area"],
            result["sample_basis"],
            result["hook_pattern"],
            result["structure_pattern"],
            result["credibility_pattern"],
            result["interaction_pattern"],
            result["style_pattern"],
            json.dumps(result["transferable_rules"], ensure_ascii=False),
            result["limitations"],
            PROMPT_VERSION,
            DEFAULT_LLM_CONFIG["provider"],
            now,
            now,
        ),
    )


def record_run(connection: sqlite3.Connection, stats: KOLAnalysisStats) -> None:
    connection.execute(
        """
        INSERT INTO kol_analysis_runs (
            run_id, started_at, finished_at, profiles_analyzed,
            outputs_written, errors, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            stats.run_id,
            stats.started_at,
            stats.finished_at,
            stats.profiles_analyzed,
            stats.outputs_written,
            stats.errors,
            stats.notes,
        ),
    )


def run_linkedin_analysis(
    db_path: Path,
    checklist_path: Path,
    analysis_prompt_path: Path,
    constraints_prompt_path: Path,
) -> tuple[KOLAnalysisStats, Path]:
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    logger, log_path = setup_logger(run_id)
    stats = KOLAnalysisStats(run_id=run_id, started_at=utc_now())

    logger.info("Starting Stage 4 LinkedIn KOL analysis run: %s", run_id)
    logger.info("KOL profiles configured: %s", len(KOL_PROFILES))
    logger.info(
        "LLM provider placeholder: %s | enabled=%s",
        DEFAULT_LLM_CONFIG["provider"],
        DEFAULT_LLM_CONFIG["enabled"],
    )

    apply_schema(db_path, SQLITE_SCHEMA_PATH)
    generated_at = utc_now()
    results: list[dict[str, Any]] = []

    with sqlite3.connect(db_path) as connection:
        for profile in KOL_PROFILES:
            try:
                result = analyze_profile(profile)
                upsert_kol_analysis_result(connection, result)
                results.append(result)
                stats.profiles_analyzed += 1
                logger.info("ANALYZED | %s", result["kol_name"])
            except Exception as exc:  # noqa: BLE001 - keep stage run resilient.
                stats.errors += 1
                logger.error("Failed to analyze profile=%s: %s", profile.get("name"), exc)

        try:
            write_text(checklist_path, render_checklist(results, run_id, generated_at))
            write_text(analysis_prompt_path, render_analysis_prompt())
            write_text(constraints_prompt_path, render_constraints_prompt())
            stats.outputs_written = 3
            logger.info("WROTE | %s", checklist_path)
            logger.info("WROTE | %s", analysis_prompt_path)
            logger.info("WROTE | %s", constraints_prompt_path)
        except Exception as exc:  # noqa: BLE001 - keep stage run resilient.
            stats.errors += 1
            logger.error("Failed to write Stage 4 outputs: %s", exc)

        stats.finished_at = utc_now()
        stats.notes = (
            "Offline Stage 4 KOL analysis completed. The checklist and constraint "
            "prompt convert representative KOL patterns into a decision-brief "
            "structure for later LinkedIn content generation."
        )
        record_run(connection, stats)

    logger.info(
        "Completed KOL analysis. profiles=%s outputs=%s errors=%s",
        stats.profiles_analyzed,
        stats.outputs_written,
        stats.errors,
    )
    return stats, log_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Stage 4 LinkedIn KOL style analysis.")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DATABASE_PATH,
        help="SQLite database path.",
    )
    parser.add_argument(
        "--checklist-path",
        type=Path,
        default=KOL_STYLE_CHECKLIST_PATH,
        help="Output path for the LinkedIn style checklist.",
    )
    parser.add_argument(
        "--analysis-prompt-path",
        type=Path,
        default=KOL_STYLE_ANALYSIS_PROMPT_PATH,
        help="Output path for the Stage 4 KOL analysis prompt sample.",
    )
    parser.add_argument(
        "--constraints-prompt-path",
        type=Path,
        default=LINKEDIN_CONTENT_CONSTRAINTS_PROMPT_PATH,
        help="Output path for the Stage 5 content constraints prompt.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stats, log_path = run_linkedin_analysis(
        args.db_path,
        args.checklist_path,
        args.analysis_prompt_path,
        args.constraints_prompt_path,
    )
    print("\nStage 4 LinkedIn KOL analysis completed")
    print(f"Run ID: {stats.run_id}")
    print(f"Database: {args.db_path}")
    print(f"Profiles analyzed: {stats.profiles_analyzed}")
    print(f"Outputs written: {stats.outputs_written}")
    print(f"Errors: {stats.errors}")
    print(f"Checklist: {args.checklist_path}")
    print(f"Analysis prompt: {args.analysis_prompt_path}")
    print(f"Constraints prompt: {args.constraints_prompt_path}")
    print(f"Log file: {log_path}")


if __name__ == "__main__":
    main()
