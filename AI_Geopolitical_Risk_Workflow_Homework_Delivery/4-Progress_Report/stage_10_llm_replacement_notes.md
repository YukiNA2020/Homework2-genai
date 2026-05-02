# 阶段十记录：LLM替换摘要、评分、分类与生成

> 日期：2026-05-02  
> 阶段目标：把阶段二到阶段五的核心文本判断与生成环节接入统一 `llm_client.py`，同时保留离线fallback。

## 完成内容

1. 新增 `1-Workflow_Files/llm_stage_utils.py`。
   - 统一提供 `--llm-mode offline|auto|online` 三种模式。
   - `offline`：不调用API，使用确定性fallback。
   - `auto`：配置可用则调用LLM，否则fallback。
   - `online`：要求真实API成功，失败则报错，适合用户填写 `.env` 后测试。

2. 升级 `1_news_monitoring.py`。
   - 新闻摘要、关键词和决策信号可由LLM生成。
   - 输出仍写入原有 `news_items.summary` 与 `news_items.keywords` 字段。
   - 默认 `--llm-mode offline`，保护无网络、无API key演示能力。

3. 升级 `2_relevance_router.py`。
   - 保留第一层规则过滤。
   - 通过规则门槛后，可由LLM按0-10分rubric输出相关性分数、保留/过滤决策、评分拆解与理由。
   - `prompt_version` 与 `model_provider` 会写入 `relevance_routing_results`。

4. 升级 `3_information_classification.py`。
   - 可由LLM输出主线分类、辅助标签、置信度与分类依据。
   - 输出被限制在既有两个主分类与三个辅助标签内，避免模型自创分类。
   - `prompt_version` 与 `model_provider` 会写入 `classification_results`。

5. 升级 `5_linkedin_content_generation.py`。
   - 可由LLM生成LinkedIn决策简报正文、图片Prompt与质量自检。
   - 仍使用SQLite中的分类结果和来源证据，不允许模型编造来源、数字或发布时间。
   - `prompt_version` 与 `model_provider` 会写入 `linkedin_content_results`，最终Markdown也会展示。

6. 升级 `0_main_workflow.py`。
   - 新增全局 `--llm-mode offline|auto|online`。
   - 默认 `offline`，保证原有稳定MVP一键运行不被破坏。
   - 新增 `--stage10-max-items`，用于小批量online验收，避免历史RSS记录全量调用时拖慢测试。

7. 新增分阶段模型覆盖能力。
   - 默认读取 `.env` 中的 `LLM_MODEL`。
   - 可用 `SUMMARIZATION_LLM_MODEL`、`ROUTING_LLM_MODEL`、`CLASSIFICATION_LLM_MODEL`、`CONTENT_LLM_MODEL` 分别覆盖阶段二摘要、阶段三A评分、阶段三B分类、阶段五内容生成模型。
   - 如果需要快速批量评分，可将全局 `LLM_MODEL` 或 `ROUTING_LLM_MODEL` 设置为 `deepseek-v4-flash`。

## 测试命令

语法检查：

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/homework2_pycache python3 -m py_compile \
  AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/llm_stage_utils.py \
  AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/0_main_workflow.py \
  AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/1_news_monitoring.py \
  AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/2_relevance_router.py \
  AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/3_information_classification.py \
  AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/5_linkedin_content_generation.py
```

离线回归：

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/0_main_workflow.py --llm-mode offline
```

验证结果：

- Run ID：`run_20260502_092016_e351f378`
- `Overall success: True`
- 阶段二到阶段五全部 `OK`
- 数据库健康检查全部 `PASS`

## 用户后续真实API测试

用户自行填写 `1-Workflow_Files/.env` 后，先运行脱敏连通性检查：

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/llm_client.py --print-config --require-online
```

连通性通过后，再运行真实LLM严格模式：

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/0_main_workflow.py --llm-mode online
```

日常测试也可使用：

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/0_main_workflow.py --llm-mode auto
```

## 真实联网小批量验收记录

2026-05-02 用户将网络和模型调整为 `deepseek-v4-flash` 后，完成脱敏连通性与阶段十小批量online验收。

脱敏连通性：

- `provider: deepseek`
- `model: deepseek-v4-flash`
- `api_key_configured: true`
- `API succeeded: True`
- `Used fallback: False`

小批量online全流程：

```bash
env LLM_TIMEOUT_SECONDS=120 python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/0_main_workflow.py --llm-mode online --stage10-max-items 1
```

验证结果：

- Run ID：`run_20260502_112420_efc3355a`
- `Overall success: True`
- Stage 2 online摘要：OK，7.20s，errors=0
- Stage 3A online相关性评分：OK，7.41s，errors=0
- Stage 3B online分类：OK，8.00s，errors=0
- Stage 5 online内容生成：OK，23.85s，errors=0
- 数据库健康检查全部 `PASS`

结论：`deepseek-v4-flash` 比 `deepseek-v4-pro` 更适合当前阶段十的小批量和后续批量评分/分类验收。若后续追求最终LinkedIn文案质量，可以仅将 `CONTENT_LLM_MODEL` 覆盖为 `deepseek-v4-pro`。

## 模型选择说明

阶段十只涉及文本摘要、结构化评分、文本分类和LinkedIn正文生成。DeepSeek V4 Flash当前更适合作为快速结构化JSON模型使用。用户提到的多模态能力不足不影响阶段十；如果阶段十一要生成真实图片，建议单独选择更适合图像生成的模型或服务，不强行让DeepSeek V4承担多模态任务。

## 安全边界

- 不读取、打印、复制或总结用户私密 `.env` 内容。
- 不把真实API key写入Markdown、日志或对话。
- 日志只允许记录 `available`、`api_key_configured` 等脱敏状态。
- 默认离线模式必须长期保留。
