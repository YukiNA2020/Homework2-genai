# 阶段十三记录：Daily Run数据血缘闭环修复

> 日期：2026-05-02  
> 阶段目标：确保每日审核包中的候选内容只来自本次 workflow/daily run，不再从历史 sample/RSS 结果中回捞旧内容。

## 完成内容

1. 新增 `1-Workflow_Files/lineage_utils.py`。
   - 提供 Stage 13 migration helper。
   - 新增 `run_item_lineage` 表。
   - 对旧 SQLite 数据库执行可重复的 `ALTER TABLE` 迁移。
   - 标准化 `rss_current_run`、`local_sample_baseline`、`fallback` 等 lineage mode。

2. 扩展 SQLite schema。
   - `news_items` 新增 `ingestion_run_id`、`workflow_run_id`、`daily_run_id`。
   - `ingestion_runs`、`routing_runs`、`classification_runs`、`linkedin_content_runs`、`image_generation_runs` 新增 run lineage 字段。
   - `relevance_routing_results`、`classification_results`、`linkedin_content_results`、`image_generation_results` 新增 current-run lineage 字段。
   - `daily_workflow_runs` 新增 `lineage_mode` 与 `no_candidate_reason`。
   - `review_queue_items` 新增 `lineage_mode`。

3. Stage 2 ingestion 血缘修复。
   - 插入新 `news_items` 时记录当前 `ingestion_run_id`、`workflow_run_id`、`daily_run_id`。
   - 即使新闻因为 `content_hash` 去重被跳过，也会写入 `run_item_lineage`，标记为 `duplicate_seen`。
   - 这样当前RSS重复抓取不会丢失“本次run看到了这条新闻”的事实。

4. Stage 3A/3B run-scoped processing。
   - `2_relevance_router.py` 支持 `--workflow-run-id` 与 `--daily-run-id`。
   - `3_information_classification.py` 支持 `--workflow-run-id` 与 `--daily-run-id`。
   - 当传入 run ID 时，只处理当前 run 的 `run_item_lineage` / routing results。

5. Stage 5 candidate generation 血缘修复。
   - `5_linkedin_content_generation.py` 支持 run-scoped 取数。
   - 只从本次 workflow/daily run 的 classified items 生成内容。
   - 若当前 run 没有分类结果，跳过候选生成并返回成功，不再使用历史内容。
   - 输出 Markdown 和 evidence basis 中加入 `lineage_mode`、`source_mode`、run IDs。

6. Stage 11 image/archive 血缘修复。
   - `6_image_generation.py` 支持 run-scoped 读取当前 `linkedin_content_results`。
   - 当前 run 没有候选时不生成图片，也不复用旧图片。
   - archive manifest 中写入 `workflow_run_id`、`daily_run_id`、`lineage_mode`。

7. Stage 12 review package 修复。
   - `7_daily_run_review.py` 将 `daily_run_id` 传入 `0_main_workflow.py`。
   - `0_main_workflow.py` 再将 `workflow_run_id` 与 `daily_run_id` 传入 Stage 2/3/5/11。
   - `select_review_candidates()` 只选择当前 workflow/daily run 的 content/image records。
   - `manifest.json`、`review_queue.md`、candidate markdown 均显示 lineage mode。
   - 当前 run 无候选时输出 `no_candidate_generated_today`，并作为合理成功状态。

## 验证记录

语法检查通过：

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/homework2_pycache python3 -m py_compile \
  AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/lineage_utils.py \
  AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/1_news_monitoring.py \
  AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/2_relevance_router.py \
  AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/3_information_classification.py \
  AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/5_linkedin_content_generation.py \
  AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/6_image_generation.py \
  AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/7_daily_run_review.py \
  AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/0_main_workflow.py
```

离线 daily run 回归：

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/7_daily_run_review.py \
  --stage2-input-mode local_sample \
  --llm-mode offline \
  --image-mode offline \
  --run-date 2026-05-02
```

结果摘要：

- Daily Run ID：`daily_20260502_203904_4e5b7da4`
- Wrapped Workflow Run ID：`run_20260502_203905_fa433c16`
- `Overall success: True`
- News seen：6
- Items kept：4
- Items classified：4
- Candidate posts：2
- Review items：2
- Lineage mode：`local_sample_baseline`
- Errors：0

血缘校验：

```text
candidate_source_ids = [1, 2, 3, 4]
daily_run_lineage_news_ids = [1, 2, 3, 4, 5, 6]
all_candidate_ids_in_daily_lineage = True
source_modes = ['local_sample_baseline']
```

无候选成功路径验证：

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/7_daily_run_review.py \
  --stage2-input-mode local_sample \
  --stage10-max-items 0 \
  --llm-mode offline \
  --image-mode offline \
  --output-root /private/tmp/homework2_stage13_no_candidate_workflow \
  --run-date 2026-05-02
```

结果摘要：

- `Overall success: True`
- Candidate posts：0
- Review items：0
- Lineage mode：`fallback`
- No-candidate reason：`no_candidate_generated_today`
- Historical sample content was not reused.

## 当前人工审核入口

```text
AI_Geopolitical_Risk_Workflow_Homework_Delivery/daily_outputs/2026-05-02/review_queue.md
AI_Geopolitical_Risk_Workflow_Homework_Delivery/daily_outputs/2026-05-02/manifest.json
```

## 交接说明

阶段十三只修复数据血缘和no-candidate行为，不处理事实约束、过滤透明度、KOL reverse engineering和图片一致性的全部细节。下一步进入阶段十四：Evidence Grounding与事实约束。
