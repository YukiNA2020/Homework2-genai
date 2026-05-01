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
LLM_ENV_PATH = WORKFLOW_DIR / ".env"
LLM_ENV_EXAMPLE_PATH = WORKFLOW_DIR / ".env.example"
RELEVANCE_ROUTING_PROMPT_PATH = PROMPT_DIR / "relevance_routing_prompt.txt"
INFORMATION_CLASSIFICATION_PROMPT_PATH = PROMPT_DIR / "information_classification_prompt.txt"
KOL_STYLE_ANALYSIS_PROMPT_PATH = PROMPT_DIR / "kol_style_analysis_prompt.txt"
LINKEDIN_CONTENT_CONSTRAINTS_PROMPT_PATH = PROMPT_DIR / "linkedin_content_constraints_prompt.txt"
LINKEDIN_POST_GENERATION_PROMPT_PATH = PROMPT_DIR / "linkedin_post_generation_prompt.txt"
IMAGE_GENERATION_PROMPT_PATH = PROMPT_DIR / "image_generation_prompt.txt"
KOL_STYLE_CHECKLIST_PATH = LINKEDIN_CONTENT_DIR / "LinkedIn_Post_Style_Anatomy_Checklist.md"
CATEGORY_1_POST_PATH = LINKEDIN_CONTENT_DIR / "Category_1_AI_Infrastructure_Risk_Post.md"
CATEGORY_2_POST_PATH = LINKEDIN_CONTENT_DIR / "Category_2_AI_Mineral_SupplyChain_Post.md"

DEFAULT_LLM_CONFIG = {
    "provider": "DeepSeek V4",
    "enabled": False,
    "api_key_env": "DEEPSEEK_API_KEY",
    "endpoint_env": "DEEPSEEK_API_ENDPOINT",
    "provider_env": "LLM_PROVIDER",
    "model_env": "LLM_MODEL",
    "api_style_env": "LLM_API_STYLE",
    "model": "deepseek-v4-pro",
    "endpoint": "https://api.deepseek.com/chat/completions",
}

# Backward-compatible name used by existing stage scripts.
MINIMAX_M27_CONFIG = DEFAULT_LLM_CONFIG

DEFAULT_INGESTION_MODE = "local_sample"
