# Homework 2 最终进度报告

## 1. 项目概述

本项目名称为 **AI基建地缘风险洞察工作流**，对应课程作业《AI Content Monitoring and Generation Workflow》。项目目标是设计并实现一个AI驱动的信息处理工作流，用于监控、过滤、分类并生成适合LinkedIn发布的专业内容。

经过战略收窄后，本项目不再定位为泛AI新闻系统，而是聚焦更清晰的垂直场景：

> 面向AI基建投资者、数据中心运营商、跨国AI企业战略/供应链/风控负责人，构建一个可运行、可解释、可复盘的AI基础设施地缘风险与供应链决策洞察MVP工作流。

核心主线包括：

1. **AI算力基础设施地缘风险**：数据中心、算力网络、能源、电力、海缆、区域政策与冲突对AI基建布局的影响。
2. **AI关键矿产供应链与地缘政治**：铜、锂、稀土等关键矿产对AI算力扩张、芯片制造和数据中心建设成本的影响。

## 2. 工作流架构与设计逻辑

本项目采用“可运行MVP优先”的架构，不追求一次性实现全自动全球信息抓取，而是先跑通完整闭环：

```text
本地样例新闻 / RSS预留配置
    -> 新闻清洗与摘要
    -> 规则过滤
    -> LLM语义评分接口占位
    -> 主线分类与辅助标签
    -> SQLite信息仓库
    -> KOL风格拆解
    -> LinkedIn决策简报生成
    -> 运行日志与最终报告
```

设计逻辑包括四点：

1. **范围优先**：只围绕AI基建和关键矿产供应链两个主线，避免项目发散。
2. **可解释优先**：相关性路由采用“规则过滤 + 语义评分”的双层结构，保留判断理由。
3. **可复现优先**：当前版本使用本地样例数据和离线确定性逻辑，保证没有网络和外部API时也能测试。
4. **内容质量优先**：LinkedIn内容不做泛新闻总结，而是按照决策简报结构输出商业影响和后续观察信号。

## 3. 核心技术栈与AI工具应用

| 工具/技术 | 项目角色 |
|-----------|----------|
| Claude Code | 用于项目架构设计、Python脚本生成、调试、文档整理与交付物收口 |
| Minimax M2.7 | 作为计划中的核心LLM引擎，用于后续接入摘要、评分、分类和内容生成 |
| SQLite | 作为MVP信息仓库，保存新闻、路由、分类、KOL分析、内容生成和运行审计记录 |
| Python标准库 | 完成离线样例读取、文本清洗、规则过滤、数据库写入、日志记录和总控脚本 |
| Markdown | 保存Prompt样例、风格指南、最终LinkedIn内容与进度报告 |

当前版本为了保证用户测试稳定，Minimax M2.7接口采用占位配置，核心逻辑以离线可复现方式实现。后续可以在不重做数据库结构的情况下替换为真实LLM调用。

## 4. 阶段完成情况

| 阶段 | 对应作业要求 | 交付物 | 完成状态 |
|------|--------------|--------|----------|
| 阶段一 | 领域定义与战略定位 | `Implementation_Roadmap.md`、`Plan_of_Project.md`、`Intro.md` | 已完成 |
| 阶段二 | Daily AI News and Information Monitoring | `1_news_monitoring.py`、样例新闻、RSS配置、SQLite schema | 已完成 |
| 阶段三A | Relevance Routing | `2_relevance_router.py`、相关性Prompt、路由结果表 | 已完成 |
| 阶段三B | Information Classification | `3_information_classification.py`、分类Prompt、分类结果表 | 已完成 |
| 阶段四 | LinkedIn Content Research | `4_linkedin_analysis.py`、KOL风格清单、约束Prompt | 已完成 |
| 阶段五 | LinkedIn Content Generation | `5_linkedin_content_generation.py`、两篇最终帖子、配图Prompt | 已完成 |
| 阶段六 | Workflow, Prompt Optimization and Progress Report | `0_main_workflow.py`、最终报告、优化记录、架构说明 | 已完成，待用户测试 |

## 5. 数据库与运行结果

当前SQLite数据库路径：

```text
AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/ai_geopolitical_risk_workflow.sqlite3
```

截至阶段六整理时，数据库中已有如下核心结果：

| 表 | 记录数 | 含义 |
|----|--------|------|
| `news_items` | 6 | 样例新闻记录 |
| `relevance_routing_results` | 6 | 每条新闻的相关性路由结果 |
| `classification_results` | 4 | 被保留内容的主线分类结果 |
| `kol_analysis_results` | 4 | 4位KOL的风格拆解 |
| `linkedin_content_results` | 2 | 两篇最终LinkedIn帖子 |

路由结果：

- 保留：4条。
- 过滤：2条。

分类结果：

- AI算力基础设施地缘风险：3条。
- AI关键矿产供应链与地缘政治：1条。

## 6. Prompt设计样例

本项目按阶段保留关键Prompt样例：

| Prompt文件 | 使用环节 |
|------------|----------|
| `news_summarization_prompt.txt` | 新闻清洗、摘要与关键词抽取 |
| `relevance_routing_prompt.txt` | 双层相关性路由与0-10分评分 |
| `information_classification_prompt.txt` | 主线分类与辅助标签分配 |
| `kol_style_analysis_prompt.txt` | KOL内容结构拆解 |
| `linkedin_content_constraints_prompt.txt` | LinkedIn内容生成约束 |
| `linkedin_post_generation_prompt.txt` | 最终帖子正文生成 |
| `image_generation_prompt.txt` | LinkedIn配图Prompt生成 |

这些Prompt共同固化了项目定位、目标受众、判断标准、分类体系和最终输出格式。

## 7. 核心挑战与解决方案

### 7.1 挑战一：原始项目范围过大

最初设想覆盖AI全产业链、全球信息源和全自动内容生成，容易导致信息源过多、分类边界模糊、内容输出泛化。

解决方案：

- 将主题收窄为AI算力基础设施和AI关键矿产供应链。
- 将5个宽泛分类压缩为2个主线分类和3个辅助标签。
- 将“全自动平台”调整为“可运行MVP工作流”。

### 7.2 挑战二：信息源稳定性不足

真实RSS/API源存在网络、权限、格式和稳定性问题。如果作业演示完全依赖外部抓取，容易影响测试。

解决方案：

- 使用本地样例新闻保证无网络环境可运行。
- 保留RSS/API配置文件，体现未来扩展能力。
- 所有样例数据统一入库，后续模块只依赖SQLite。

### 7.3 挑战三：LLM相关性判断可能波动

如果直接让LLM判断新闻是否相关，结果可能因措辞变化而不稳定，也不利于解释。

解决方案：

- 第一层使用工程化规则过滤。
- 第二层按照固定权重评分。
- 每条结果保留命中词、分数、决策和判断理由。

### 7.4 挑战四：LinkedIn内容容易变成普通新闻总结

作业要求输出专业平台内容，因此最终内容必须体现业务洞察，而不是简单复述新闻。

解决方案：

- 拆解4位KOL的内容结构。
- 固定决策简报式模板。
- 强制输出Business implications和Signals to watch。
- 每篇帖子附带目标受众、语气定位、来源证据和质量自检。

## 8. 工作流与Prompt优化过程

项目优化可以概括为四个方向：

| 优化方向 | 优化前 | 优化后 | 效果 |
|----------|--------|--------|------|
| 项目范围 | AI全产业链地缘政治内容系统 | AI基建地缘风险MVP工作流 | 范围更清晰，交付更可控 |
| 信息输入 | 偏向每日全自动抓取 | 本地样例数据 + RSS/API预留 | 演示稳定，扩展路径明确 |
| 相关性判断 | 完全依赖LLM | 规则过滤 + LLM评分接口 | 判断更一致、更可解释 |
| 内容输出 | 普通LinkedIn文章 | 决策简报式LinkedIn帖子 | 更适合投资者和企业高管 |

详细Prompt优化记录见：

```text
AI_Geopolitical_Risk_Workflow_Homework_Delivery/4-Progress_Report/prompt_optimization_records.md
```

## 9. 最终LinkedIn内容

本项目最终生成两篇LinkedIn内容：

1. `Category_1_AI_Infrastructure_Risk_Post.md`
   - 主题：AI算力基础设施地缘风险。
   - 目标受众：AI基建投资者、数据中心运营商、云战略团队和跨国AI企业战略负责人。
   - 定位：专业洞察 + 风险预警式决策简报。

2. `Category_2_AI_Mineral_SupplyChain_Post.md`
   - 主题：AI关键矿产供应链与地缘政治。
   - 目标受众：AI基建投资者、大宗商品投资者和AI企业供应链负责人。
   - 定位：深度分析 + 高管简报式内容。

两篇内容均包含：

- LinkedIn正文。
- 目标受众。
- 语气与定位。
- 来源证据。
- 配图Prompt。
- 质量自检。

## 10. 项目经验与核心收获

1. **信息系统项目需要先收窄场景，再谈自动化。** 如果领域太宽，后续的监控、分类和内容生成都会失去稳定标准。
2. **Prompt设计必须和数据结构一起设计。** 只有当Prompt输出能写入数据库并被下一阶段使用，工作流才真正可复盘。
3. **规则和LLM适合协同，而不是互相替代。** 规则适合降低噪音，LLM适合做语义判断和内容生成。
4. **内容生成的质量取决于前面阶段的约束。** 如果前面的定位、分类和KOL风格拆解不清楚，最终LinkedIn内容很容易变成泛泛总结。
5. **MVP不是功能缩水，而是风险控制。** 当前版本优先保证可运行、可解释和可测试，为后续真实API接入打基础。

## 11. 未来优化与自动化机会

后续可以从以下方向升级：

1. 接入真实RSS/API源，实现每日自动抓取。
2. 接入Minimax M2.7，替换当前离线摘要、评分、分类和内容生成逻辑。
3. 增加Chroma向量库，用于长期新闻案例检索和主题聚类。
4. 增加自动去重和相似主题合并，避免同一事件重复生成内容。
5. 增加人工审核界面，让用户选择哪些事件进入LinkedIn生成阶段。
6. 增加定时任务和邮件/消息提醒，形成每日风险简报。
7. 增加更多内容风格版本，例如高管摘要版、投资人深度版和政策分析版。

## 12. 用户测试方式

在项目根目录 `Homework2` 下运行：

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/0_main_workflow.py
```

预期检查点：

- 命令成功退出。
- `Overall success: True`。
- 阶段二到阶段五均显示OK。
- 数据库健康检查全部PASS。
- `4-Progress_Report/workflow_running_logs/` 中新增 `main_workflow` 主控日志。
- 两篇LinkedIn内容和Prompt样例文件存在且内容非空。

## 13. 最终交付物清单

```text
AI_Geopolitical_Risk_Workflow_Homework_Delivery
├── 1-Workflow_Files
│   ├── 0_main_workflow.py
│   ├── 1_news_monitoring.py
│   ├── 2_relevance_router.py
│   ├── 3_information_classification.py
│   ├── 4_linkedin_analysis.py
│   ├── 5_linkedin_content_generation.py
│   ├── workflow_architecture.md
│   ├── api_config.py
│   ├── database_config/sqlite_db_init.sql
│   └── sample_data/
├── 2-Prompt_Design_Samples
│   ├── news_summarization_prompt.txt
│   ├── relevance_routing_prompt.txt
│   ├── information_classification_prompt.txt
│   ├── kol_style_analysis_prompt.txt
│   ├── linkedin_content_constraints_prompt.txt
│   ├── linkedin_post_generation_prompt.txt
│   └── image_generation_prompt.txt
├── 3-Final_LinkedIn_Content
│   ├── LinkedIn_Post_Style_Anatomy_Checklist.md
│   ├── Category_1_AI_Infrastructure_Risk_Post.md
│   └── Category_2_AI_Mineral_SupplyChain_Post.md
└── 4-Progress_Report
    ├── Progress_Report_Final.md
    ├── prompt_optimization_records.md
    └── workflow_running_logs/
```

## 14. 总结

本项目完成了从信息监控、相关性路由、分类、KOL分析到LinkedIn内容生成的完整MVP闭环。相比原始设想，最终版本更聚焦、更可运行、更容易解释，也更符合课程作业对工作流设计、Prompt优化和进度复盘的要求。

当前阶段六已完成，进入用户最终测试阶段。
