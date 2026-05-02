# AI基建地缘风险洞察工作流架构说明

> 使用环节：阶段六/阶段八/阶段十一 - 工作流、真实RSS接入、图片生成与归档说明。  
> 版本：v1.2 image-archive enabled MVP  
> 更新日期：2026-05-02

## 1. 设计目标

本工作流面向“AI基础设施地缘风险与供应链决策洞察”这一垂直场景，目标不是搭建泛AI新闻平台，而是完成一个可运行、可解释、可复盘的MVP闭环：

```text
样例新闻/真实RSS配置
    -> 新闻清洗与摘要
    -> 双层相关性路由
    -> 主线分类与辅助标签
    -> SQLite信息仓库
    -> KOL风格约束
    -> LinkedIn决策简报生成
    -> 图片生成与内容归档
    -> 运行日志与最终报告
```

核心判断问题：

> 这条信息是否会影响AI基建投资、数据中心布局、供应链成本或跨境风险决策？

## 2. 模块结构

| 阶段 | 脚本 | 输入 | 输出 | 说明 |
|------|------|------|------|------|
| 阶段二/八 | `1_news_monitoring.py` | `sample_news.json`、真实RSS配置 | `news_items`、`source_registry`、`ingestion_runs` | 支持本地样例与真实RSS双模式，完成清洗、摘要、关键词抽取与去重入库 |
| 阶段三A | `2_relevance_router.py` | `news_items` | `relevance_routing_results`、`routing_runs` | 先规则过滤，再执行离线语义评分占位，保留≥7分内容 |
| 阶段三B | `3_information_classification.py` | 保留内容 | `classification_results`、`classification_runs` | 分入两条主线分类，并附加辅助标签 |
| 阶段四 | `4_linkedin_analysis.py` | KOL画像规则 | `kol_analysis_results`、风格清单、约束Prompt | 拆解4位KOL的LinkedIn内容结构 |
| 阶段五 | `5_linkedin_content_generation.py` | 分类结果、内容约束 | `linkedin_content_results`、两篇最终帖子、配图Prompt | 为两个主线分类各生成1篇决策简报式帖子 |
| 阶段十一 | `6_image_generation.py` | `linkedin_content_results`、配图Prompt | `image_generation_results`、图片文件、归档包 | 为最终帖子生成或fallback渲染16:9视觉图，并归档Markdown、图片和manifest |
| 阶段六/十一 | `0_main_workflow.py` | 全部阶段脚本 | 主控日志、最终报告支撑数据 | 一键串联阶段二到阶段五，可选 `--include-stage11` 跑图片生成与归档 |

## 3. 数据库设计逻辑

SQLite作为MVP信息仓库，核心表分为四类：

| 表类型 | 表名 | 用途 |
|--------|------|------|
| 原始输入与来源 | `source_registry`、`news_items` | 保存来源、原文、摘要、关键词与去重哈希 |
| 路由与分类结果 | `relevance_routing_results`、`classification_results` | 保存规则命中、评分、分类、标签和判断理由 |
| 内容研究与生成 | `kol_analysis_results`、`linkedin_content_results` | 保存KOL风格拆解和最终LinkedIn内容 |
| 图片与归档 | `image_generation_results` | 保存每个分类最新图片、归档路径、模型、状态和元数据 |
| 审计运行记录 | `ingestion_runs`、`routing_runs`、`classification_runs`、`kol_analysis_runs`、`linkedin_content_runs`、`image_generation_runs` | 保存每次运行的数量统计、错误数与运行ID |

这种结构保证每个阶段既可以单独测试，也可以通过总控脚本串联运行。

## 4. 相关性路由设计

路由采用“双层守门”：

1. 规则过滤：必须同时命中AI基建/供应链信号和地缘/跨境风险信号。
2. 语义评分：按照业务影响、证据支撑、受众匹配和核心链条相关性进行0-10分评分。

保留阈值为7分。这样做的目的，是降低纯LLM判断波动，并让过滤理由可以被复盘。

## 5. 分类设计

主线分类只保留两类：

1. AI算力基础设施地缘风险。
2. AI关键矿产供应链与地缘政治。

辅助标签包括：

- AI芯片出口管制。
- 区域冲突影响。
- 全球AI治理。

这种分类方式避免范围过大，同时保留未来扩展空间。

## 6. 内容生成设计

最终LinkedIn内容采用固定决策简报结构：

```text
Hook
What happened
Why it matters for AI infrastructure
Business implications
Signals to watch
Closing question
```

每篇帖子必须附带：

- 目标受众。
- 语气与定位。
- 来源证据。
- 配图Prompt。
- 质量自检。

## 7. 图片生成与归档设计

阶段十一不自动发布LinkedIn，只补齐最终内容形态：

```text
linkedin_content_results
    -> 读取 visual_prompt
    -> 生成或fallback渲染16:9图片
    -> 更新最终帖子Markdown
    -> 写入 images/ 与 archive/YYYY-MM-DD/
    -> 记录 image_generation_results 和 image_generation_runs
```

运行模式：

- `--image-mode offline`：不读取 `.env`，生成本地SVG fallback，保证无key可演示。
- `--image-mode auto`：如MiniMax图片API配置可用则调用API，否则fallback。
- `--image-mode online`：强制真实图片API成功，用于用户填写MiniMax key后验收。

归档包包含：

- `linkedin_post.md`。
- 生成的图片文件。
- `manifest.json`。

## 8. 一键运行方式

在项目根目录 `Homework2` 下运行：

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/0_main_workflow.py
```

预期结果：

- 阶段二读取6条样例新闻；如果数据库已有数据，显示重复跳过是正常现象。
- 阶段三A完成6条路由，保留4条、过滤2条。
- 阶段三B完成4条分类。
- 阶段四完成4位KOL画像与3个输出文件。
- 阶段五生成2篇最终LinkedIn帖子和2个Prompt文件。
- 阶段六主控日志写入 `4-Progress_Report/workflow_running_logs/`。

阶段八以后如需用真实RSS作为阶段二输入，可运行：

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/0_main_workflow.py --stage2-input-mode rss --rss-limit 2
```

如果只测试RSS抓取与入库，可运行：

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/1_news_monitoring.py --input-mode rss --rss-limit 2
```

阶段十一单独测试：

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/6_image_generation.py --image-mode offline
```

阶段十一总控集成测试：

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/0_main_workflow.py --include-stage11 --image-mode offline
```

## 9. 扩展接口

当前版本为RSS + LLM + image-archive enabled MVP，未来可在不重做数据库结构的前提下扩展：

- 增加定时任务，实现每日监控。
- 增加Chroma或其他向量库，用于长期检索和相似案例召回。
- 增加仪表盘，展示分类趋势、风险信号和内容生成记录。
