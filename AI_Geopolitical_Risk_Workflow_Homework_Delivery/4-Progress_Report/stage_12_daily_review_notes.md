# 阶段十二记录：每日定时运行与人工审核

> 日期：2026-05-02  
> 阶段目标：把现有手动总控脚本升级为“每日生成候选内容 + 人工审核队列”的运行方式，同时继续禁止自动发布LinkedIn。

## 完成内容

1. 新增 `1-Workflow_Files/7_daily_run_review.py`。
   - 包装调用 `0_main_workflow.py`。
   - 默认执行每日RSS输入、文本离线fallback、图片离线fallback。
   - 支持 `--stage2-input-mode local_sample|rss|all`、`--llm-mode offline|auto|online`、`--image-mode offline|auto|online`。
   - 每次运行后生成 `daily_outputs/YYYY-MM-DD/` 人工审核包。

2. 新增每日输出目录：

```text
AI_Geopolitical_Risk_Workflow_Homework_Delivery/daily_outputs/YYYY-MM-DD/
├── review_queue.md
├── review_queue.csv
├── manifest.json
├── candidates/
│   ├── category_1_ai_infrastructure_risk_candidate.md
│   └── category_2_ai_critical_minerals_supply_chain_candidate.md
└── assets/
    └── generated_or_fallback_images
```

3. 新增SQLite审计表。
   - `daily_workflow_runs`：保存每日运行的抓取、保留、分类、候选帖、图片、审核项和错误计数。
   - `review_queue_items`：保存每条候选内容的 `pending_review` 状态、候选稿路径、图片路径、来源新闻标题和审核优先级。

4. 人工审核包内容。
   - `review_queue.md`：每日总览、指标、日志路径、候选内容列表和失败排查入口。
   - `candidates/*.md`：每条候选LinkedIn内容的来源证据、正文、图片、Prompt和人工审核清单。
   - `manifest.json`：结构化交接清单，便于后续接看板或邮件简报。
   - `review_queue.csv`：可用表格方式查看候选队列。

5. 发布边界。
   - 阶段十二不接LinkedIn OAuth。
   - 不做浏览器自动发帖。
   - 不自动对外发布内容。
   - 所有候选内容默认状态均为 `pending_review`，必须由人工审核后再复制到LinkedIn。

## 测试命令

语法检查：

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/homework2_pycache python3 -m py_compile \
  AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/7_daily_run_review.py \
  AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/0_main_workflow.py \
  AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/api_config.py
```

完全离线验收：

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/7_daily_run_review.py \
  --stage2-input-mode local_sample \
  --llm-mode offline \
  --image-mode offline
```

验证结果：

- Stage 12 daily run ID：`daily_20260502_153834_3c00c0d5`
- Wrapped workflow run ID：`run_20260502_153835_7de03b80`
- `Overall success: True`
- News seen：6
- Items kept：5
- Items classified：5
- Candidate posts：2
- Images generated：2
- Review items：2
- Errors：0

输出位置：

```text
AI_Geopolitical_Risk_Workflow_Homework_Delivery/daily_outputs/2026-05-02/
```

核心审核文件：

```text
AI_Geopolitical_Risk_Workflow_Homework_Delivery/daily_outputs/2026-05-02/review_queue.md
```

## 日常运行方式

默认每日RSS模式：

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/7_daily_run_review.py
```

无网络或课堂演示时使用离线模式：

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/7_daily_run_review.py \
  --stage2-input-mode local_sample \
  --llm-mode offline \
  --image-mode offline
```

用户填写 `.env` 后的小批量真实LLM/图片验收：

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/7_daily_run_review.py \
  --stage2-input-mode rss \
  --rss-limit 2 \
  --llm-mode auto \
  --image-mode auto \
  --stage10-max-items 2 \
  --stage11-max-items 2
```

## 本地定时示例

cron示例，每天早上8点生成审核包：

```cron
0 8 * * * cd /Users/jing/Desktop/some_code/GenAI_Coding/Homework2/Homework2 && /usr/bin/python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/7_daily_run_review.py --stage2-input-mode rss --rss-limit 2 --llm-mode offline --image-mode offline
```

macOS `launchd` 也可以调用同一条命令；当前阶段先交付可运行脚本和审核包，不自动安装系统级定时任务，避免在用户机器上静默新增后台任务。

## 安全边界

- 不读取、打印、复制或总结用户私密 `.env` 内容。
- 默认离线验收不需要API key。
- `auto/online` 模式仍通过既有 `llm_client.py` 和 `6_image_generation.py` 的脱敏配置机制。
- 阶段十二只生成候选内容和审核材料，不做自动发布。

