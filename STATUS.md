# 项目状态同步

## 项目概述

**项目名称：** AI基建地缘风险洞察工作流  
**核心定位：** AI基础设施 + 地缘政治 + 供应链/投资决策  
**人设：** AI基建地缘风险洞察分析师 | 信息管理与信息系统专业  
**当前战略版本：** v3.0稳定MVP已完成，并已完成阶段七冻结验证；v4.0升级路线下一步进入真实新闻/RSS接入。

---

## 当前进度总览

| 阶段 | 名称 | 状态 |
|------|------|------|
| 阶段一 | 核心定位收窄 | ✅ 已完成 |
| 阶段二 | MVP信息监控管道 | ✅ 已完成，已测试通过 |
| 阶段三 | 双层路由与分类引擎 | ✅ 已完成，AI本地验证通过 |
| 阶段四 | KOL分析与风格指南 | ✅ 已完成，通过 |
| 阶段五 | LinkedIn决策简报生成 | ✅ 已完成，AI本地验证通过 |
| 阶段六 | 最终文档与交付整理 | ✅ 已完成，AI本地验证通过 |
| 阶段七 | 稳定MVP冻结与升级保护 | ✅ 已完成，冻结基线已验证 |
| 阶段八 | 真实新闻/RSS接入 | 🔜 下一步 |
| 阶段九 | LLM客户端与API配置 | ⏳ 待启动 |
| 阶段十 | LLM替换摘要、评分、分类与生成 | ⏳ 待启动 |
| 阶段十一 | 图片生成与内容归档 | ⏳ 待启动 |
| 阶段十二 | 每日定时运行与人工审核 | ⏳ 待启动 |
| 阶段十三 | 向量库、看板、邮件简报等可选增强 | ⏳ 后续可选 |

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
- 阶段四已采用离线可复现KOL画像拆解：生成风格清单、KOL分析Prompt、内容生成约束Prompt，并写入SQLite审计表。
- 阶段五已采用离线可复现内容生成：从SQLite分类结果中按两条主线各生成1篇LinkedIn决策简报、配图Prompt、目标受众与语气定位，并写入SQLite审计表。
- 阶段六已完成交付收口：新增一键总控脚本、工作流架构说明、Prompt优化记录与最终进度报告，并提供全流程测试入口。
- 阶段七已完成稳定MVP冻结验证：2026-05-01重新运行总控脚本，`Overall success: True`，阶段二到阶段五全部OK，数据库健康检查全部PASS。
- 后续阶段八以后新增联网、LLM或图片生成能力时，必须保留当前离线fallback，确保无网络、无API key时仍可运行当前MVP。

---

## 已完成

### 1. 架构文件
- [x] `Implementation_Roadmap.md` - 已更新为v3.0稳定MVP路线图，并追加v4.0阶段七以后升级路线。
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

### 4. 阶段四：KOL分析与风格指南
- [x] 已编写 `1-Workflow_Files/4_linkedin_analysis.py`。
- [x] 已扩展SQLite schema，新增 `kol_analysis_results`、`kol_analysis_runs`。
- [x] 已拆解4位对标KOL：Chris Miller、Paul Triolo、Gregory C. Allen、Jordan Schneider。
- [x] 已输出风格清单：`3-Final_LinkedIn_Content/LinkedIn_Post_Style_Anatomy_Checklist.md`。
- [x] 已输出阶段四Prompt样例：`2-Prompt_Design_Samples/kol_style_analysis_prompt.txt`。
- [x] 已输出后续内容生成约束Prompt：`2-Prompt_Design_Samples/linkedin_content_constraints_prompt.txt`。
- [x] 已完成本地验证：4位KOL画像写入SQLite，3个文件输出成功，错误0条。

### 5. 阶段五：LinkedIn决策简报生成
- [x] 已编写 `1-Workflow_Files/5_linkedin_content_generation.py`。
- [x] 已扩展SQLite schema，新增 `linkedin_content_results`、`linkedin_content_runs`。
- [x] 已生成两篇最终LinkedIn内容：
  - `3-Final_LinkedIn_Content/Category_1_AI_Infrastructure_Risk_Post.md`
  - `3-Final_LinkedIn_Content/Category_2_AI_Mineral_SupplyChain_Post.md`
- [x] 每篇内容均包含正文、目标受众、语气定位、来源证据、配图Prompt与质量自检。
- [x] 已输出阶段五Prompt样例：
  - `2-Prompt_Design_Samples/linkedin_post_generation_prompt.txt`
  - `2-Prompt_Design_Samples/image_generation_prompt.txt`
- [x] 已完成本地验证：2个分类、2篇帖子、4个输出文件、错误0条。

### 6. 阶段六：最终文档与交付整理
- [x] 已编写 `1-Workflow_Files/0_main_workflow.py`，可一键运行阶段二到阶段五。
- [x] 已输出工作流架构说明：`1-Workflow_Files/workflow_architecture.md`。
- [x] 已输出最终进度报告：`4-Progress_Report/Progress_Report_Final.md`。
- [x] 已输出Prompt优化记录：`4-Progress_Report/prompt_optimization_records.md`。
- [x] 总控脚本包含主控日志、阶段状态汇总与数据库健康检查。
- [x] 已完成AI本地验证：阶段二到阶段五全部OK，数据库健康检查全部PASS。

### 7. 阶段七：稳定MVP冻结与升级保护
- [x] 已重新运行阶段六总控脚本，确认当前稳定基线。
- [x] 本次冻结基线Run ID：`run_20260501_221718_d3a32586`。
- [x] 主控日志：`AI_Geopolitical_Risk_Workflow_Homework_Delivery/4-Progress_Report/workflow_running_logs/run_20260501_221718_d3a32586_main_workflow.log`。
- [x] 验证结果：`Overall success: True`；阶段二到阶段五均为`OK`；数据库健康检查全部`PASS`。
- [x] 已记录阶段七冻结说明：`AI_Geopolitical_Risk_Workflow_Homework_Delivery/4-Progress_Report/stage_7_mvp_freeze_baseline.md`。
- [x] 已明确升级保护规则：后续新增RSS、LLM或图片生成能力时，必须保留本地样例/离线逻辑作为fallback。

### 8. 核心定位（已收窄）
- [x] **垂直领域：** AI基础设施地缘风险与供应链决策洞察。
- [x] **主目标受众：** AI基建投资者、跨国AI企业战略/供应链/风控负责人。
- [x] **主线分类：** 分类1 AI算力基础设施地缘风险；分类2 AI关键矿产供应链与地缘政治。
- [x] **辅助标签：** AI芯片出口管制、区域冲突影响、全球AI治理。
- [x] **核心判断问题：** 这条信息是否影响AI基建投资、数据中心布局、供应链成本或跨境风险决策？

### 9. 相关性打分标准
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

### 10. 信息源体系
当前版本采用MVP策略：

| 输入类型 | 用途 |
|------|------|
| 手动样例数据 | 保证无网络环境下可运行、可演示、可复现 |
| RSS/API预留接口 | 展示未来每日自动化监控能力 |
| 公开报告/企业公告 | 提供高可信背景材料 |

优先来源包括：Microsoft、Google、NVIDIA、OpenAI、IEA、USGS、CSIS、RAND、Reuters、FT、MIT Technology Review、a16z、Sequoia、Goldman Sachs、McKinsey、BCG。

---

## 下一步行动

### 阶段七完成记录：稳定MVP冻结与升级保护

阶段七已完成。当前离线MVP已经作为稳定基线冻结，后续阶段不得破坏以下能力：

1. 在不配置API key、不联网的情况下，仍可运行：
   ```bash
   python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/0_main_workflow.py
   ```
2. 阶段七冻结验证结果：
   - Run ID：`run_20260501_221718_d3a32586`
   - `Overall success: True`
   - 阶段二到阶段五均显示 `OK`
   - 数据库健康检查全部 `PASS`
   - 主控日志：`AI_Geopolitical_Risk_Workflow_Homework_Delivery/4-Progress_Report/workflow_running_logs/run_20260501_221718_d3a32586_main_workflow.log`
3. 后续新增联网、LLM或图片生成能力时，必须保留离线fallback，保证没有网络、没有API key时仍能运行当前MVP。

### 阶段八预告：真实新闻/RSS接入

阶段八是下一步。第一批具体任务：

1. 扩展 `sample_data/rss_sources.json`，加入3-5个真实、稳定、公开可访问的RSS源。
2. 升级 `1_news_monitoring.py`，新增 `--input-mode rss`。
3. 抓取真实RSS后写入现有 `news_items` 表，不改变下游数据库结构。
4. 保留 `--input-mode local_sample`，作为无网络环境下的演示和测试入口。

### 阶段九预告：LLM客户端与API配置

阶段九要做的第一批具体任务：

1. 新增 `1-Workflow_Files/llm_client.py`，统一封装Minimax M2.7或其他LLM调用。
2. 新增 `.env.example`，列出 `MINIMAX_API_KEY`、`MINIMAX_API_ENDPOINT`、`LLM_PROVIDER`、`LLM_MODEL` 等配置。
3. 先用一个最小Prompt测试API是否能返回结构化JSON，再替换摘要、评分、分类和内容生成逻辑。

---

## 文件清单

| 文件名 | 用途 | 状态 |
|--------|------|------|
| `Homework2.md` | 作业要求原文 | 保留不改 |
| `Plan_of_Project.md` | 详细执行方案 | ✅ 已更新v3.0 |
| `Implementation_Roadmap.md` | 战略路线图 | ✅ 已更新v3.0/v4.0 |
| `Progress_Report.md` | 对话记录 + Prompt库 | ✅ 已追加阶段七升级路线记录 |
| `STATUS.md` | 本文件 - 状态同步 | ✅ 已更新 |
| `Intro.md` | 作业落地总说明 | ✅ 已同步更新 |
| `AI_Geopolitical_Risk_Workflow_Homework_Delivery/` | 最终作业交付目录 | ✅ 已创建 |
| `1_news_monitoring.py` | 阶段二MVP信息监控脚本 | ✅ 已完成，已测试通过 |
| `2_relevance_router.py` | 阶段三A双层相关性路由脚本 | ✅ 已完成，AI本地验证通过 |
| `3_information_classification.py` | 阶段三B信息分类脚本 | ✅ 已完成，AI本地验证通过 |
| `4_linkedin_analysis.py` | 阶段四KOL分析与风格指南脚本 | ✅ 已完成，通过 |
| `5_linkedin_content_generation.py` | 阶段五LinkedIn决策简报生成脚本 | ✅ 已完成，AI本地验证通过 |
| `0_main_workflow.py` | 阶段六全流程总控脚本 | ✅ 已完成，AI本地验证通过 |
| `workflow_architecture.md` | 工作流架构说明 | ✅ 已完成 |
| `Progress_Report_Final.md` | 最终进度报告 | ✅ 已完成 |
| `prompt_optimization_records.md` | Prompt优化记录 | ✅ 已完成 |
| `stage_7_mvp_freeze_baseline.md` | 阶段七冻结基线记录 | ✅ 已完成 |
| `relevance_routing_prompt.txt` | 阶段三A相关性评分Prompt样例 | ✅ 已完成 |
| `information_classification_prompt.txt` | 阶段三B分类Prompt样例 | ✅ 已完成 |
| `kol_style_analysis_prompt.txt` | 阶段四KOL拆解Prompt样例 | ✅ 已完成 |
| `linkedin_content_constraints_prompt.txt` | 阶段四输出的内容生成约束Prompt | ✅ 已完成 |
| `linkedin_post_generation_prompt.txt` | 阶段五LinkedIn正文生成Prompt样例 | ✅ 已完成 |
| `image_generation_prompt.txt` | 阶段五配图Prompt样例 | ✅ 已完成 |
| `LinkedIn_Post_Style_Anatomy_Checklist.md` | 阶段四风格与结构清单 | ✅ 已完成 |
| `Category_1_AI_Infrastructure_Risk_Post.md` | 分类1最终LinkedIn帖子 | ✅ 已完成 |
| `Category_2_AI_Mineral_SupplyChain_Post.md` | 分类2最终LinkedIn帖子 | ✅ 已完成 |

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

*最后更新：2026-05-01*
*依据：Implementation_Roadmap.md v3.0/v4.0 与 Plan_of_Project.md v3.0*
