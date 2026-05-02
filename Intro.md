# AI基建地缘风险洞察工作流 作业落地总说明

> 文档用途：本文件为《Homework 2 AI Content Monitoring and Generation Workflow》作业的总体说明，用于快速理解项目方向、工作流架构与交付策略。
> 核心技术栈：Claude Code（代码生成/调试/架构设计）+ DeepSeek V4（摘要、评分、分类、内容生成，默认 `deepseek-v4-pro`）+ MiniMax图片接口预留/离线SVG fallback + SQLite（MVP信息仓库）。
> 战略定位：本项目采用MVP优先策略，不追求一次性覆盖“全产业链、全自动、全信息源”，而是聚焦“AI基建地缘风险”这一更可落地的高价值场景。

---

## 一、作业核心目标与项目改造方向

### 1.1 作业核心目标
设计并落地一套AI驱动的工作流，完成信息监控、相关性路由、分类、KOL风格拆解、LinkedIn内容生成与进度复盘。

### 1.2 本项目的垂直方向
**AI基础设施地缘风险与供应链决策洞察**

项目服务于一个明确决策问题：

> 哪些地缘政治、区域政策、能源约束或关键矿产供应变化，会影响AI基建投资、数据中心布局、供应链成本与跨境业务连续性？

### 1.3 为什么收窄范围
原始设想“AI全产业链地缘政治风险洞察”差异化很强，但范围过大，落地时会遇到三个问题：

1. 信息源过多，短期内难以稳定自动化抓取。
2. 主题过宽，相关性判断容易波动。
3. LinkedIn内容容易变成泛泛新闻总结，而不是高质量决策洞察。

因此，当前版本采用更成熟的MVP策略：

- 主线只保留 **AI算力基础设施地缘风险** 与 **AI关键矿产供应链风险**。
- 芯片出口管制、区域冲突、AI治理保留为辅助标签。
- 信息输入采用 **手动样例数据 + RSS/API预留接口**。
- 内容输出采用 **决策简报式LinkedIn帖子**。

---

## 二、作业6项任务与本项目对应方式

| 作业任务 | 本项目落地方式 |
|----------|----------------|
| 1. 每日AI新闻与信息监控 | 建立混合输入管道：本地样例数据保证可运行，RSS/API接口作为可扩展设计 |
| 2. 相关性路由与领域定义 | 使用“规则过滤 + LLM评分”的双层路由，减少纯LLM判断不稳定 |
| 3. 信息分类 | 两个主线分类 + 三个辅助标签，服务后续内容生成 |
| 4. LinkedIn内容调研 | 拆解Chris Miller、Paul Triolo、Gregory C. Allen、Jordan Schneider的内容结构 |
| 5. LinkedIn内容生成 | 每个主线分类生成1篇决策简报式帖子，含文案、配图Prompt、目标受众和语气定位 |
| 6. 工作流与进度报告 | 输出架构说明、Prompt样例、运行日志、优化记录与最终报告 |

---

## 三、核心工作流架构

```text
样例新闻/RSS配置
    ↓
新闻清洗与摘要
    ↓
第一层规则过滤
    ↓
第二层LLM相关性评分
    ↓
主线分类与辅助标签
    ↓
SQLite信息仓库
    ↓
LinkedIn决策简报生成
    ↓
图片生成与内容归档
    ↓
每日候选内容输出与人工审核
    ↓
运行日志与进度报告
```

---

## 四、模块设计

### 4.1 信息监控模块：`1_news_monitoring.py`
目标是读取本地样例新闻，并预留RSS/API扩展能力。输出结构化新闻数据，并写入SQLite数据库。

### 4.2 相关性路由模块：`2_relevance_router.py`
采用双层路由：

1. 规则过滤：必须同时命中AI基建/供应链信号和地缘/跨境风险信号。
2. LLM评分：按照0-10分打分，≥7分进入下一环节。

### 4.3 信息分类模块：`3_information_classification.py`
将高相关性信息归入两个主线分类：

1. AI算力基础设施地缘风险。
2. AI关键矿产供应链与地缘政治。

同时可附加辅助标签：

- AI芯片出口管制。
- 区域冲突影响。
- 全球AI治理。

### 4.4 KOL分析模块：`4_linkedin_analysis.py`
拆解目标KOL的内容结构，输出《LinkedIn_Post_Style_Anatomy_Checklist.md》，作为内容生成约束。

### 4.5 内容生成模块：`5_linkedin_content_generation.py`
生成两篇LinkedIn帖子，结构采用：

```text
Hook
What happened
Why it matters for AI infrastructure
Business implications
Signals to watch
Closing question
```

### 4.6 总控与报告模块：`0_main_workflow.py`
串联所有模块，记录运行日志，支撑最终进度报告。

### 4.7 图片生成与归档模块：`6_image_generation.py`
为每篇最终LinkedIn内容生成或fallback渲染16:9视觉图，并写入图片目录与按日期归档包。

### 4.8 每日运行与人工审核模块：`7_daily_run_review.py`
包装总控脚本生成 `daily_outputs/YYYY-MM-DD/` 审核包。候选内容默认 `pending_review`，人工审核前不自动发布LinkedIn。

---

## 五、最终交付物标准目录结构

```text
AI_Geopolitical_Risk_Workflow_Homework_Delivery
├── 1-Workflow_Files
│   ├── 0_main_workflow.py
│   ├── 1_news_monitoring.py
│   ├── 2_relevance_router.py
│   ├── 3_information_classification.py
│   ├── 4_linkedin_analysis.py
│   ├── 5_linkedin_content_generation.py
│   ├── 6_image_generation.py
│   ├── 7_daily_run_review.py
│   ├── database_config
│   │   ├── chroma_db_config.py
│   │   └── sqlite_db_init.sql
│   ├── api_config.py
│   └── workflow_architecture.md
├── 2-Prompt_Design_Samples
│   ├── news_summarization_prompt.txt
│   ├── relevance_routing_prompt.txt
│   ├── information_classification_prompt.txt
│   ├── linkedin_content_analysis_prompt.txt
│   ├── linkedin_post_generation_prompt.txt
│   └── image_generation_prompt.txt
├── 3-Final_LinkedIn_Content
│   ├── LinkedIn_Post_Style_Anatomy_Checklist.md
│   ├── Category_1_AI_Infrastructure_Risk_Post.md
│   ├── Category_2_AI_Mineral_SupplyChain_Post.md
│   ├── images
│   └── archive
├── daily_outputs
│   └── YYYY-MM-DD
│       ├── review_queue.md
│       ├── review_queue.csv
│       ├── manifest.json
│       ├── candidates
│       └── assets
└── 4-Progress_Report
    ├── Progress_Report_Final.md
    ├── workflow_running_logs
    ├── stage_12_daily_review_notes.md
    └── prompt_optimization_records.md
```

---

## 六、核心优化记录

本项目完成了一次关键战略优化：

| 原设想 | 当前版本 |
|--------|----------|
| AI全产业链地缘政治风险洞察 | AI基建地缘风险与供应链决策洞察 |
| 覆盖5大分类 | 2个主线分类 + 3个辅助标签 |
| 每日全自动抓取全球信息源 | MVP混合输入：样例数据 + RSS/API预留 |
| 完全依赖LLM相关性判断 | 规则过滤 + LLM评分 |
| 生成普通LinkedIn文章 | 生成决策简报式LinkedIn帖子 |

这个调整让项目更适合作业交付：范围更清楚，流程更可运行，评分逻辑更可解释，最终内容也更像面向投资者和企业负责人的专业洞察。
