# 项目状态同步

## 项目概述

**项目名称：** AI基建地缘风险洞察工作流  
**核心定位：** AI基础设施 + 地缘政治 + 供应链/投资决策  
**人设：** AI基建地缘风险洞察分析师 | 信息管理与信息系统专业  
**当前战略版本：** v3.0，已从“AI全产业链全自动内容系统”收窄为“AI基建地缘风险MVP工作流”

---

## 当前进度总览

| 阶段 | 名称 | 状态 |
|------|------|------|
| 阶段一 | 核心定位收窄 | ✅ 已完成 |
| 阶段二 | MVP信息监控管道 | ✅ 已完成，已测试通过 |
| 阶段三 | 双层路由与分类引擎 | ✅ 已完成，待用户测试 |
| 阶段四 | KOL分析与风格指南 | 🔄 待启动 |
| 阶段五 | LinkedIn决策简报生成 | 🔄 待启动 |
| 阶段六 | 最终文档与交付整理 | 🔄 待启动 |

---

## 新会话启动Prompt

> 用途：当关闭当前AI窗口、重新打开新窗口继续项目时，把下面这段Prompt发给新的AI。新的AI应先读取本文件，再按当前阶段继续执行。

```text
你现在接手我的 Homework2 项目，请先完整读取并理解当前项目状态。

项目目录：
/Users/jing/Desktop/some_code/GenAI_Coding/Homework2

请按以下顺序读取文件：
1. STATUS.md：这是当前项目状态、阶段进度和下一步行动的最高优先级入口。
2. Implementation_Roadmap.md：这是项目战略路线图和全局根规则。
3. Plan_of_Project.md：这是详细落地执行方案，所有代码、Prompt和交付物都应与它保持一致。
4. Progress_Report.md：这是对话记录、Prompt记录和后续进度报告素材。
5. Homework2.md：这是作业要求原文，只用于核对交付要求，不要随意修改。

当前项目定位：
本项目是“AI基建地缘风险洞察工作流”，不是泛AI新闻系统，也不是全自动媒体平台。核心目标是为AI基建投资者、数据中心运营商、跨国AI企业战略/供应链/风控负责人，构建一个可运行、可解释、可复盘的MVP工作流。

当前有效技术路线：
样例新闻/RSS预留配置
-> 新闻清洗与摘要
-> 规则过滤
-> LLM相关性评分
-> 主线分类与辅助标签
-> SQLite存储
-> LinkedIn决策简报式内容生成
-> 运行日志与最终进度报告

必须遵守的实现原则：
1. 先保证MVP可运行，不要扩展成过大的平台。
2. 使用本地样例数据保证无网络环境也能演示；RSS/API只作为可扩展接口预留。
3. 规则过滤要工程化，建议采用 keywords / required_terms / exclude_terms 三类配置，而不是简单关键词散列表。
4. 不做自动LinkedIn发布，不接LinkedIn OAuth，不做浏览器自动发帖；本作业只交付LinkedIn帖子正文、目标受众、语气定位和配图Prompt。
5. 模型供应商和具体LLM调用方式由用户后续决定；代码设计时保留清晰接口即可。
6. SQLite作为MVP信息仓库，Chroma只作为未来扩展方向，不要在MVP阶段强行加入。
7. 每完成一个阶段，必须更新STATUS.md中的阶段状态、已完成事项和下一步行动，并把关键Prompt或优化记录追加到Progress_Report.md。

请先告诉我你读完后理解到的当前状态，再根据STATUS.md里的“下一步行动”继续工作。
```

---

## 最新技术路线确认

- 已确认采用更工程化的规则过滤配置：`keywords`、`required_terms`、`exclude_terms`。
- 已确认本次作业不做自动LinkedIn发布，只生成LinkedIn内容正文、目标受众、语气定位和配图Prompt。
- LLM模型与具体API接入方式由用户后续自行决定，本项目代码层面只保留清晰接口。
- 阶段三已采用离线可复现实现：默认全量重跑并覆盖结果表，`--only-new` 可用于只处理新增记录。

---

## 已完成

### 1. 架构文件
- [x] `Implementation_Roadmap.md` - 已更新为v3.0战略路线图。
- [x] `Plan_of_Project.md` - 已更新为AI基建地缘风险MVP执行方案。
- [x] `Progress_Report.md` - 对话记录 + Prompt库，需持续追加。
- [x] `STATUS.md` - 本文件，作为每次重新打开项目时的快速同步入口。

### 2. 阶段二：MVP信息监控管道
- [x] 已创建最终交付目录结构：`AI_Geopolitical_Risk_Workflow_Homework_Delivery/`。
- [x] 已编写 `1-Workflow_Files/1_news_monitoring.py`。
- [x] 已提供本地样例新闻数据：`1-Workflow_Files/sample_data/sample_news.json`。
- [x] 已提供RSS/API预留配置：`1-Workflow_Files/sample_data/rss_sources.json`。
- [x] 已提供SQLite初始化脚本：`1-Workflow_Files/database_config/sqlite_db_init.sql`。
- [x] 已提供阶段二新闻摘要Prompt样例：`2-Prompt_Design_Samples/news_summarization_prompt.txt`。
- [x] **已通过用户测试**（2026-04-30 20:04）：读取6条样例，写入SQLite 6条，去重逻辑正常，错误0条。

### 3. 阶段三：双层路由与分类引擎
- [x] 已编写 `1-Workflow_Files/2_relevance_router.py`。
- [x] 已编写 `1-Workflow_Files/3_information_classification.py`。
- [x] 已扩展SQLite schema，新增 `relevance_routing_results`、`routing_runs`、`classification_results`、`classification_runs`。
- [x] 已提供阶段三Prompt样例：
  - `2-Prompt_Design_Samples/relevance_routing_prompt.txt`
  - `2-Prompt_Design_Samples/information_classification_prompt.txt`
- [x] 已实现工程化规则配置：`keywords`、`required_terms`、`exclude_terms`。
- [x] 已实现离线语义评分占位逻辑，保持后续接入Minimax M2.7的接口边界。
- [x] 已完成本地验证：6条样例中4条保留、2条过滤；4条保留内容全部完成主线分类与辅助标签分配。

### 4. 核心定位（已收窄）
- [x] **垂直领域：** AI基础设施地缘风险与供应链决策洞察。
- [x] **主目标受众：** AI基建投资者、跨国AI企业战略/供应链/风控负责人。
- [x] **主线分类：** 分类1 AI算力基础设施地缘风险；分类2 AI关键矿产供应链与地缘政治。
- [x] **辅助标签：** AI芯片出口管制、区域冲突影响、全球AI治理。
- [x] **核心判断问题：** 这条信息是否影响AI基建投资、数据中心布局、供应链成本或跨境风险决策？

### 5. 相关性打分标准
采用“双层路由”：

| 层级 | 作用 |
|------|------|
| 第一层：规则过滤 | 必须同时命中AI基建/供应链信号 + 地缘/跨境风险信号 |
| 第二层：LLM评分 | 对通过规则过滤的内容做0-10分语义评分，≥7分保留 |

LLM评分权重：

| 权重 | 标准 |
|------|------|
| 40% | 影响AI基建投资、数据中心布局、供应链成本或跨境业务连续性 |
| 25% | 有真实事件、数据、报告或案例支撑 |
| 20% | 匹配主目标受众的决策需求 |
| 15% | 涉及算力基础设施、关键矿产、能源、电力、芯片供应链等核心环节 |

### 6. 信息源体系
当前版本采用MVP策略：

| 输入类型 | 用途 |
|------|------|
| 手动样例数据 | 保证无网络环境下可运行、可演示、可复现 |
| RSS/API预留接口 | 展示未来每日自动化监控能力 |
| 公开报告/企业公告 | 提供高可信背景材料 |

优先来源包括：Microsoft、Google、NVIDIA、OpenAI、IEA、USGS、CSIS、RAND、Reuters、FT、MIT Technology Review、a16z、Sequoia、Goldman Sachs、McKinsey、BCG。

---

## 下一步行动

### 立即执行（用户测试阶段三）
1. 如需从头确认阶段二数据仍在，可先运行：
   ```bash
   python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/1_news_monitoring.py
   ```
   如果看到 `Inserted: 0`、`Duplicates skipped: 6`，这是正常去重结果。

2. 运行阶段三A：双层相关性路由。
   ```bash
   python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/2_relevance_router.py
   ```
   预期结果：`Items seen: 6`、`Routed: 6`、`Kept: 4`、`Filtered: 2`、`Errors: 0`。

3. 运行阶段三B：信息分类。
   ```bash
   python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/3_information_classification.py
   ```
   预期结果：`Items seen: 4`、`Classified: 4`、`Errors: 0`。

4. 检查SQLite数据库：
   - 数据库路径：`AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/ai_geopolitical_risk_workflow.sqlite3`
   - 阶段二核心表：`news_items`、`source_registry`、`ingestion_runs`
   - 阶段三核心表：`relevance_routing_results`、`routing_runs`、`classification_results`、`classification_runs`
5. 检查运行日志：
   - 日志目录：`AI_Geopolitical_Risk_Workflow_Homework_Delivery/4-Progress_Report/workflow_running_logs/`

### 阶段三测试交接注意
- 阶段三脚本已经由AI运行过，数据库中已有路由与分类结果。
- 默认直接运行脚本会全量重算并覆盖结果表，因此仍会看到6条路由、4条分类，便于用户测试。
- 如果只想处理新增记录，可追加 `--only-new`；在当前数据库状态下会看到0条新增处理。
- 判断阶段三是否正常时，请同时检查：
  - 命令是否成功退出；
  - 两个脚本的 `Errors` 是否都为0；
  - `relevance_routing_results` 中应有6条结果，其中4条 `decision='keep'`、2条 `decision='filter'`；
  - `classification_results` 中应有4条结果；
  - `routing_runs` 与 `classification_runs` 应新增运行记录。

### 测试通过后执行
6. KOL内容拆解 → `4_linkedin_analysis.py` + `LinkedIn_Post_Style_Anatomy_Checklist.md`
7. 生成LinkedIn决策简报 → `5_linkedin_content_generation.py`
8. 整理最终文档 → `0_main_workflow.py` + `Progress_Report_Final.md`

---

## 文件清单

| 文件名 | 用途 | 状态 |
|--------|------|------|
| `Homework2.md` | 作业要求原文 | 保留不改 |
| `Plan_of_Project.md` | 详细执行方案 | ✅ 已更新v3.0 |
| `Implementation_Roadmap.md` | 战略路线图 | ✅ 已更新v3.0 |
| `Progress_Report.md` | 对话记录 + Prompt库 | ✅ 已追加战略调整记录 |
| `STATUS.md` | 本文件 - 状态同步 | ✅ 已更新 |
| `Intro.md` | 作业落地总说明 | ✅ 已同步更新 |
| `AI_Geopolitical_Risk_Workflow_Homework_Delivery/` | 最终作业交付目录 | ✅ 已创建 |
| `1_news_monitoring.py` | 阶段二MVP信息监控脚本 | ✅ 已完成，已测试通过 |
| `2_relevance_router.py` | 阶段三A双层相关性路由脚本 | ✅ 已完成，待用户测试 |
| `3_information_classification.py` | 阶段三B信息分类脚本 | ✅ 已完成，待用户测试 |
| `relevance_routing_prompt.txt` | 阶段三A相关性评分Prompt样例 | ✅ 已完成 |
| `information_classification_prompt.txt` | 阶段三B分类Prompt样例 | ✅ 已完成 |

---

## 交付物目标

```text
AI_Geopolitical_Risk_Workflow_Homework_Delivery
├── 1-Workflow_Files/        # 6个Python脚本 + 配置
├── 2-Prompt_Design_Samples/ # 各环节Prompt
├── 3-Final_LinkedIn_Content/ # 2篇帖子 + 风格清单
└── 4-Progress_Report/        # 最终进度报告
```

---

*最后更新：2026-04-30*  
*依据：Implementation_Roadmap.md v3.0 与 Plan_of_Project.md v3.0*
