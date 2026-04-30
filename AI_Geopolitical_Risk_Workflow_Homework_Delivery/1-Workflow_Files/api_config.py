"""Configuration placeholders for the AI geopolitical risk workflow.

Stage 2 is designed to run offline with local sample data. RSS/API and LLM
settings are intentionally kept as explicit placeholders for later stages.
"""

from pathlib import Path

WORKFLOW_DIR = Path(__file__).resolve().parent
DELIVERY_DIR = WORKFLOW_DIR.parent

DATABASE_PATH = WORKFLOW_DIR / "ai_geopolitical_risk_workflow.sqlite3"
SQLITE_SCHEMA_PATH = WORKFLOW_DIR / "database_config" / "sqlite_db_init.sql"
SAMPLE_DATA_PATH = WORKFLOW_DIR / "sample_data" / "sample_news.json"
RSS_CONFIG_PATH = WORKFLOW_DIR / "sample_data" / "rss_sources.json"
LOG_DIR = DELIVERY_DIR / "4-Progress_Report" / "workflow_running_logs"
PROMPT_DIR = DELIVERY_DIR / "2-Prompt_Design_Samples"
LINKEDIN_CONTENT_DIR = DELIVERY_DIR / "3-Final_LinkedIn_Content"
RELEVANCE_ROUTING_PROMPT_PATH = PROMPT_DIR / "relevance_routing_prompt.txt"
INFORMATION_CLASSIFICATION_PROMPT_PATH = PROMPT_DIR / "information_classification_prompt.txt"
KOL_STYLE_ANALYSIS_PROMPT_PATH = PROMPT_DIR / "kol_style_analysis_prompt.txt"
LINKEDIN_CONTENT_CONSTRAINTS_PROMPT_PATH = PROMPT_DIR / "linkedin_content_constraints_prompt.txt"
KOL_STYLE_CHECKLIST_PATH = LINKEDIN_CONTENT_DIR / "LinkedIn_Post_Style_Anatomy_Checklist.md"

MINIMAX_M27_CONFIG = {
    "provider": "Minimax M2.7",
    "enabled": False,
    "api_key_env": "MINIMAX_API_KEY",
    "endpoint_env": "MINIMAX_API_ENDPOINT",
    "model": "minimax-m2.7-placeholder",
}

DEFAULT_INGESTION_MODE = "local_sample"
