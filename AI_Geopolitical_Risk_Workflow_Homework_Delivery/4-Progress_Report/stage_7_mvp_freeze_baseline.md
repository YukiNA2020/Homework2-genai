# 阶段七：稳定MVP冻结基线记录

> 使用环节：阶段七 - 稳定MVP冻结与升级保护。  
> 记录日期：2026-05-01  
> 目标：在接入真实RSS、真实LLM和图片生成之前，确认当前离线MVP可以独立、稳定、可复现地运行。

## 1. 冻结结论

当前离线MVP已通过阶段七冻结验证，可以作为后续v4.0升级路线的稳定基线。

后续任何新增联网、API、LLM或图片生成能力，都必须保留当前离线fallback能力，确保没有网络、没有API key时仍能完成课程作业所需的完整演示流程。

## 2. 本次验证命令

在项目根目录运行：

```bash
python3 AI_Geopolitical_Risk_Workflow_Homework_Delivery/1-Workflow_Files/0_main_workflow.py
```

## 3. 本次验证结果

| 项目 | 结果 |
|------|------|
| Run ID | `run_20260501_221718_d3a32586` |
| Overall success | `True` |
| Stage 2 news monitoring | `OK` |
| Stage 3A relevance routing | `OK` |
| Stage 3B information classification | `OK` |
| Stage 4 LinkedIn KOL analysis | `OK` |
| Stage 5 LinkedIn content generation | `OK` |
| Database health checks | 全部 `PASS` |

主控日志：

```text
AI_Geopolitical_Risk_Workflow_Homework_Delivery/4-Progress_Report/workflow_running_logs/run_20260501_221718_d3a32586_main_workflow.log
```

## 4. 数据库健康检查摘要

| 检查项 | 结果 |
|--------|------|
| `news_items_at_least_6` | PASS |
| `routing_results_at_least_6` | PASS |
| `kept_items_at_least_4` | PASS |
| `classification_results_at_least_4` | PASS |
| `kol_profiles_at_least_4` | PASS |
| `linkedin_posts_at_least_2` | PASS |
| `linkedin_outputs_nonempty` | PASS |

本次数据库核心计数：

| 表 | 记录数 |
|----|--------|
| `news_items` | 6 |
| `relevance_routing_results` | 6 |
| `classification_results` | 4 |
| `kol_analysis_results` | 4 |
| `linkedin_content_results` | 2 |

## 5. 升级保护规则

1. `local_sample` 输入模式必须保留，作为无网络环境下的演示入口。
2. 真实RSS接入只能作为新增输入模式，不应破坏现有样例数据入库流程。
3. LLM调用必须通过统一客户端封装，并在没有API key时自动回退到离线逻辑。
4. 图片生成失败不能阻断文本内容生成；当前配图Prompt必须继续可用。
5. 后续每完成一个升级阶段，都应重新运行总控脚本，确认离线MVP仍然可通过。

## 6. 阶段八起点

阶段七完成后，下一步进入阶段八：真实新闻/RSS接入。

阶段八优先做三件事：

1. 扩展 `sample_data/rss_sources.json`，加入3-5个真实、稳定、公开可访问的RSS源。
2. 升级 `1_news_monitoring.py`，新增 `--input-mode rss`。
3. 抓取真实RSS后写入现有 `news_items` 表，并保留 `--input-mode local_sample` 作为fallback。
