"""Shared helpers for Stage 10 LLM-enabled workflow steps."""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Literal

from llm_client import LLMClient, LLMResponse, load_llm_config


LLMMode = Literal["offline", "auto", "online"]
LLM_MODE_CHOICES = ("offline", "auto", "online")


def build_llm_client(
    llm_mode: str,
    logger: logging.Logger | None = None,
) -> tuple[LLMClient, bool]:
    """Create an LLM client for a stage without exposing local secrets.

    Modes:
    - offline: never reads the local .env file and never calls the API.
    - auto: reads configured environment normally; missing API config falls back.
    - online: requires a successful API response and disables fallback-on-error.
    """
    if llm_mode not in LLM_MODE_CHOICES:
        raise ValueError(f"Unsupported llm_mode: {llm_mode}")

    load_dotenv = llm_mode != "offline"
    config = load_llm_config(load_dotenv=load_dotenv)

    if llm_mode == "offline":
        config = replace(config, force_offline=True, fallback_on_error=True, api_key="")
    elif llm_mode == "online":
        config = replace(config, force_offline=False, fallback_on_error=False)

    return LLMClient(config=config, logger=logger), llm_mode == "online"


def require_online_success(response: LLMResponse, require_online: bool, operation_name: str) -> None:
    """Raise when a stage was explicitly asked to use the online model."""
    if require_online and not response.api_succeeded:
        reason = response.error or response.offline_reason or "LLM API did not succeed"
        raise RuntimeError(f"{operation_name} required online LLM but failed: {reason}")


def model_provider_label(response: LLMResponse) -> str:
    if response.api_succeeded:
        return f"{response.provider}:{response.model}"
    if response.used_fallback:
        return "offline_fallback"
    return response.provider or "unknown"


def prompt_version_label(base_name: str, response: LLMResponse | None) -> str:
    if response is None:
        return f"{base_name}_offline_rule_gate"
    if response.api_succeeded:
        return f"{base_name}_llm"
    if response.used_fallback:
        return f"{base_name}_offline_fallback"
    return f"{base_name}_llm_failed"

