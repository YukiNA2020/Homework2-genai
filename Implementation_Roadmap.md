# 实施路线图：AI基建地缘风险洞察工作流

> 本文档为作业专属落地执行方案的核心架构文件，定义全流程的根规则、阶段目标与交付边界。
> 战略版本：3.0（作业交付版）/ 4.0（后续升级路线）
> 更新日期：2026-05-02

---

## 1. 核心定位（全局根规则，所有环节必须严格遵循）

### 1.1 垂直领域
**AI基础设施地缘风险与供应链决策洞察**

本项目不再定位为覆盖“AI全产业链”的宏大信息系统，而是聚焦一个更可落地的决策场景：

> 面向AI基建投资与跨国AI企业供应链决策的地缘风险信息过滤、分类与LinkedIn内容生成工作流。

核心关注两条主线：
1. **AI算力基础设施地缘风险**：数据中心、算力网络、能源、海缆、区域政策与冲突对AI基建布局的影响。
2. **AI关键矿产供应链风险**：铜、锂、稀土等关键矿产的地缘供应风险，对AI算力扩张、芯片制造与数据中心建设成本的影响。

芯片出口管制、区域冲突、AI治理等内容保留为辅助标签或未来扩展方向，不作为本次作业主线。

### 1.2 LinkedIn人设
AI基建地缘风险洞察分析师 | 信息管理与信息系统专业背景 | 聚焦AI算力基础设施、关键矿产供应链与跨境投资风险

### 1.3 精准目标受众（强制）
**主目标受众：**
1. AI基建投资者：VC/PE、科技赛道基金、数据中心与算力基础设施投资者。
2. 跨国AI企业、数据中心运营商、AI芯片/算力厂商的战略、供应链与风险管理负责人。

**次级目标受众：**
3. 关键矿产、能源与AI基础设施交叉领域的行业分析师与跨境投资者。
4. 关注科技地缘政治的智库研究员、政策观察者与产业研究人员。

后续所有相关性判断优先回答一个问题：

> 这条信息是否会影响AI基建投资、数据中心布局、供应链成本或跨境风险决策？

### 1.4 核心商业价值（相关性判断的核心标尺）
所有内容必须围绕解决目标受众的2个终极问题：
1. 当下的地缘政治事件，会给AI基建投资、数据中心布局或供应链成本带来什么可判断的风险或机会？
2. 企业或投资者应该关注哪些预警信号，以提前规避风险或捕捉产业机会？

### 1.5 落地边界
本项目采用 **MVP优先** 策略：

- 当前版本：使用“RSS/API可扩展接口 + 手动样例数据”的混合输入，跑通信息监控、摘要、双层路由、分类、内容生成与日志记录。
- 未来版本：扩展到更多真实RSS/API源，实现每日定时运行和更完整的数据库沉淀。

因此，本项目不是承诺一次性完成“全球AI新闻全自动抓取系统”，而是设计一个可扩展、可验证、适合作业交付的地缘风险洞察工作流。

---

## 2. 信息源体系

### 2.1 MVP输入策略
| 输入类型 | 用途 | 当前版本处理方式 |
|------|------|------|
| 手动样例数据 | 保证流程可运行、可演示、可复现 | 内置样例新闻与报告摘要 |
| RSS/API源 | 展示可扩展的信息监控能力 | 预留配置文件与抓取接口 |
| 公开报告/机构页面 | 提供高可信背景材料 | 作为样例来源与Prompt引用来源 |

### 2.2 优先信息源
| 类别 | 来源 |
|------|------|
| AI基建/科技企业 | Microsoft、Google、NVIDIA、OpenAI、主要云厂商数据中心与供应链公告 |
| 投资与咨询机构 | a16z、Sequoia、Goldman Sachs、Morgan Stanley、McKinsey、BCG关于AI基建、能源、供应链的研究 |
| 地缘与产业媒体 | Reuters、Financial Times、The Economist、Wall Street Journal的科技供应链与地缘风险报道 |
| 专业机构 | IEA、USGS、CSIS、RAND、MIT Technology Review |
| 垂直专家/KOL | Chris Miller、Paul Triolo、Gregory C. Allen、Jordan Schneider |

---

## 3. 相关性评分规则

### 3.1 双层路由机制
为避免完全依赖LLM的主观判断，相关性路由采用两层结构：

**第一层：规则过滤**

内容必须同时命中两类信号：
- AI基建/供应链信号：AI、data center、compute、GPU、chip、semiconductor、cloud、power、copper、lithium、rare earths等。
- 地缘/跨境风险信号：export control、sanctions、conflict、regulation、supply chain、China、US、EU、Taiwan、Middle East、trade restriction等。

未同时命中两类信号的内容直接过滤或降为低优先级。

**第二层：LLM语义评分**

通过第一层的内容，再由LLM按照0-10分进行语义判断。

### 3.2 高分权重规则
| 权重 | 标准 |
|------|------|
| 40% | 是否影响AI基建投资、数据中心布局、供应链成本或跨境业务连续性 |
| 25% | 是否有真实事件、数据、报告或案例支撑 |
| 20% | 是否匹配主目标受众的决策需求 |
| 15% | 是否涉及算力基础设施、关键矿产、能源、电力、芯片供应链等核心环节 |

### 3.3 阈值设置
0-10分量化打分，**≥7分保留，＜7分过滤**。保留内容必须输出判断依据，便于后续复盘Prompt与规则。

---

## 4. 内容分类体系

### 4.1 主线分类（本次作业重点）
| 编号 | 分类名称 | 定义 |
|------|----------|------|
| 1 | AI算力基础设施地缘风险 | 区域冲突、政策管制、能源约束、海缆/数据中心布局变化对AI算力基础设施的影响 |
| 2 | AI关键矿产供应链与地缘政治 | 铜、锂、稀土等关键矿产的全球供给、出口管制、区域冲突对AI基建成本与投资节奏的影响 |

### 4.2 辅助标签（作为补充，不作为内容生成主线）
| 标签 | 用途 |
|------|------|
| AI芯片出口管制 | 用于标记芯片、GPU、先进制程相关的跨境管制信息 |
| 区域冲突影响 | 用于标记战争、冲突、航运中断等事件 |
| 全球AI治理 | 用于标记AI监管、国际治理框架与政策协调 |

---

## 5. KOL分析清单

### 对标KOL（4位）
1. **Chris Miller** - 《芯片战争》作者，科技供应链与地缘政治专家。
2. **Paul Triolo** - 科技地缘政治与中美科技博弈研究者。
3. **Gregory C. Allen** - CSIS人工智能项目主任，关注AI国家安全与政策影响。
4. **Jordan Schneider** - 《ChinaTalk》主播，关注中美科技竞争、AI与半导体产业。

### 拆解维度
1. 开篇钩子：是否以反直觉判断、风险信号或关键数字开场。
2. 内容结构：是否适合移动端扫读，段落短、逻辑清晰。
3. 公信力搭建：是否引用数据、报告、政策文件或真实案例。
4. 互动引导：是否提出面向投资者或企业负责人的判断问题。
5. 内容风格：偏“决策简报式”，而不是泛泛新闻复述。

---

## 6. 选定内容生成分类

| 分类 | 主题方向 | 目标受众 | 语气与定位 |
|------|----------|----------|------------|
| 分类1 | AI算力基础设施地缘风险 | AI基建投资者、数据中心运营商、跨国AI企业战略负责人 | 专业洞察 + 风险预警式决策简报 |
| 分类2 | AI关键矿产供应链与地缘政治 | AI基建投资者、大宗商品投资者、AI企业供应链负责人 | 深度分析 + 高管简报式内容 |

### 固定LinkedIn内容模板
每篇帖子采用决策简报式结构：

```text
Hook:
用一个反直觉判断、关键数字或风险信号开场。

What happened:
简述事件或趋势。

Why it matters for AI infrastructure:
说明对算力、数据中心、能源、芯片或关键矿产供应的影响。

Business implications:
列出3个商业/投资影响。

Signals to watch:
列出2-3个后续观察指标。

Closing question:
提出一个能引发目标受众讨论的问题。
```

---

## 7. 实施阶段

```text
[阶段一] -> [阶段二] -> [阶段三] -> [阶段四] -> [阶段五] -> [阶段六]
  定位收窄     MVP信息输入   双层路由与分类   KOL风格规范    决策简报生成    最终文档
```

### 阶段一：核心定位收窄
- 将主题从“AI全产业链”收窄为“AI基建地缘风险”。
- 明确主目标受众为AI基建投资者与跨国AI企业战略/供应链负责人。
- 输出：更新后的领域定义与路线图。

### 阶段二：MVP信息监控管道
- 建立混合输入机制：手动样例数据 + RSS/API预留接口。
- 完成新闻清洗、摘要、关键词提取、标准化存储。
- 使用SQLite作为优先落地数据库，Chroma作为可选扩展。
- 输出：`1_news_monitoring.py`

### 阶段三：双层路由与分类
- 第一层规则关键词过滤。
- 第二层LLM相关性打分（≥7分保留）。
- 将保留内容归入2个主线分类，并可附加辅助标签。
- 输出：`2_relevance_router.py`、`3_information_classification.py`

### 阶段四：KOL分析与风格指南
- 拆解4位KOL的内容结构。
- 输出面向“决策简报式LinkedIn帖子”的风格清单。
- 输出：`LinkedIn_Post_Style_Anatomy_Checklist.md`、`4_linkedin_analysis.py`

### 阶段五：内容生成
- 按2个主线分类各生成1篇LinkedIn帖子。
- 每篇包含文案、配图Prompt、目标受众、语气与定位。
- 输出：`5_linkedin_content_generation.py`

### 阶段六：最终文档
- 生成全流程总控脚本。
- 输出Prompt样例、运行日志、优化记录与最终进度报告。
- 输出：`0_main_workflow.py`、`Progress_Report_Final.md`

---

## 8. 交付物目录结构

```text
AI_Geopolitical_Risk_Workflow_Homework_Delivery
├── 1-Workflow_Files
│   ├── 0_main_workflow.py
│   ├── 1_news_monitoring.py
│   ├── 2_relevance_router.py
│   ├── 3_information_classification.py
│   ├── 4_linkedin_analysis.py
│   ├── 5_linkedin_content_generation.py
│   └── database_config/
├── 2-Prompt_Design_Samples
│   └── (各环节Prompt文件)
├── 3-Final_LinkedIn_Content
│   ├── LinkedIn_Post_Style_Anatomy_Checklist.md
│   ├── Category_1_AI_Infrastructure_Risk_Post.md
│   └── Category_2_AI_Mineral_SupplyChain_Post.md
└── 4-Progress_Report
    └── Progress_Report_Final.md
```

---

## 9. 核心原则

1. **范围优先：** 本次作业主线只聚焦AI算力基础设施与关键矿产供应链。
2. **受众中心：** 每条内容必须服务AI基建投资或跨国AI企业供应链/战略决策。
3. **MVP可运行：** 先跑通可复现闭环，再扩展真实RSS/API与向量数据库。
4. **规则+LLM协同：** 先用规则降低噪音，再用LLM完成语义判断。
5. **决策简报式输出：** LinkedIn帖子必须体现商业影响、观察指标与行动价值。

---

## 10. v4.0 后续升级路线：从离线MVP到真实半自动系统

### 10.1 当前状态判断

当前项目已经完成了作业要求中的核心闭环：

```text
本地样例新闻
-> 新闻清洗与摘要
-> 规则相关性过滤
-> 离线评分占位
-> 主线分类
-> SQLite存储
-> KOL风格约束
-> LinkedIn决策简报生成
-> 图片生成与内容归档
-> 日志与最终报告
```

现阶段的主要限制不是架构方向错误，而是后续真实自动化能力仍需继续补齐：

1. **真实每日运行已形成审核包**：RSS、LLM接线、图片生成和归档已经接入，阶段十二已补齐每日运行包装脚本与人工审核队列；后续如需可再安装系统级 `cron`/`launchd`。
2. **真实LLM业务接线已完成但待用户API实测**：DeepSeek V4已作为默认真实LLM配置，摘要、评分、分类和内容生成已支持 `--llm-mode auto|online`，用户填写 `.env` 后再做真实API验收。
3. **真实图片API待用户key验收**：阶段十一已保存本地fallback图片文件并预留MiniMax `online` 模式，用户填写 `.env` 后可测试真实图片生成。

因此，v4.0的目标不是重写系统，而是在现有MVP上逐步替换占位模块。

### 10.2 总体升级路径

```text
[阶段七：稳定MVP冻结]
    -> [阶段八：真实新闻/RSS接入]
    -> [阶段九：LLM客户端统一封装]
    -> [阶段十：用LLM替换摘要、评分、分类、生成]
    -> [阶段十一：图片生成与文件归档]
    -> [阶段十二：每日定时运行与人工审核]
    -> [阶段十三：Daily Run数据血缘闭环修复]
    -> [阶段十四：Evidence Grounding与事实约束]
    -> [阶段十五：Daily Review透明度增强]
    -> [阶段十六：KOL Reverse Engineering修正]
    -> [阶段十七：图片与结果包一致性修复]
    -> [阶段十八：最终报告修订与回归验证]
    -> [阶段十九：可选增强：向量库、看板、邮件简报]
```

### 10.3 阶段七：冻结当前稳定MVP

目标：保护当前已经能跑通的作业版本，避免后续接API时把稳定交付弄坏。

当前状态：已于2026-05-01完成冻结验证。总控脚本运行结果为 `Overall success: True`，阶段二到阶段五全部OK，数据库健康检查全部PASS。冻结基线记录见 `AI_Geopolitical_Risk_Workflow_Homework_Delivery/4-Progress_Report/stage_7_mvp_freeze_baseline.md`。

具体行动：

1. 保留当前 `AI_Geopolitical_Risk_Workflow_Homework_Delivery/` 作为稳定交付目录。
2. 继续使用当前SQLite表结构，优先做兼容式升级。
3. 后续新增真实联网/LLM功能时，保留离线fallback开关。
4. 新增任何API能力前，先确认 `0_main_workflow.py` 仍能离线跑通。

验收标准：

- 不配置API key时，现有离线工作流仍然 `Overall success: True`。
- 配置API key后，可以逐步启用真实抓取或真实模型调用。

### 10.4 阶段八：接入真实新闻/RSS信息源

目标：把阶段二从“本地样例输入”升级为“本地样例 + 真实RSS/API输入”。

当前状态：已于2026-05-01完成阶段八。`1_news_monitoring.py` 已新增 `--input-mode rss` 与 `--rss-limit`；`rss_sources.json` 已配置5个公开RSS源；`0_main_workflow.py` 已新增 `--stage2-input-mode`，默认仍保持 `local_sample` 离线基线。

优先接入来源：

| 优先级 | 来源类型 | 建议来源 |
|------|------|------|
| P0 | 稳定RSS | MIT Technology Review AI、OpenAI Blog、Google AI Blog、Microsoft Blog |
| P1 | 机构/智库 | CSIS、RAND、IEA、USGS |
| P1 | 企业公告 | NVIDIA、Microsoft、Google、主要云厂商 |
| P2 | 媒体/商业源 | Reuters、FT、WSJ等，若无公开RSS则先保留为手动/半自动输入 |

具体行动：

1. 在 `rss_sources.json` 中扩展真实RSS源，先从3-5个稳定源开始。
2. 在 `1_news_monitoring.py` 中实现真实RSS抓取模式，例如 `--input-mode rss`。
3. 为每条抓取内容保存：标题、URL、发布时间、来源、摘要前原文、抓取时间、内容哈希。
4. 保留本地样例模式，避免网络失败时无法演示。
5. 增加抓取失败日志，不因为单个源失败中断整条工作流。

验收标准：

- 运行RSS模式后，数据库能新增真实新闻记录。（已验证）
- 重复运行不会重复插入同一URL或同一内容哈希。（已验证）
- 网络失败时工作流给出清晰日志，而不是直接崩溃。（已验证）

### 10.5 阶段九：统一LLM客户端与API配置

目标：先做一个统一的模型调用接口，再逐步替换各阶段的离线占位逻辑。

当前状态：已于2026-05-01完成阶段九。`1-Workflow_Files/llm_client.py` 已提供统一LLM调用入口；`1-Workflow_Files/.env.example` 已切换为DeepSeek V4默认配置；无API key或endpoint时会自动返回结构化离线fallback，不影响当前MVP运行。

密钥安全规则：`1-Workflow_Files/.env` 只允许用户本人本地编辑，不允许任何AI开发/测试流程读取、打印、复制、总结或上传该文件内容。后续测试真实LLM时，只能使用 `llm_client.py --print-config --require-online` 这类脱敏命令确认 key 是否配置成功；不得运行 `cat .env`、`sed ... .env`、`grep/rg ... .env`，也不得要求用户把API key发送到对话中。

建议新增模块：

```text
1-Workflow_Files/llm_client.py
1-Workflow_Files/.env.example
```

具体行动：

1. 在 `.env.example` 中列出需要的环境变量，例如：
   - `DEEPSEEK_API_KEY`
   - `DEEPSEEK_API_ENDPOINT`
   - `LLM_PROVIDER`
   - `LLM_MODEL`
2. 在 `llm_client.py` 中封装：
   - API key读取
   - 请求发送
   - JSON输出解析
   - 重试与超时
   - 错误日志
   - fallback到离线逻辑
   - 脱敏配置检查，日志中只显示API key是否存在，不显示真实key
3. 所有阶段脚本不要直接写API请求，而是统一调用 `llm_client.py`。

验收标准：

- 没有API key时，系统自动使用离线逻辑。
- 有API key时，可以用一个最小测试Prompt拿到模型返回。
- 模型返回必须能解析为结构化JSON，解析失败要记录日志。

### 10.6 阶段十：逐步替换LLM占位逻辑

目标：不要一次性改完所有阶段，而是按风险从低到高逐个替换。

当前状态：已于2026-05-02完成阶段十。阶段二新闻摘要、阶段三相关性评分、阶段三信息分类和阶段五LinkedIn内容生成均已接入统一 `llm_client.py`，并新增全局 `--llm-mode offline|auto|online`。默认模式保持 `offline`，确保无网络、无API key时仍可运行稳定MVP。

推荐顺序：

| 顺序 | 替换环节 | 原逻辑 | 升级后 |
|------|------|------|------|
| 1 | 新闻摘要 | 离线取前两句 | LLM生成摘要、关键词、决策信号 |
| 2 | 相关性评分 | 规则+确定性打分 | 规则过滤后由LLM按rubric评分 |
| 3 | 信息分类 | 关键词分类 | LLM输出主线分类、辅助标签、理由 |
| 4 | LinkedIn生成 | 模板生成 | LLM按KOL checklist生成更自然的内容 |
| 5 | KOL分析 | 静态画像 | 可选：输入真实KOL样本后由LLM分析 |

具体行动：

1. 每次只替换一个阶段。
2. 替换后保留同样的数据库字段，不破坏下游模块。
3. 每个LLM输出都要求JSON格式，严禁只返回自由文本。
4. 每个阶段都保留 `--offline` 或 fallback 机制。
5. 任何调试日志、错误信息、进度报告和Prompt记录都不得包含真实API key或 `.env` 文件内容。

验收标准：

- 阶段二到阶段五均能通过统一参数进入LLM模式；真实API由用户填写 `.env` 后使用 `--llm-mode online` 验证。
- 总控脚本可以通过参数选择离线模式或LLM模式。（已完成）
- 数据库中的 `prompt_version`、`model_provider` 能反映真实模型版本或离线fallback状态。（已完成）

### 10.7 阶段十一：接入图片生成与内容归档

目标：补齐作业中“text and image”的真实图片能力，让每篇LinkedIn内容都能附带一张可用视觉图。

当前状态：已于2026-05-02完成阶段十一。新增 `6_image_generation.py`，支持 `--image-mode offline|auto|online`；默认离线模式生成本地16:9 SVG fallback，`auto/online` 可接MiniMax图片API。两篇最终帖子Markdown已写入图片文件路径、生成时间、模型名称和Prompt，并已生成按日期分组的归档包。

具体行动：

1. 在阶段五中保留现有 `visual_prompt`。（已完成）
2. 新增图片生成脚本或函数，例如 `6_image_generation.py`。（已完成）
3. 调用图片生成API生成16:9图片；无API key时生成本地fallback图片。（已完成）
4. 图片保存到：（已完成）

```text
AI_Geopolitical_Risk_Workflow_Homework_Delivery/3-Final_LinkedIn_Content/images/
```

5. 在最终帖子Markdown中写入图片文件路径、生成时间、模型名称和Prompt。（已完成）
6. 归档成品到：

```text
AI_Geopolitical_Risk_Workflow_Homework_Delivery/3-Final_LinkedIn_Content/archive/YYYY-MM-DD/
```

验收标准：

- 每篇最终LinkedIn帖子至少对应一张本地图片文件。（已验证）
- 图片风格符合专业LinkedIn视觉，不含logo、不含文字水印、不使用夸张灾难图。（离线fallback已遵守）
- 即使图片生成失败，文本内容仍然可以正常生成。（已通过fallback设计保护）

### 10.8 阶段十二：每日定时运行与人工审核

目标：把系统从“手动运行脚本”升级为“每日自动生成候选简报，但仍由人审核发布”。

当前状态：已于2026-05-02完成阶段十二。新增 `7_daily_run_review.py`，可包装总控脚本生成 `daily_outputs/YYYY-MM-DD/` 审核包；SQLite新增 `daily_workflow_runs` 和 `review_queue_items`；离线验收 Run ID `daily_20260502_153834_3c00c0d5`，`Overall success: True`，生成2条 `pending_review` 候选内容。

具体行动：

1. 先用本地 `cron`、macOS `launchd` 或手动脚本模拟每日运行。（已完成脚本与cron示例，未静默安装系统级后台任务）
2. 每日运行顺序：

```text
RSS/API抓取
-> 摘要
-> 路由
-> 分类
-> 内容生成
-> 图片生成
-> 输出候选内容
-> 人工审核
```

3. 新增每日输出目录：（已完成）

```text
daily_outputs/YYYY-MM-DD/
```

4. 每日只生成“候选内容”，不自动发布LinkedIn。（已完成）
5. 人工审核后再复制到LinkedIn，避免事实错误、语气不当或来源不足。（已固化为审核清单与 `pending_review` 状态）

验收标准：

- 每天运行后能看到当天抓取数量、保留数量、分类数量、生成候选帖数量。（已验证）
- 失败源、失败Prompt、失败图片生成均有日志。（已通过总控日志、阶段日志和每日审核日志记录）
- 人工审核前不自动对外发布。（已通过脚本边界和审核包说明固化）

### 10.9 阶段十三到十九：90+评分修正路线

> 本段为2026-05-02根据评分AI反馈新增的修正路线。原“阶段十三：向量库、看板、邮件简报等可选增强”整体顺延到阶段十九。

当前核心目标不是继续堆新功能，而是把已有工作流从“能跑通”提升为“数据血缘闭环、事实约束强、每日审核可解释”的90+版本。后续AI接手时应优先按阶段十三到十八修复评分扣分点，再考虑阶段十九可选增强。

| 阶段 | 名称 | 核心扣分点 | 优先级 |
|------|------|------|------|
| 阶段十三 | Daily Run数据血缘闭环修复 | Stage 12候选内容引用历史sample而不是本次RSS run | P0 |
| 阶段十四 | Evidence Grounding与事实约束 | LinkedIn内容出现unsupported claims、未证实数字/国家/机构 | P0 |
| 阶段十五 | Daily Review透明度增强 | review queue未充分展示过滤项、拒绝理由和审计解释 | P1 |
| 阶段十六 | KOL Reverse Engineering修正 | KOL分析偏静态画像，样本来源表述需更谨慎 | P1 |
| 阶段十七 | 图片与结果包一致性修复 | 图片状态、fallback、prompt与source evidence需要更透明 | P1 |
| 阶段十八 | 最终报告修订与回归验证 | 报告需说明data lineage、grounding、daily review修复 | P1 |
| 阶段十九 | 可选增强 | 向量库、看板、邮件/Slack简报、多版本内容 | P2 |

#### 阶段十三：Daily Run数据血缘闭环修复

目标：确保 `result/YYYY-MM-DD/manifest.json`、`review_queue.md`、candidate markdown中的 `source_news_ids` 和 `source_titles` 只来自本次 daily run，不再混用历史sample data。

优先修改文件：

```text
1-Workflow_Files/1_news_monitoring.py
1-Workflow_Files/2_relevance_router.py
1-Workflow_Files/3_information_classification.py
1-Workflow_Files/5_linkedin_content_generation.py
1-Workflow_Files/7_daily_run_review.py
1-Workflow_Files/0_main_workflow.py
1-Workflow_Files/database_config/sqlite_db_init.sql
```

实施要点：

1. Stage 2 ingestion必须记录每条 `news_items` 属于哪个 `ingestion_run_id`、`workflow_run_id`、`daily_run_id`。
2. Stage 3 relevance routing只处理本次run新增或指定的news IDs，不能默认从数据库最早记录切片。
3. Stage 3B classification只分类本次run保留下来的items。
4. Stage 5 content generation只基于本次workflow/daily run的classified items生成候选。
5. Stage 12输出必须标明每篇candidate来源：`rss_current_run`、`local_sample_baseline` 或 `fallback`。
6. 如果本次RSS没有足够相关内容，应输出 `no_candidate_generated_today`，不能回退旧样例冒充今日结果。
7. Schema修改必须migration-safe，可优先新增关联表，例如 `run_item_lineage`，或谨慎使用可重复执行的ALTER逻辑。

验收标准：

- 重新运行Stage 12后，candidate source IDs全部属于本次daily run。
- 本次RSS无相关内容时，review queue明确显示no-candidate状态。
- sample baseline与RSS production-like path不能混用。

#### 阶段十四：Evidence Grounding与事实约束

目标：消除unsupported claims，禁止生成证据中没有的数字、国家、公司、机构、引用或预测区间。

优先修改文件：

```text
1-Workflow_Files/5_linkedin_content_generation.py
2-Prompt_Design_Samples/linkedin_post_generation_prompt.txt
2-Prompt_Design_Samples/image_generation_prompt.txt
```

实施要点：

1. Prompt必须明确：`do not introduce facts not present in source_records`。
2. LinkedIn post只能使用 `evidence_basis` 中明确出现的title、source、summary、content、published_at。
3. 增加 `validate_post_against_evidence()` 或等价后处理：
   - 检查unsupported numbers。
   - 检查unsupported named entities。
   - 检查unsupported source names。
   - 修复 `#AInfrastructure` 为 `#AIInfrastructure`。
4. 如果LLM输出不通过校验，应回退到更保守模板或标记 `factual_validation_failed`，不能悄悄输出。

验收标准：

- 两篇候选帖不得包含evidence中没有的具体数字、国家、公司、机构或引用。
- candidate markdown和manifest中显示factual validation result。

#### 阶段十五：Daily Review透明度增强

目标：让老师能清楚看到系统每天抓了什么、保留什么、过滤什么、为什么过滤。

优先修改文件：

```text
1-Workflow_Files/2_relevance_router.py
1-Workflow_Files/7_daily_run_review.py
```

实施要点：

1. candidate markdown中展示每条source的：
   - relevance rationale
   - classification rationale
   - matched terms
   - score breakdown
2. review_queue.md新增 `Filtered Today` 区块，列出本次run被过滤RSS内容、filter reason和score。
3. 对被过滤的RSS内容生成short rejection summary。
4. review_queue.md必须包含：
   - Daily metrics
   - Candidate posts
   - Source evidence
   - Filtered/rejected items with reasons
   - Factual validation result
   - Manual review required policy

验收标准：

- 即使无候选内容，review queue也能展示当天监控和过滤链路。

#### 阶段十六：KOL Reverse Engineering修正

目标：让KOL研究更像真实reverse engineering，同时避免声称分析了项目中没有保存的具体帖子。

优先修改文件：

```text
1-Workflow_Files/4_linkedin_analysis.py
3-Final_LinkedIn_Content/LinkedIn_Post_Style_Anatomy_Checklist.md
2-Prompt_Design_Samples/kol_style_analysis_prompt.txt
```

实施要点：

1. 明确2-5位KOL的选择理由。
2. 每位KOL补充五项表格：
   - hook
   - structure
   - credibility
   - engagement
   - style
3. 如果没有真实样本文件或来源链接，统一写成：

```text
representative public style analysis based on known public writing patterns
```

4. 避免写成“分析了某篇具体帖子”。

验收标准：

- KOL部分更可信、更像结构化拆解，且不夸大样本来源。

#### 阶段十七：图片与结果包一致性修复

目标：确保图片路径、archive、candidate visual都能打开，并如实记录图片API或fallback状态。

优先修改文件：

```text
1-Workflow_Files/6_image_generation.py
1-Workflow_Files/7_daily_run_review.py
```

实施要点：

1. manifest记录：
   - `image_status`
   - `fallback_used`
   - `provider`
   - `model`
   - 脱敏 `api_error` 摘要
2. result assets只复制本次run图片。
3. 图片prompt必须与当前source evidence和post topic对齐，避免泛泛抽象。
4. 保留manual review policy，不自动发布。

验收标准：

- `result/YYYY-MM-DD/assets/` 图片与candidate一一对应。
- fallback时manifest如实记录。

#### 阶段十八：最终报告修订与回归验证

目标：把阶段十三到十七的修复写进最终交付说明，并跑一次完整验证。

优先修改文件：

```text
4-Progress_Report/Progress_Report_Final.md
STATUS.md
Implementation_Roadmap.md
1-Workflow_Files/workflow_architecture.md
```

实施要点：

1. 报告说明已修复：
   - data lineage
   - evidence grounding
   - daily review transparency
2. 明确：
   - offline sample = demo/sample baseline
   - daily RSS = production-like path
   - 两者结果不能混用
3. 重新运行主流程和daily review。

验收命令：

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/7_daily_run_review.py --output-root result --stage2-input-mode rss --rss-limit 2 --llm-mode auto --image-mode auto --stage10-max-items 2 --stage11-max-items 2
```

成功标准：

- `Overall success: True` 或合理的 `no_candidate_generated_today`。
- candidate source IDs来自本次run。
- no unsupported claims。
- review queue有filtered/rejected items。
- manifest lineage清楚。

#### 阶段十九：可选增强能力

原阶段十三整体顺延到阶段十九。这些不是90+修正的优先任务，只有阶段十三到十八完成并通过回归后再考虑。

| 增强方向 | 价值 | 建议时机 |
|------|------|------|
| Chroma向量库 | 支持长期案例检索、相似事件召回 | 数据量超过100条后 |
| Streamlit/Gradio看板 | 方便查看新闻、分类、候选帖 | Daily lineage修复后 |
| 邮件/飞书/Slack简报 | 每日推送候选内容 | 人工审核流程稳定后 |
| 来源可信度评分 | 区分官方报告、媒体、博客、社交内容 | 真实源数量增加后 |
| 多版本内容生成 | 高管摘要版、投资人深度版、政策分析版 | Evidence guard稳定后 |

### 10.10 推荐执行顺序

下一步不要先做可选增强。推荐按下面顺序一轮一轮推进评分修正：

1. **阶段十三：Daily Run数据血缘闭环修复**。这是最严重扣分点，必须先做。
2. **阶段十四：Evidence Grounding与事实约束**。防止unsupported claims。
3. **阶段十五：Daily Review透明度增强**。补足过滤、拒绝和审计解释。
4. **阶段十六：KOL Reverse Engineering修正**。提高研究可信度。
5. **阶段十七：图片与结果包一致性修复**。确保图片、manifest和candidate一致。
6. **阶段十八：最终报告修订与回归验证**。把修复写进最终报告并跑完整验证。
7. **阶段十九：可选增强**。向量库、看板、邮件简报等顺延到最后。

### 10.11 阶段九完成与阶段十起点

阶段九已完成以下三件事；下一次开发应从阶段十“先替换新闻摘要”开始：

1. **新增 `.env.example`**：已完成，当前默认DeepSeek V4，列出 `DEEPSEEK_API_KEY`、`DEEPSEEK_API_ENDPOINT`、`LLM_PROVIDER`、`LLM_MODEL` 等环境变量。
2. **新增 `llm_client.py`**：已完成，统一封装API key读取、请求发送、结构化JSON解析、重试、超时与离线fallback。
3. **新增最小LLM连通性测试**：已完成，无API key时返回结构化fallback；用户填写 `.env` 后可用 `--require-online` 验证真实API。

### 10.12 阶段十完成与阶段十一起点

阶段十已完成以下内容；下一次开发应从阶段十一“图片生成与内容归档”开始：

1. **新增 `llm_stage_utils.py`**：统一管理 `offline`、`auto`、`online` 三种LLM运行模式。
2. **完成文本LLM替换接线**：`1_news_monitoring.py`、`2_relevance_router.py`、`3_information_classification.py`、`5_linkedin_content_generation.py` 均可通过统一LLM客户端运行。
3. **升级总控脚本**：`0_main_workflow.py --llm-mode offline|auto|online` 可统一控制阶段二、阶段三和阶段五的LLM行为。
4. **离线回归通过**：Run ID `run_20260502_092016_e351f378`，`Overall success: True`，数据库健康检查全部 `PASS`。
5. **模型边界**：DeepSeek V4继续用于文本LLM任务；阶段十一如果生成真实图片，应单独选择图片生成模型或服务。

### 10.13 阶段十一完成与阶段十二起点

阶段十一已完成以下内容；下一次开发应从阶段十二“每日定时运行与人工审核”开始：

1. **新增 `6_image_generation.py`**：从 `linkedin_content_results` 读取最终帖子和图片Prompt，生成图片并写入归档。
2. **扩展图片模式**：`--image-mode offline|auto|online`，默认离线fallback，用户填写MiniMax key后可用online模式测试真实图片。
3. **扩展数据库审计**：新增 `image_generation_results` 和 `image_generation_runs`。
4. **升级总控脚本**：`0_main_workflow.py --include-stage11 --image-mode offline|auto|online` 可选择是否跑阶段十一。
5. **离线集成验证通过**：Run ID `run_20260502_113929_cab3e7e7`，`Overall success: True`，图片与归档检查全部 `PASS`。
6. **下一阶段边界**：阶段十二只做每日运行与人工审核队列，不做自动LinkedIn发布。

### 10.14 阶段十二完成与阶段十三起点

阶段十二已完成以下内容；下一步进入阶段十三“Daily Run数据血缘闭环修复”，原可选增强顺延到阶段十九：

1. **新增 `7_daily_run_review.py`**：包装 `0_main_workflow.py --include-stage11`，生成每日候选内容审核包。
2. **新增每日输出目录**：`daily_outputs/YYYY-MM-DD/`，包含 `review_queue.md`、`review_queue.csv`、`manifest.json`、候选稿和图片资产。
3. **扩展数据库审计**：新增 `daily_workflow_runs` 和 `review_queue_items`，候选内容默认 `pending_review`。
4. **离线验收通过**：Daily Run ID `daily_20260502_153834_3c00c0d5`，Wrapped Workflow Run ID `run_20260502_153835_7de03b80`，错误0条，候选审核项2条。
5. **定时边界**：已提供cron命令示例；当前阶段不静默安装后台任务，不接LinkedIn自动发布。
6. **下一阶段边界**：阶段十三不做可选增强，优先修复daily run数据血缘闭环，确保候选内容来自本次RSS/daily run。

### 10.15 阶段十三完成与阶段十四起点

阶段十三已完成以下内容；下一步进入阶段十四“Evidence Grounding与事实约束”：

1. **新增 `lineage_utils.py`**：集中处理Stage 13 schema migration、`run_item_lineage` 表和lineage mode判断。
2. **修复Stage 2 ingestion血缘**：每条当前run看到的新闻都会写入 `run_item_lineage`；即使被 `content_hash` 去重，也会标记为 `duplicate_seen`。
3. **修复Stage 3A/3B run-scoped处理**：`2_relevance_router.py` 与 `3_information_classification.py` 支持 `--workflow-run-id` / `--daily-run-id`，只处理本次run范围内的items。
4. **修复Stage 5候选生成取数**：`5_linkedin_content_generation.py` 只基于本次workflow/daily run的classified items生成候选；无当前run分类结果时不回捞历史内容。
5. **修复Stage 11图片取数**：`6_image_generation.py` 只处理本次run的content records，避免当前run无候选时复制旧图片。
6. **修复Stage 12审核包**：`7_daily_run_review.py` 与 `0_main_workflow.py` 贯穿 `daily_run_id` / `workflow_run_id`；`manifest.json`、`review_queue.md` 和candidate markdown均展示lineage信息。
7. **无候选成功状态**：当前run没有候选时输出 `no_candidate_generated_today`，并明确说明历史sample内容未被复用。

阶段十三验证结果：

```text
Daily Run ID: daily_20260502_203904_4e5b7da4
Wrapped Workflow Run ID: run_20260502_203905_fa433c16
Overall success: True
candidate_source_ids = [1, 2, 3, 4]
daily_run_lineage_news_ids = [1, 2, 3, 4, 5, 6]
all_candidate_ids_in_daily_lineage = True
lineage_mode = local_sample_baseline
```

no-candidate路径已验证：

```text
Overall success: True
Candidate posts: 0
Review items: 0
Lineage mode: fallback
No-candidate reason: no_candidate_generated_today
Historical sample content was not reused.
```

下一阶段边界：

- 阶段十四只处理事实约束和evidence grounding。
- 不在阶段十四推进向量库、看板、邮件简报等阶段十九可选增强。
- 不读取或打印 `.env`；真实API测试仍使用脱敏命令。

### 10.16 阶段十四完成与阶段十五后置判断

阶段十四已完成以下内容；当前主产品闭环已经具备联网正常使用测试所需的核心能力：

1. **新增事实约束后处理**：`5_linkedin_content_generation.py` 新增 `validate_post_against_evidence()`，生成后检查unsupported numbers、named entities、source names和countries/regions。
2. **证据语料增强**：`evidence_basis` 除title/source/published_at外，增加summary、cleaned content excerpt、url、keywords和classification rationale。
3. **失败不静默放行**：如果LLM或离线模板输出不通过事实校验，系统使用 conservative grounded fallback；若fallback仍失败，则标记 `factual_validation_failed` 并让Stage 5失败。
4. **审核包透明展示**：`review_queue.md`、candidate markdown、`review_queue.csv` 和 `manifest.json` 均写入factual validation result。
5. **总控健康检查**：`0_main_workflow.py` 新增 `stage14_factual_validation_passed`。
6. **Prompt约束升级**：post和image prompt都明确不得引入source_records中没有的事实、国家、公司、机构、来源名、引用或数据标签。

阶段十四验证结果：

```text
Daily Run ID: daily_20260502_210317_49a0162b
Wrapped Workflow Run ID: run_20260502_210317_5f687756
Overall success: True
Candidate posts: 2
Review items: 2
stage14_factual_validation_passed: PASS
factual_validation_status = passed for both candidates
Errors: 0
```

no-candidate路径保持通过：

```text
Overall success: True
Candidate posts: 0
Review items: 0
No-candidate reason: no_candidate_generated_today
Historical sample content was not reused.
```

产品状态判断：

- 当前系统已经具备RSS联网输入、可选在线LLM、可选在线图片、每日审核包、数据血缘和事实约束。
- 因此若目标是“能联网跑通并满足当前主要需求”，阶段十四后可以认为主产品已可进入正常使用测试。
- 阶段十五到十八仍有助于提高作业评分、解释透明度和最终报告质量，但不再是主流程联网可用性的阻塞项；阶段十五可以后置。
