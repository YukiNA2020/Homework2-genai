# 阶段十四记录：Evidence Grounding与事实约束

> 日期：2026-05-02  
> 阶段目标：候选LinkedIn帖子不得包含source evidence中没有的数字、国家、公司、机构、来源名或引用；如果生成结果不通过校验，必须回退到保守模板或显式标记失败。

## 完成内容

1. 升级 `5_linkedin_content_generation.py`。
   - 新增 `validate_post_against_evidence()`。
   - 检查 unsupported numbers、named entities、source names、countries/regions。
   - 自动修复 `#AInfrastructure` 为 `#AIInfrastructure`。
   - LLM/离线模板生成后先做 factual validation，再写入Markdown和SQLite。
   - 如果原始输出不通过，自动使用 conservative grounded fallback；如果fallback仍失败，则标记 `factual_validation_failed` 并让阶段失败。

2. 扩展 evidence basis。
   - `evidence_basis` 中增加 `url`、`summary`、`cleaned_content_excerpt`、`keywords`、`classification_rationale`。
   - 事实校验使用 title、source、summary、content、published_at、routing/classification rationale 共同组成证据语料。

3. 扩展SQLite schema与migration。
   - `linkedin_content_results` 新增：
     - `factual_validation_status`
     - `factual_validation_summary`
     - `factual_validation_details`
   - `review_queue_items` 同步新增上述字段。
   - `lineage_utils.py` 负责migration-safe补列和索引创建。

4. 升级 Stage 12 review package。
   - `review_queue.md` 增加 `Factual guard` 列。
   - candidate markdown 增加 `## Factual Validation` 区块。
   - `review_queue.csv` 与 `manifest.json` 写入完整 factual validation result。
   - manifest新增 `evidence_grounding_policy`。

5. 升级总控健康检查。
   - `0_main_workflow.py` 新增 `stage14_factual_validation_passed` 检查。
   - 只要出现 `factual_validation_failed` 或 `not_run`，健康检查会显示FAIL。

6. 更新Prompt样例。
   - `linkedin_post_generation_prompt.txt` 明确 `Do not introduce facts not present in source_records`。
   - `image_generation_prompt.txt` 明确图片prompt不得引入证据中没有的国家、公司、机构、来源名、logo或数据标签。

## 验证记录

语法检查通过：

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/homework2_pycache python3 -m py_compile \
  AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/lineage_utils.py \
  AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/5_linkedin_content_generation.py \
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

- Daily Run ID：`daily_20260502_210317_49a0162b`
- Wrapped Workflow Run ID：`run_20260502_210317_5f687756`
- `Overall success: True`
- Candidate posts：2
- Review items：2
- `stage14_factual_validation_passed: PASS`
- SQLite `linkedin_content_results.factual_validation_status`：两篇均为 `passed`
- Errors：0

no-candidate路径验证：

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/7_daily_run_review.py \
  --stage2-input-mode local_sample \
  --stage10-max-items 0 \
  --llm-mode offline \
  --image-mode offline \
  --output-root /private/tmp/homework2_stage14_no_candidate \
  --run-date 2026-05-02
```

结果摘要：

- `Overall success: True`
- Candidate posts：0
- Review items：0
- Lineage mode：`fallback`
- No-candidate reason：`no_candidate_generated_today`
- 历史内容未被复用。

## 当前人工审核入口

```text
AI_Geopolitical_Risk_Workflow_Homework_Delivery/daily_outputs/2026-05-02/review_queue.md
AI_Geopolitical_Risk_Workflow_Homework_Delivery/daily_outputs/2026-05-02/manifest.json
```

## 交接说明

阶段十四完成后，当前产品已经具备“联网抓取RSS + 可选在线LLM + 可选在线图片 + 每日人工审核包 + 数据血缘 + 事实约束”的主流程能力。阶段十五之后主要是透明度、表达质量、报告修订和结果包一致性的P1优化；如果当前目标是先测试主产品闭环，阶段十五可以后置。
