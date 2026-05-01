# Stage 8 RSS Ingestion Notes

## Scope

Stage 8 upgrades the news monitoring layer from local sample-only ingestion to a dual-mode input design:

- `local_sample`: offline fallback for classroom demo and no-network testing.
- `rss`: real public RSS/Atom ingestion from configured sources.
- `all`: local sample plus RSS ingestion.

No LLM, image generation, paid API, or user API key is required in this stage.

## Updated Files

- `1-Workflow_Files/1_news_monitoring.py`
- `1-Workflow_Files/0_main_workflow.py`
- `1-Workflow_Files/sample_data/rss_sources.json`
- `STATUS.md`
- `Implementation_Roadmap.md`
- `Progress_Report.md`

## Configured RSS Sources

| Source | URL |
|---|---|
| MIT Technology Review - Artificial Intelligence | `https://www.technologyreview.com/topic/artificial-intelligence/feed/` |
| OpenAI News | `https://openai.com/news/rss.xml` |
| Microsoft Official Blog | `https://blogs.microsoft.com/feed/` |
| NVIDIA Blog | `https://blogs.nvidia.com/feed/` |
| USGS News | `https://www.usgs.gov/news/national-news-release/feed` |

## Test Commands

Offline fallback:

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/1_news_monitoring.py --input-mode local_sample
```

RSS smoke test:

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/1_news_monitoring.py --input-mode rss --rss-limit 2
```

Full workflow using RSS as the Stage 2 input:

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/0_main_workflow.py --stage2-input-mode rss --rss-limit 2
```

Full workflow using the frozen offline baseline:

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/0_main_workflow.py
```

## Validation Summary

- Offline fallback still runs with `Errors: 0`.
- RSS mode parsed all 5 configured sources during the final smoke test.
- Duplicate handling is active through the existing `content_hash` constraint; final duplicate run result was `seen=10 inserted=0 duplicates=10 errors=0`.
- Current database count after verification: `local_sample=6`, `rss=10`.

## Notes For Later Stages

- Stage 9 should add a unified `llm_client.py` instead of placing API calls inside stage scripts.
- Stage 10 can reuse RSS-ingested records from `news_items` without schema changes.
- Keep `local_sample` as the default path for reproducible grading and no-network demos.
