# Prompt优化记录

> 使用环节：阶段六 - 工作流、Prompt优化与进度报告。  
> 版本：v1.0 offline MVP  
> 更新日期：2026-04-30

## 1. 总体优化方向

本项目的Prompt优化不是简单改写措辞，而是围绕“范围控制、判断一致性、业务价值和输出可复盘”四个目标持续收窄。

最重要的优化，是从原来的“泛AI新闻与全产业链地缘风险内容系统”，收窄为“AI基建地缘风险与关键矿产供应链决策洞察工作流”。这个改变使Prompt不再试图覆盖所有AI动态，而是明确服务AI基建投资者、数据中心运营商和跨国AI企业战略/供应链负责人。

## 2. 新闻摘要Prompt优化

| 版本 | 原始倾向 | 优化后规则 | 改进效果 |
|------|----------|------------|----------|
| 初始方向 | 总结AI新闻本身 | 摘要必须提取对AI基建、能源、芯片、供应链或跨境风险的决策信号 | 摘要更适合进入后续路由，不会停留在泛新闻复述 |

关键优化：

- 要求输出“事件摘要 + 决策相关信号”。
- 强制保留来源、时间、关键词和摘要。
- 对无网络环境增加离线摘要占位逻辑，保证流程可测试。

对应文件：

- `2-Prompt_Design_Samples/news_summarization_prompt.txt`

## 3. 相关性路由Prompt优化

| 版本 | 原始倾向 | 优化后规则 | 改进效果 |
|------|----------|------------|----------|
| 初始方向 | 让LLM直接判断“是否相关” | 先规则过滤，再按权重打分 | 降低LLM主观波动，保留可解释的过滤依据 |

关键优化：

- 规则层要求同时命中AI基建/供应链信号与地缘/跨境风险信号。
- 评分层采用四项权重：
  - 40% 商业影响。
  - 25% 证据支撑。
  - 20% 目标受众匹配。
  - 15% 核心链条相关性。
- 阈值固定为7分，低于7分过滤。
- 每条结果必须输出判断理由和分项得分。

对应文件：

- `2-Prompt_Design_Samples/relevance_routing_prompt.txt`

## 4. 信息分类Prompt优化

| 版本 | 原始倾向 | 优化后规则 | 改进效果 |
|------|----------|------------|----------|
| 初始方向 | 5个宽泛分类 | 2个主线分类 + 3个辅助标签 | 分类边界更清晰，后续内容生成更稳定 |

关键优化：

- 主线分类只保留：
  - AI算力基础设施地缘风险。
  - AI关键矿产供应链与地缘政治。
- 芯片出口管制、区域冲突影响、全球AI治理改为辅助标签。
- 每条保留信息只分配一个主线分类，避免内容生成主题发散。

对应文件：

- `2-Prompt_Design_Samples/information_classification_prompt.txt`

## 5. KOL分析Prompt优化

| 版本 | 原始倾向 | 优化后规则 | 改进效果 |
|------|----------|------------|----------|
| 初始方向 | 模仿KOL语气 | 提炼可迁移结构，不直接模仿个人风格 | 避免机械仿写，同时获得可复用的内容规范 |

关键优化：

- 拆解维度固定为Hook、结构、公信力、互动方式、整体风格。
- 输出从“风格描述”升级为“内容生成约束清单”。
- 明确禁止直接模仿KOL个人声音，只迁移结构方法。

对应文件：

- `2-Prompt_Design_Samples/kol_style_analysis_prompt.txt`
- `2-Prompt_Design_Samples/linkedin_content_constraints_prompt.txt`
- `3-Final_LinkedIn_Content/LinkedIn_Post_Style_Anatomy_Checklist.md`

## 6. LinkedIn生成Prompt优化

| 版本 | 原始倾向 | 优化后规则 | 改进效果 |
|------|----------|------------|----------|
| 初始方向 | 生成普通LinkedIn文章 | 生成决策简报式帖子 | 内容更符合投资者和企业高管阅读场景 |

关键优化：

- 固定输出结构：
  - Hook。
  - What happened。
  - Why it matters for AI infrastructure。
  - Business implications。
  - Signals to watch。
  - Closing question。
- 每篇必须包含目标受众和语气定位。
- 每篇必须引用来源证据，避免空泛观点。
- 同步生成配图Prompt，但不自动发布LinkedIn。

对应文件：

- `2-Prompt_Design_Samples/linkedin_post_generation_prompt.txt`
- `2-Prompt_Design_Samples/image_generation_prompt.txt`
- `3-Final_LinkedIn_Content/Category_1_AI_Infrastructure_Risk_Post.md`
- `3-Final_LinkedIn_Content/Category_2_AI_Mineral_SupplyChain_Post.md`

## 7. 工作流级优化

| 问题 | 优化动作 | 结果 |
|------|----------|------|
| 范围过大 | 从全产业链收窄到AI基建和关键矿产 | 项目更像可交付的信息系统MVP |
| 信息源不稳定 | 使用本地样例数据 + RSS/API预留接口 | 无网络环境也能演示完整流程 |
| LLM结果不可复现 | 当前阶段使用离线确定性逻辑，保留LLM接口 | 用户测试时结果稳定，后续可替换为Minimax M2.7 |
| 内容容易泛泛而谈 | 引入KOL结构清单和质量自检 | 最终帖子更像专业决策简报 |
| 过程不易审计 | 每个阶段写入SQLite运行表和日志 | 可追踪每次处理数量、错误数和输出文件 |

## 8. 后续Prompt升级方向

1. 接入真实Minimax M2.7后，保留同样的JSON输出格式，减少代码改动。
2. 为不同来源类型设计不同摘要Prompt，例如企业公告、智库报告、媒体报道和投资机构报告。
3. 增加“反事实检查”Prompt，要求模型标注哪些结论只是推断，哪些由来源直接支持。
4. 增加“重复主题合并”Prompt，将多条相似信息合并成一个更有判断力的内容选题。
5. 增加“高管摘要版”和“投资人深度版”两套LinkedIn输出风格。
