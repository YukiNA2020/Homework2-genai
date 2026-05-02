# 阶段十一记录：图片生成与内容归档

> 日期：2026-05-02  
> 阶段目标：补齐最终LinkedIn内容的图片文件与归档包，同时保留无API key、无网络环境下的离线fallback。

## 完成内容

1. 新增 `1-Workflow_Files/6_image_generation.py`。
   - 从 `linkedin_content_results` 读取两篇最终帖子和 `visual_prompt`。
   - 为每个主线分类生成一张16:9图片文件。
   - 更新原始帖子Markdown，写入图片路径、归档路径、生成时间、模型名称、状态和最终图片Prompt。
   - 生成按日期分组的归档包：`linkedin_post.md`、图片文件、`manifest.json`。

2. 新增 `--image-mode offline|auto|online`。
   - `offline`：不读取 `.env`，直接生成确定性的本地SVG fallback。
   - `auto`：如MiniMax图片API配置可用则调用真实API，否则fallback。
   - `online`：强制真实图片API成功，适合用户填写key后验收。

3. 扩展SQLite schema。
   - 新增 `image_generation_results`：保存每个分类最新图片、归档路径、模型、状态与元数据。
   - 新增 `image_generation_runs`：保存每次阶段十一运行的数量、fallback、错误与备注。

4. 升级 `0_main_workflow.py`。
   - 新增 `--include-stage11`。
   - 新增 `--image-mode offline|auto|online`。
   - 新增 `--stage11-max-items`。
   - 当包含阶段十一时，数据库健康检查会额外验证图片记录、图片文件和归档帖子是否存在。

5. 更新 `.env.example`。
   - 新增MiniMax图片生成配置：
     - `IMAGE_PROVIDER=minimax`
     - `IMAGE_MODEL=image-01`
     - `MINIMAX_IMAGE_ENDPOINT=https://api.minimaxi.com/v1/image_generation`
     - `IMAGE_ASPECT_RATIO=16:9`
     - `IMAGE_RESPONSE_FORMAT=base64`
   - 继续强调 `.env` 只能由用户本地填写，不得在对话或日志中暴露API key。

## 测试命令

语法检查：

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/homework2_pycache python3 -m py_compile \
  AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/0_main_workflow.py \
  AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/6_image_generation.py
```

阶段十一离线运行：

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/6_image_generation.py --image-mode offline
```

验证结果：

- Run ID：`run_20260502_113914_a90532c1`
- Items seen：2
- Images generated：2
- Archive bundles written：2
- Fallback used：2
- Errors：0

总控脚本阶段十一集成验证：

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/0_main_workflow.py \
  --include-stage11 \
  --image-mode offline \
  --skip-stage stage_2_news_monitoring \
  --skip-stage stage_3a_relevance_router \
  --skip-stage stage_3b_information_classification \
  --skip-stage stage_4_linkedin_analysis \
  --skip-stage stage_5_linkedin_content_generation
```

验证结果：

- Run ID：`run_20260502_113929_cab3e7e7`
- `Overall success: True`
- Stage 11：OK，0.07s
- `image_generation_results_at_least_2: PASS`
- `image_files_exist: PASS`
- `archive_posts_exist: PASS`

## 当前输出

图片目录：

```text
AI_Geopolitical_Risk_Workflow_Homework_Delivery/3-Final_LinkedIn_Content/images/
```

归档目录：

```text
AI_Geopolitical_Risk_Workflow_Homework_Delivery/3-Final_LinkedIn_Content/archive/2026-05-02/
```

每个分类归档包包含：

```text
linkedin_post.md
<generated image file>
manifest.json
```

## 用户后续真实图片API测试

用户如需测试MiniMax真实图片生成，请只在本地私密 `.env` 中填写：

```env
MINIMAX_API_KEY=
IMAGE_MODEL=image-01
MINIMAX_IMAGE_ENDPOINT=https://api.minimaxi.com/v1/image_generation
IMAGE_ASPECT_RATIO=16:9
IMAGE_RESPONSE_FORMAT=base64
```

然后运行：

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/6_image_generation.py --image-mode online
```

如希望日常测试“有key则调用、无key则fallback”，运行：

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/6_image_generation.py --image-mode auto
```

## 模型选择说明

阶段十一不使用DeepSeek V4做图片生成。DeepSeek V4继续保留在文本摘要、评分、分类和LinkedIn正文生成环节。图片生成独立使用MiniMax图片模型，默认模型为 `image-01`。

当前离线fallback生成的是专业风格SVG示意图，用于保证作业工作流在无key情况下完整可跑。用户填写MiniMax key后，`online` 模式会尝试保存真实模型返回的图片文件。

## 安全边界

- 不读取、打印、复制或总结用户私密 `.env` 内容。
- 不把真实API key写入Markdown、日志或对话。
- 离线模式不会读取 `.env`。
- 日志只记录 `api_key_configured` 等脱敏状态。
- 图片生成失败不能阻断已有文本内容和归档材料。
