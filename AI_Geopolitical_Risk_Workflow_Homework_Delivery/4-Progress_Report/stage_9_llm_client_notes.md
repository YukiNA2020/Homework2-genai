# 阶段九记录：统一LLM客户端与API配置

> 日期：2026-05-01  
> 阶段目标：先建立统一LLM调用入口，不直接改写阶段二到阶段五业务逻辑。

## 完成内容

1. 新增 `1-Workflow_Files/llm_client.py`。
   - 统一读取 `.env` 与当前进程环境变量。
   - 支持 API key、endpoint、provider、model、timeout、retry、temperature、max tokens 等配置。
   - 使用标准库发送 chat-completions 风格请求。
   - 强制要求业务输出可解析为结构化 JSON。
   - API key 或 endpoint 缺失时自动使用离线 fallback。
   - API 调用失败或模型返回非 JSON 时，可通过 `LLM_FALLBACK_ON_ERROR=true` 回退到离线 JSON。

2. 新增 `1-Workflow_Files/.env.example`。
   - 当前默认DeepSeek V4，包含 `DEEPSEEK_API_KEY`、`DEEPSEEK_API_ENDPOINT`、`LLM_PROVIDER`、`LLM_MODEL`、`LLM_API_STYLE` 等配置项。
   - `.env` 不提交，项目根目录 `.gitignore` 已包含 `.env`。

3. 更新 `1-Workflow_Files/api_config.py`。
   - 新增 `LLM_ENV_PATH`、`LLM_ENV_EXAMPLE_PATH`。
   - 默认真实LLM配置切换为DeepSeek V4，推荐模型为 `deepseek-v4-pro`。
   - 保留现有阶段二到阶段五的离线逻辑，不提前进入阶段十。

## API Key安全规则

`1-Workflow_Files/.env` 是用户本地私密文件，只能由用户本人编辑。后续AI开发、测试或代码审查必须遵守：

- 不读取、打印、复制、总结或上传 `.env` 内容。
- 不运行 `cat .env`、`sed ... .env`、`grep/rg ... .env` 等会暴露密钥的命令。
- 不要求用户把API key粘贴到对话、Markdown、日志或进度报告中。
- 只使用脱敏命令测试真实LLM，例如 `llm_client.py --print-config --require-online`。
- 日志和报告只能记录 `api_key_configured: true/false`、`endpoint_configured: true/false` 这类布尔状态。

## 离线自测命令

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/llm_client.py --print-config
```

预期结果：

- `available: false`
- `reason: API key is not configured`
- `Used fallback: True`
- 输出 JSON 中包含 `stage: stage_9_llm_client`

## 稳定MVP回归

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/0_main_workflow.py
```

验证结果：

- Run ID：`run_20260501_230740_6af9ab82`
- `Overall success: True`
- 阶段二到阶段五全部 `OK`
- 数据库健康检查全部 `PASS`
- 主控日志：`AI_Geopolitical_Risk_Workflow_Homework_Delivery/4-Progress_Report/workflow_running_logs/run_20260501_230740_6af9ab82_main_workflow.log`

## 后续真实API测试命令

用户填写真实配置后，可运行：

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/llm_client.py --print-config --require-online
```

如果 API 正常，预期结果为：

- `API called: True`
- `API succeeded: True`
- `Used fallback: False`
- `Parsed JSON` 能正常解析

## 设计边界

阶段九只完成统一客户端与最小连通性测试，不替换新闻摘要、相关性评分、分类或LinkedIn内容生成逻辑。阶段十再从新闻摘要开始逐步接入真实LLM。
