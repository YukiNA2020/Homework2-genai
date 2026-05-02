# AI Geopolitical Risk Workflow — Homework 2
# AI地缘风险监测与内容生成工作流 — 作业2

---

## Personal Information

JingyangFeng1155242429

---

## Project Overview | 项目概述

This project is an academic assignment implementing an **AI-powered geopolitical risk monitoring and content generation pipeline** focused on AI infrastructure and critical mineral supply chains. It demonstrates an end-to-end agentic workflow covering news ingestion, relevance routing, classification, KOL analysis, LinkedIn content generation, image generation, and human review.

本项目是一门课程的学术作业，实现了一个**AI驱动的地缘风险监测与内容生成流水线**，聚焦于AI算力基础设施和关键矿产供应链领域。整体工作流涵盖了：新闻采集、相关性路由、信息分类、KOL分析、LinkedIn内容生成、图片生成以及人工审核全流程。

---

## Project Structure | 项目结构

```
Homework2/
├── Homework2.md                          # Assignment description | 作业说明
│
├── AI_Geopolitical_Risk_Workflow_Homework_Delivery/
│   ├── 1-Workflow_Files/                # Core workflow code | 核心工作流代码
│   │   ├── 0_main_workflow.py            # Main orchestrator | 主协调器
│   │   ├── 1_news_monitoring.py          # Stage 2: RSS/news ingestion | 新闻采集
│   │   ├── 2_relevance_router.py         # Stage 3A: relevance filtering | 相关性过滤
│   │   ├── 3_information_classification.py # Stage 3B: categorization | 分类
│   │   ├── 4_linkedin_analysis.py        # Stage 4: KOL style analysis | KOL风格分析
│   │   ├── 5_linkedin_content_generation.py # Stage 5: post generation | 内容生成
│   │   ├── 6_image_generation.py         # Stage 11: image generation | 图片生成
│   │   ├── 7_daily_run_review.py         # Stage 12: daily review | 每日审核
│   │   ├── llm_client.py                 # Unified LLM client | LLM客户端
│   │   ├── lineage_utils.py              # Data lineage tracking | 数据溯源
│   │   ├── api_config.py                 # Configuration | 配置
│   │   ├── ai_geopolitical_risk_workflow.sqlite3 # Database | 数据库
│   │   └── sample_data/                  # Sample news for offline testing | 离线测试样例
│   │
│   ├── 2-Prompt_Design_Samples/         # All prompt templates | 提示词模板
│   │
│   ├── 3-Final_LinkedIn_Content/        # Final generated content | 最终生成内容
│   │   ├── LinkedIn_Post_Style_Anatomy_Checklist.md
│   │   ├── Category_1_AI_Infrastructure_Risk_Post.md
│   │   └── Category_2_AI_Mineral_SupplyChain_Post.md
│   │
│   ├── 4-Progress_Report/                # Development logs | 开发进度记录
│   │
│   └── daily_outputs/                    # Daily run outputs | 每日运行输出
│
└── result/                               # Output archives | 输出归档
    └── {YYYY-MM-DD}/                      # Date-organized runs | 按日期组织的运行
        └── run_XXX_{run_name}/            # Sequential run folders | 顺序命名的运行文件夹
            ├── assets/                     # Generated images | 生成的图片
            ├── candidates/                # Content candidates | 内容候选
            ├── manifest.json             # Run manifest | 运行清单
            ├── review_queue.md           # Human review queue | 人工审核队列
            └── review_queue.csv          # Review queue (CSV) | 审核队列(CSV)
```

---

## Workflow Pipeline | 工作流流水线

```
Stage 2: News Monitoring (RSS ingestion / local sample)
    ↓
Stage 3A: Relevance Routing (rule gate + semantic scoring, threshold ≥ 7)
    ↓
Stage 3B: Information Classification (2 main categories + auxiliary tags)
    ↓
Stage 4: KOL Analysis (reverse-engineer LinkedIn style from 4 thought leaders)
    ↓
Stage 5: LinkedIn Content Generation (decision brief posts)
    ↓
Stage 11: Image Generation + Content Archiving
    ↓
Stage 12: Daily Run Review + Human Review Queue
    ↓
Stage 13: Data Lineage (provenance tracking)
    ↓
Stage 14: Evidence Grounding (factual validation of generated content)
```

---

## Quick Start | 快速开始

### Prerequisites | 环境要求

- **Python 3.10+**
- **SQLite3** (built into Python standard library)
- No external pip packages required for core functionality

### Agent Run Prompt | Agent运行提示词

If you are an AI agent (e.g., Claude Code) tasked with running this project, use the following prompt as a template:

---

**For the AI Agent | 给AI Agent的提示词：**
可以直接用Claude Code等AGENT来运行本项目

```
请帮我运行这个AI地缘风险监测与内容生成工作流项目。

项目位置：Homework2/AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files

运行要求：
1. 进入项目目录：cd Homework2/AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files
2. 运行主工作流（在线模式，使用LLM API）：
   python 0_main_workflow.py --llm-mode online --include-stage11
3. 将本次运行结果输出到 result/{日期}/{本次运行名称}/ 文件夹下
   - 日期格式：YYYY-MM-DD（例如：2026-05-02）
   - 运行名称：由你根据本次运行的配置和目的自动生成一个简洁的英文名称
   - 例如：result/2026-05-02/run_001_online_full_run/
   - 确保生成对应的 assets/ 和 candidates/ 子文件夹，以及 manifest.json、review_queue.md、review_queue.csv
4. 运行完成后，报告本次运行的阶段数量、处理的信息条目数、生成的LinkedIn内容数量等关键统计信息

API密钥配置（如尚未配置）：
   - DeepSeek API：用于LLM增强的语义评分、内容生成等阶段
   - MiniMax API：用于图片生成阶段
   - 配置方式：复制 .env.example 为 .env，填入API密钥

运行模式说明：
   - --llm-mode offline：纯离线模式，使用规则和样例数据，无需API，为本项目的省钱测试形态
   - --llm-mode online --include-stage11：在线模式，使用真实LLM API并生成图片，为本项目的核心形态

如果你需要运行单个阶段，请依次运行以下阶段脚本：
python 1_news_monitoring.py          # Stage 2: 新闻采集
python 2_relevance_router.py         # Stage 3A: 相关性路由
python 3_information_classification.py  # Stage 3B: 信息分类
python 4_linkedin_analysis.py        # Stage 4: KOL风格分析
python 5_linkedin_content_generation.py  # Stage 5: LinkedIn内容生成
python 6_image_generation.py        # Stage 11: 图片生成
python 7_daily_run_review.py        # Stage 12: 每日审核
```

---

### Running the Workflow | 运行工作流

#### Option 1: Offline Mode (No API Keys Required) | 离线模式（无需API密钥）

```bash
cd AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files
python 0_main_workflow.py --llm-mode offline
```

This uses built-in sample news and deterministic fallbacks.

#### Option 2: Online Mode (With API Keys) | 在线模式（需要API密钥）

1. Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Edit `.env`:
```
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_API_ENDPOINT=https://api.deepseek.com/v1
MINIMAX_API_KEY=your_minimax_api_key
```

2. Run with online mode:

```bash
python 0_main_workflow.py --llm-mode online --include-stage11
```

#### Run Individual Stages | 运行单个阶段

```bash
python 1_news_monitoring.py          # Stage 2
python 2_relevance_router.py         # Stage 3A
python 3_information_classification.py  # Stage 3B
python 4_linkedin_analysis.py       # Stage 4
python 5_linkedin_content_generation.py  # Stage 5
python 6_image_generation.py        # Stage 11
python 7_daily_run_review.py        # Stage 12
```

---

## Key Features | 关键特性

### 1. Multi-Stage Agentic Pipeline | 多阶段智能代理流水线

14 stages covering the full lifecycle from raw news to reviewed content. Each stage can run independently and has a clear single responsibility.

14个阶段覆盖从原始新闻到审核后内容的完整生命周期。每个阶段可独立运行，职责清晰。

### 2. Dual-Layer Relevance Routing | 双层相关性路由

Combines rule-based filtering (must match AI infrastructure signals AND geopolitical signals) with semantic scoring (0-10 across 4 dimensions) for robust and explainable routing decisions.

结合基于规则的过滤（必须同时匹配AI基础设施信号和地缘政治信号）与语义评分（4个维度0-10分），实现稳健且可解释的路由决策。

### 3. Two-Track Classification System | 双轨分类系统

- **Primary category**: One of two main tracks (AI Infrastructure Risk / AI Critical Mineral Supply Chain)
- **Auxiliary tags**: Additional context tags (Export Controls, Regional Conflicts, Global AI Governance)

- **主类别**：两个主要轨道之一（AI算力基础设施风险 / AI关键矿产供应链）
- **辅助标签**：额外上下文标签（出口管制、区域冲突、全球AI治理）

### 4. KOL-Driven Style Learning | KOL驱动风格学习

Reverse-engineers LinkedIn content style from 4 real thought leaders in AI geopolitics (Chris Miller, Paul Triolo, Gregory C. Allen, Jordan Schneider) to generate authentic professional content.

从4位AI地缘政治领域的真实思想领袖（Chris Miller, Paul Triolo, Gregory C. Allen, Jordan Schneider）的LinkedIn内容中逆向工程LinkedIn风格，生成真实的职业内容。

### 5. Evidence Grounding | 证据验证

Stage 14 validates that generated content claims are supported by source evidence, preventing hallucination and maintaining factual accuracy.

第14阶段验证生成内容的声明是否有源证据支持，防止幻觉并保持事实准确性。

### 6. Human Review Gate | 人工审核门控

All generated content goes into a pending review queue by default. No auto-publishing — every piece requires human review before external distribution.

所有生成内容默认进入待审核队列。无自动发布——每条内容在外部分发前都需要人工审核。

---

## Generated Output Examples | 生成输出示例

### Category 1: AI Infrastructure Geopolitical Risk Post

Topic: AI data center expansion raising electricity demand and grid planning risk

Structure:
- Hook → What happened → Why it matters → Business implications (3) → Signals to watch (2-3) → Closing decision question

### Category 2: AI Critical Mineral Supply Chain Post

Topic: Copper supply concentration creating cost risk for AI infrastructure buildout

Structure:
- Same decision brief format with domain-specific content

---

## Result Folder Structure | 结果文件夹结构

```
result/                                    # Top level: by date | 顶级：按日期
└── {YYYY-MM-DD}/                         # Date folder (e.g., 2026-05-02)
    └── run_XXX_{run_name}/              # Run folder: run counter + custom name
        ├── assets/                       # Generated images
        ├── candidates/                  # LinkedIn post candidates (pending review)
        ├── manifest.json                # Run metadata and statistics
        ├── review_queue.md              # Human review queue (Markdown)
        └── review_queue.csv             # Human review queue (CSV)

Example:
result/
└── 2026-05-02/
    ├── run_001_initial/                 # Initial offline baseline run
    ├── run_002_full_online_all/         # Full online run with all stages
    ├── run_003_llm_fallback_test/       # Test LLM fallback behavior
    └── run_004_with_images/             # Run with image generation enabled
```

---

## Database Schema | 数据库架构

The SQLite database tracks:
- Source registry and news items | 来源注册和新闻条目
- Stage run metadata | 阶段运行元数据
- Relevance routing decisions with scoring breakdown | 带评分细分的相关性路由决策
- Classification results | 分类结果
- Generated LinkedIn content with quality scores | 带质量评分的LinkedIn生成内容
- Image generation results | 图片生成结果
- Daily review queue | 每日审核队列
- Data lineage for audit trail | 用于审计追踪的数据溯源

---

## Dependencies | 依赖项

| Dependency | Required | Purpose |
|------------|----------|---------|
| Python 3.10+ | Yes | Runtime |
| SQLite3 | Yes (built-in) | Database |
| DeepSeek API | Optional | LLM for Stages 3A, 3B, 5 |
| MiniMax API | Optional | Image generation in Stage 11 |

**Note**: Core workflow runs entirely offline without any API keys.

**注意**：核心工作流无需任何API密钥即可完全离线运行。

---

## Troubleshooting | 故障排查

### "No module named 'llm_client'"
Make sure you are running from the `1-Workflow_Files/` directory.

### Database locked errors
Close any SQLite GUI tools accessing the database, then retry.

### API errors in online mode
Check that your `.env` file has correct API keys and endpoints. Falls back to offline mode automatically if APIs are unreachable.

### Empty review queue
Check that Stage 3A relevance threshold (≥ 7.0) is not filtering out all items. Run with sample data first to verify pipeline flow.

---

## Background| 背景

This is a project demonstrating:
- Agentic workflow design | 智能代理工作流设计
- Multi-stage pipeline orchestration | 多阶段流水线编排
- Prompt engineering for domain-specific generation | 领域特定生成的提示词工程
- Offline-first architecture with intelligent fallback | 离线优先架构与智能降级
- Data lineage and provenance tracking | 数据溯源追踪
- Human-in-the-loop review systems | 人在环审核系统

The project focuses on a specific vertical domain: **AI infrastructure geopolitical risk and critical mineral supply chain decision intelligence**.

本项目展示了：
- 智能代理工作流设计
- 多阶段流水线编排
- 领域特定生成的提示词工程
- 离线优先架构与智能降级
- 数据溯源追踪
- 人在环审核系统

项目聚焦于特定垂直领域：**AI算力基础设施地缘风险与关键矿产供应链决策智能**。
