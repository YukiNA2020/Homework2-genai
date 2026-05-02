# Homework2 专属落地执行方案：AI基建地缘风险洞察工作流

> 文档用途：本文件为《Homework 2 AI Content Monitoring and Generation Workflow》的专属落地执行方案，用于指导全链路工作流的代码实现、Prompt设计与交付物生成。
> 核心背景：信息管理与信息系统专业背景，结合地缘政治研究兴趣与AI课程要求，构建一个范围清晰、可运行、可复盘的AI内容工作流。
> 核心技术栈：Claude Code（代码生成/调试/架构设计）+ DeepSeek V4（工作流核心LLM引擎，默认使用 `deepseek-v4-pro`）+ SQLite（MVP信息仓库，可扩展到Chroma）。
> 战略调整：从“AI全产业链全自动内容系统”收窄为“面向AI基建投资与供应链决策的地缘风险洞察MVP工作流”。

---

## 一、核心定位全固化

### 1.1 垂直领域定义
**AI基础设施地缘风险与供应链决策洞察**

本项目聚焦AI产业中最具商业决策价值、也最容易落地验证的两个场景：

1. **AI算力基础设施地缘风险**
   - 数据中心、算力网络、能源、电力、海缆、云基础设施布局。
   - 关注区域冲突、政策管制、能源约束、跨境数据与基础设施安全对AI基建的影响。

2. **AI关键矿产供应链与地缘政治**
   - 铜、锂、稀土等关键矿产对AI算力扩张、芯片制造、数据中心建设的影响。
   - 关注资源国政治风险、出口管制、供应集中度、运输通道与成本波动。

芯片出口管制、区域冲突、AI治理等主题作为辅助标签保留，但不作为本次作业的主要内容生成方向。

### 1.2 LinkedIn人设定位
AI基建地缘风险洞察分析师 | 信息管理与信息系统专业背景 | 聚焦AI算力基础设施、关键矿产供应链与跨境投资风险

### 1.3 精准目标受众
**主目标受众：**
1. AI基建投资者：VC/PE机构、科技赛道基金、数据中心与算力基础设施投资者。
2. 跨国AI企业、数据中心运营商、AI芯片/算力厂商的战略、供应链与风险管理负责人。

**次级目标受众：**
3. 关键矿产、能源与AI基础设施交叉领域的从业者、分析师与跨境投资者。
4. 关注科技与国际关系交叉领域的智库研究员、政策制定者、行业分析师。

### 1.4 核心商业价值
所有内容与信息筛选必须围绕一个核心判断：

> 这条信息是否会影响AI基建投资、数据中心布局、供应链成本或跨境风险决策？

具体拆解为两个问题：
1. 当下的地缘政治/国际关系事件，会给AI基建投资、AI企业供应链或数据中心布局带来什么风险或机会？
2. 企业或投资者应该关注哪些预警信号，以提前规避风险或捕捉产业机会？

### 1.5 落地边界与MVP策略
本项目不承诺一次性完成全球AI新闻的全自动抓取系统，而是采用更成熟的MVP路径：

| 阶段 | 定位 | 说明 |
|------|------|------|
| 当前作业版本 | 可运行MVP | 使用手动样例数据 + RSS/API预留接口，跑通监控、摘要、路由、分类、生成、日志闭环 |
| 后续扩展版本 | 半自动/自动化系统 | 扩展真实RSS/API源、定时任务、Chroma向量库与可视化看板 |

---

## 二、对应作业6大强制任务的专属落地执行指引

### 2.1 任务1：每日AI新闻与信息监控（15分）

#### 核心目标
建立一个可扩展的信息监控管道。当前版本优先保证可复现、可运行，因此采用“手动样例数据 + RSS/API配置预留”的混合输入模式。

#### 信息源策略
| 类型 | 来源 | 当前处理方式 |
|------|------|------|
| 手动样例数据 | 自建AI基建/关键矿产/地缘风险样例新闻 | 保证工作流稳定演示 |
| 公开RSS/API | Reuters、FT、MIT Technology Review、CSIS等可用公开源 | 预留配置和抓取函数 |
| 机构报告 | IEA、USGS、McKinsey、Goldman Sachs等 | 作为高可信背景材料和样例来源 |
| 企业公告 | Microsoft、Google、NVIDIA、OpenAI、云厂商 | 作为AI基建与供应链事件来源 |

#### 核心功能要求
1. 支持读取本地样例新闻数据，确保无网络环境下也能运行。
2. 预留RSS/API抓取接口，体现每日自动化监控的可扩展设计。
3. 调用DeepSeek V4完成新闻清洗、摘要、关键词提取、发布时间/来源标准化。
4. 使用SQLite作为MVP信息仓库，保存原始新闻、摘要、关键词、来源、链接与处理状态。
5. 支持去重处理，避免重复导入同一条内容。

#### 输入输出规范
- 输入：样例新闻数据、RSS/API配置、关键词过滤规则、DeepSeek V4 API配置。
- 输出：结构化新闻数据集、SQLite数据库、运行日志。
- 对应可运行脚本：`1_news_monitoring.py`

---

### 2.2 任务2：相关性路由与领域定义（15分）

#### 核心目标
搭建一个“规则过滤 + LLM语义评分”的双层信息守门机制，避免完全依赖LLM主观判断。

#### 第一层：规则过滤
内容必须同时命中两组信号，才进入LLM评分：

**AI基建/供应链信号：**
AI、data center、compute、GPU、chip、semiconductor、cloud、power、electricity、copper、lithium、rare earths、critical minerals、supply chain。

**地缘/跨境风险信号：**
export control、sanctions、conflict、regulation、trade restriction、China、US、EU、Taiwan、Middle East、resource nationalism、shipping disruption。

#### 第二层：LLM语义评分
通过第一层过滤后，调用DeepSeek V4进行0-10分相关性评分。

#### 固定打分规则
| 权重 | 标准 |
|------|------|
| 40% | 是否影响AI基建投资、数据中心布局、供应链成本或跨境业务连续性 |
| 25% | 是否有真实事件、数据、报告或案例支撑 |
| 20% | 是否精准匹配主目标受众的决策需求 |
| 15% | 是否涉及算力基础设施、关键矿产、能源、电力、芯片供应链等核心环节 |

#### 阈值设置
0-10分量化打分，**≥7分保留，＜7分过滤**。

#### 打分示例
| 抓取的信息 | 分数 | 处理 | 原因 |
|-----------|------|------|------|
| 海湾地区冲突导致多条海缆与数据中心能源供应面临中断风险，云服务商上调区域算力价格 | 9 | 保留 | 同时涉及区域冲突、AI算力基础设施、成本与业务连续性 |
| IEA报告指出AI数据中心扩张将显著推高铜需求，而主要铜矿产区政治风险上升 | 10 | 保留 | 同时涉及AI基建、关键矿产、权威数据与投资影响 |
| OpenAI发布新的多模态模型功能 | 0 | 过滤 | 纯技术更新，与地缘风险和AI基建投资决策无直接关系 |
| 某地区发生军事冲突，但没有涉及AI基础设施、能源、芯片或供应链 | 0 | 过滤 | 纯地缘新闻，不满足AI基建/供应链门槛 |

#### 输入输出规范
- 输入：任务1输出的结构化新闻数据、规则关键词表、相关性打分Prompt、DeepSeek V4 API配置。
- 输出：高相关性新闻数据集、过滤日志、LLM评分依据。
- 对应可运行脚本：`2_relevance_router.py`

---

### 2.3 任务3：信息分类（15分）

#### 核心目标
为高相关性内容分配主线分类与辅助标签，支持后续按主题生成LinkedIn内容。

#### 主线分类
| 分类编号 | 分类名称 | 分类定义 |
|----------|----------|----------|
| 1 | AI算力基础设施地缘风险 | 区域冲突、政策管制、能源约束、数据中心选址、海缆与云基础设施风险 |
| 2 | AI关键矿产供应链与地缘政治 | 铜、锂、稀土等关键矿产供应变化对AI基建成本、芯片制造和投资节奏的影响 |

#### 辅助标签
| 标签 | 使用场景 |
|------|----------|
| AI芯片出口管制 | GPU、先进制程、半导体设备、出口限制 |
| 区域冲突影响 | 战争、航运中断、能源通道、基础设施破坏 |
| 全球AI治理 | AI监管框架、跨境数据规则、国际政策博弈 |

#### 核心功能要求
1. 调用DeepSeek V4为每条高相关性内容分配1个主线分类。
2. 可选分配0-2个辅助标签，增强检索与分析能力。
3. 完成分类后，自动更新标签信息到SQLite数据库。
4. 支持按分类标签快速检索对应内容。

#### 输入输出规范
- 输入：任务2输出的高相关性新闻数据集、分类规则Prompt、DeepSeek V4 API配置。
- 输出：带主线分类与辅助标签的结构化新闻数据集、数据库标签更新记录。
- 对应可运行脚本：`3_information_classification.py`

---

### 2.4 任务4：LinkedIn内容调研与规范拆解（15分）

#### 核心目标
反向拆解KOL内容逻辑，输出适合本项目受众的“决策简报式LinkedIn帖子”规范。

#### 对标KOL清单
1. Chris Miller：《芯片战争》作者，关注科技供应链、芯片与地缘政治。
2. Paul Triolo：关注科技地缘政治、AI监管、中美科技博弈。
3. Gregory C. Allen：CSIS人工智能项目主任，关注AI国家安全与产业政策。
4. Jordan Schneider：《ChinaTalk》主播，关注中美科技竞争、AI与半导体产业。

#### 必须拆解的核心维度
1. 开篇钩子：是否以风险信号、关键数字、反直觉判断开场。
2. 内容结构：是否短段落、强逻辑、适合移动端扫读。
3. 公信力搭建：是否通过数据、案例、权威信源建立可信度。
4. 互动引导：是否提出高质量决策问题，而不是泛泛求评论。
5. 内容风格：以“高管/投资人决策简报”为主，避免泛新闻摘要。

#### 输出要求
1. 输出《LinkedIn AI基建地缘风险帖子风格与结构清单》Markdown文档。
2. 将清单转化为内容生成约束Prompt，严格限定后续文案生成规则。

#### 输入输出规范
- 输入：对标KOL的公开内容样本或手动整理样本、拆解维度Prompt、DeepSeek V4 API配置。
- 输出：`LinkedIn_Post_Style_Anatomy_Checklist.md`、内容生成约束Prompt文件。
- 对应可运行脚本：`4_linkedin_analysis.py`

---

### 2.5 任务5：LinkedIn内容自动化生成（20分）

#### 核心目标
从两个主线分类中各生成1篇专业LinkedIn内容，内容形式从“文章式生成”调整为“决策简报式帖子”。

#### 固定选定分类与帖子要求
| 选定分类 | 核心主题方向 | 强制标注信息 |
|----------|--------------|--------------|
| 分类1：AI算力基础设施地缘风险 | 地缘事件对数据中心、算力网络、能源和云基础设施布局的影响 | 目标受众：AI基建投资者、数据中心运营商、跨国AI企业战略负责人；语气与定位：专业洞察+风险预警式决策简报 |
| 分类2：AI关键矿产供应链与地缘政治 | AI算力扩张下，关键矿产供应风险与投资机会分析 | 目标受众：AI基建投资者、大宗商品投资者、AI企业供应链负责人；语气与定位：深度分析+高管简报式内容 |

#### 固定内容模板
```text
Hook:
一个反直觉判断、关键数字或风险信号。

What happened:
简述事件或趋势。

Why it matters for AI infrastructure:
解释对算力、数据中心、能源、芯片或关键矿产的影响。

Business implications:
3个商业/投资影响。

Signals to watch:
2-3个后续观察指标。

Closing question:
一个能引发目标受众讨论的问题。
```

#### 核心功能要求
1. 从SQLite数据库中按主线分类拉取最新高相关性新闻与洞见。
2. 调用DeepSeek V4，严格遵循内容约束Prompt生成LinkedIn文案。
3. 同步生成配图Prompt，支持后续对接绘图API。
4. 自动为每篇帖子补充目标受众、语气与定位标注。

#### 输入输出规范
- 输入：对应分类的结构化新闻洞见数据、内容生成约束Prompt、DeepSeek V4 API配置。
- 输出：最终LinkedIn帖子文案、配图生成Prompt、目标受众与定位标注。
- 对应可运行脚本：`5_linkedin_content_generation.py`

---

### 2.6 任务6：工作流、Prompt优化与进度报告（20分）

#### 核心目标
输出结构化进度报告，完整复盘工作流架构、核心挑战、优化过程、经验总结与未来改进方向，突出信管专业的信息系统设计能力。

#### 报告强制包含章节
1. 工作流架构与设计逻辑：从混合输入到内容生成的完整链路。
2. 核心技术栈与AI工具应用说明：Claude Code、DeepSeek V4、SQLite在工作流中的角色。
3. 核心挑战与解决方案：范围过大、信息源不稳定、LLM判断一致性、内容质量控制。
4. 工作流与Prompt优化进展：从“全自动全产业链”优化为“MVP可运行的AI基建地缘风险工作流”。
5. 项目经验与核心收获。
6. 未来可优化与自动化升级方向。

#### 配套支撑要求
1. 串联所有模块，生成全流程总控脚本，实现一键运行MVP工作流。
2. 记录全链路运行日志，为报告提供数据支撑。
3. 记录Prompt优化前后对比，体现迭代过程。

#### 输入输出规范
- 输入：所有子模块脚本与配置、全流程运行日志、Prompt优化记录。
- 输出：`0_main_workflow.py`、结构化运行日志、`Progress_Report_Final.md`。

---

## 三、最终交付物标准目录结构

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
    ├── stage_11_image_generation_notes.md
    ├── stage_12_daily_review_notes.md
    └── prompt_optimization_records.md
```

---

## 四、全流程Prompt设计核心规范

1. 所有Prompt必须明确标注：使用环节、核心目标、约束规则、输出格式。
2. 所有业务规则必须固化到Prompt中，包括行业定位、双层相关性标准、两类主线分类、辅助标签、内容模板。
3. Prompt输出格式优先使用JSON/Markdown，确保可被代码自动解析。
4. 必须留存Prompt优化前后版本，用于进度报告复盘。
5. LinkedIn内容生成Prompt使用英文，以适配LinkedIn语境；项目说明文档可使用中文。

---

## 五、分步起步执行清单

1. 第一步：完成战略收窄，固化AI基建地缘风险MVP定位。
2. 第二步：生成“样例新闻输入 -> 摘要 -> 规则过滤 -> LLM评分 -> 分类”的最小闭环可运行代码。
3. 第三步：完成KOL内容拆解，输出决策简报式LinkedIn风格清单。
4. 第四步：完成全模块代码开发与联调，实现一键运行MVP。
5. 第五步：生成2篇最终LinkedIn内容与结构化进度报告。
6. 第六步：按照标准目录结构整理最终交付物。
