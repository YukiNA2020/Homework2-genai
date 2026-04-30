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
RELEVANCE_ROUTING_PROMPT_PATH = PROMPT_DIR / "relevance_routing_prompt.txt"
INFORMATION_CLASSIFICATION_PROMPT_PATH = PROMPT_DIR / "information_classification_prompt.txt"

MINIMAX_M27_CONFIG = {
    "provider": "Minimax M2.7",
    "enabled": False,
    "api_key_env": "MINIMAX_API_KEY",
    "endpoint_env": "MINIMAX_API_ENDPOINT",
    "model": "minimax-m2.7-placeholder",
}

DEFAULT_INGESTION_MODE = "local_sample"
