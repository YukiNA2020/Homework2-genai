"""Stage 9: unified LLM client with offline fallback.

This module is the single place where later stages should call an external
LLM. It loads local environment settings, sends a small chat-style request when
credentials are available, parses structured JSON, and returns deterministic
fallback JSON when the API is not configured.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from api_config import DEFAULT_LLM_CONFIG, LLM_ENV_PATH


DEFAULT_PROVIDER = "deepseek"
DEFAULT_MODEL = DEFAULT_LLM_CONFIG["model"]
DEFAULT_API_STYLE = "openai_compatible"
DEFAULT_ENDPOINTS = {
    "deepseek": "https://api.deepseek.com/chat/completions",
    "minimax": "https://api.minimax.io/v1/chat/completions",
}


@dataclass(frozen=True)
class LLMConfig:
    provider: str = DEFAULT_PROVIDER
    model: str = DEFAULT_MODEL
    api_style: str = DEFAULT_API_STYLE
    api_key: str = ""
    endpoint: str = ""
    timeout_seconds: int = 30
    max_retries: int = 2
    retry_backoff_seconds: float = 1.5
    temperature: float = 0.2
    max_tokens: int = 1200
    force_offline: bool = False
    fallback_on_error: bool = True
    env_path: Path = LLM_ENV_PATH


@dataclass
class LLMResponse:
    ok: bool
    api_called: bool
    api_succeeded: bool
    used_fallback: bool
    provider: str
    model: str
    json_data: dict[str, Any]
    raw_text: str = ""
    error: str = ""
    offline_reason: str = ""
    attempts: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LLMClient:
    """Small standard-library LLM client for JSON-only workflow calls."""

    def __init__(self, config: LLMConfig | None = None, logger: logging.Logger | None = None) -> None:
        self.config = config or load_llm_config()
        self.logger = logger or logging.getLogger("llm_client")

    @property
    def is_available(self) -> bool:
        return bool(
            not self.config.force_offline
            and self.config.api_key
            and self.config.endpoint
        )

    def availability_reason(self) -> str:
        if self.config.force_offline:
            return "LLM_FORCE_OFFLINE=true"
        if not self.config.api_key:
            return "API key is not configured"
        if not self.config.endpoint:
            return "API endpoint is not configured"
        return "online LLM configuration is available"

    def status(self) -> dict[str, Any]:
        return {
            "provider": self.config.provider,
            "model": self.config.model,
            "api_style": self.config.api_style,
            "available": self.is_available,
            "reason": self.availability_reason(),
            "endpoint_configured": bool(self.config.endpoint),
            "api_key_configured": bool(self.config.api_key),
            "force_offline": self.config.force_offline,
            "fallback_on_error": self.config.fallback_on_error,
        }

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        fallback_json: dict[str, Any] | Callable[[], dict[str, Any]] | None = None,
        operation_name: str = "llm_json_call",
    ) -> LLMResponse:
        """Return parsed JSON from an LLM call, or deterministic fallback JSON."""
        fallback_json = resolve_fallback(fallback_json)

        if not self.is_available:
            return self._fallback_response(
                fallback_json=fallback_json,
                operation_name=operation_name,
                offline_reason=self.availability_reason(),
            )

        last_error = ""
        raw_text = ""
        attempts = max(1, self.config.max_retries + 1)
        for attempt in range(1, attempts + 1):
            try:
                payload = self._build_payload(system_prompt, user_prompt)
                response_payload = self._post_json(payload)
                raw_text = extract_message_text(response_payload)
                parsed = parse_json_from_text(raw_text)
                return LLMResponse(
                    ok=True,
                    api_called=True,
                    api_succeeded=True,
                    used_fallback=False,
                    provider=self.config.provider,
                    model=self.config.model,
                    json_data=parsed,
                    raw_text=raw_text,
                    attempts=attempt,
                    metadata={"operation_name": operation_name},
                )
            except Exception as exc:  # noqa: BLE001 - fallback is part of the client contract.
                last_error = str(exc)
                self.logger.warning(
                    "LLM call failed: operation=%s attempt=%s/%s error=%s",
                    operation_name,
                    attempt,
                    attempts,
                    last_error,
                )
                if attempt < attempts:
                    time.sleep(self.config.retry_backoff_seconds * attempt)

        if self.config.fallback_on_error:
            return self._fallback_response(
                fallback_json=fallback_json,
                operation_name=operation_name,
                offline_reason="LLM call failed; fallback_on_error=true",
                error=last_error,
                api_called=True,
                attempts=attempts,
                raw_text=raw_text,
            )

        return LLMResponse(
            ok=False,
            api_called=True,
            api_succeeded=False,
            used_fallback=False,
            provider=self.config.provider,
            model=self.config.model,
            json_data={},
            raw_text=raw_text,
            error=last_error,
            attempts=attempts,
            metadata={"operation_name": operation_name},
        )

    def _build_payload(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        if self.config.api_style in {"openai_compatible", "deepseek", "minimax"}:
            payload["response_format"] = {"type": "json_object"}
            return payload

        if self.config.api_style == "plain_chat":
            return payload

        raise ValueError(f"Unsupported LLM_API_STYLE: {self.config.api_style}")

    def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            self.config.endpoint,
            data=encoded,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:  # noqa: S310 - endpoint is user-configured.
                charset = response.headers.get_content_charset() or "utf-8"
                body = response.read().decode(charset, errors="replace")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {body[:500]}") from exc
        except URLError as exc:
            raise RuntimeError(f"Network error: {exc}") from exc

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM API returned non-JSON response: {body[:500]}") from exc
        if not isinstance(parsed, dict):
            raise ValueError("LLM API response root must be a JSON object.")
        return parsed

    def _fallback_response(
        self,
        *,
        fallback_json: dict[str, Any],
        operation_name: str,
        offline_reason: str,
        error: str = "",
        api_called: bool = False,
        attempts: int = 0,
        raw_text: str = "",
    ) -> LLMResponse:
        return LLMResponse(
            ok=True,
            api_called=api_called,
            api_succeeded=False,
            used_fallback=True,
            provider="offline_fallback",
            model="deterministic_fallback",
            json_data=fallback_json,
            raw_text=raw_text,
            error=error,
            offline_reason=offline_reason,
            attempts=attempts,
            metadata={
                "operation_name": operation_name,
                "configured_provider": self.config.provider,
                "configured_model": self.config.model,
            },
        )


def parse_bool(raw_value: str | None, default: bool = False) -> bool:
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "y", "on"}


def parse_int(raw_value: str | None, default: int) -> int:
    if raw_value is None or not raw_value.strip():
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


def parse_float(raw_value: str | None, default: float) -> float:
    if raw_value is None or not raw_value.strip():
        return default
    try:
        return float(raw_value)
    except ValueError:
        return default


def strip_optional_quotes(raw_value: str) -> str:
    value = raw_value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def load_env_file(env_path: Path, override: bool = False) -> dict[str, str]:
    """Load a simple KEY=VALUE .env file without adding a dependency."""
    loaded: dict[str, str] = {}
    if not env_path.exists():
        return loaded

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = strip_optional_quotes(value)
        if not key:
            continue
        if override or key not in os.environ:
            os.environ[key] = value
        loaded[key] = value
    return loaded


def load_llm_config(
    env_path: Path = LLM_ENV_PATH,
    load_dotenv: bool = True,
    override_env: bool = False,
) -> LLMConfig:
    if load_dotenv:
        load_env_file(env_path, override=override_env)

    provider = os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER).strip() or DEFAULT_PROVIDER
    provider_slug = provider.lower().replace("-", "_")
    model = (
        os.getenv("LLM_MODEL")
        or os.getenv("DEEPSEEK_MODEL")
        or os.getenv("MINIMAX_MODEL")
        or DEFAULT_MODEL
    ).strip()
    api_style = os.getenv("LLM_API_STYLE", DEFAULT_API_STYLE).strip() or DEFAULT_API_STYLE

    if provider_slug.startswith("deepseek"):
        provider_key_env = "DEEPSEEK_API_KEY"
        provider_endpoint_env = "DEEPSEEK_API_ENDPOINT"
        default_endpoint = DEFAULT_ENDPOINTS["deepseek"]
    elif provider_slug.startswith("minimax"):
        provider_key_env = "MINIMAX_API_KEY"
        provider_endpoint_env = "MINIMAX_API_ENDPOINT"
        default_endpoint = DEFAULT_ENDPOINTS["minimax"]
    else:
        provider_key_env = "LLM_API_KEY"
        provider_endpoint_env = "LLM_API_ENDPOINT"
        default_endpoint = ""

    api_key = os.getenv(provider_key_env) or os.getenv("LLM_API_KEY", "")
    endpoint = os.getenv(provider_endpoint_env) or os.getenv("LLM_API_ENDPOINT", "") or default_endpoint

    return LLMConfig(
        provider=provider,
        model=model,
        api_style=api_style,
        api_key=api_key.strip(),
        endpoint=endpoint.strip(),
        timeout_seconds=parse_int(os.getenv("LLM_TIMEOUT_SECONDS"), 30),
        max_retries=parse_int(os.getenv("LLM_MAX_RETRIES"), 2),
        retry_backoff_seconds=parse_float(os.getenv("LLM_RETRY_BACKOFF_SECONDS"), 1.5),
        temperature=parse_float(os.getenv("LLM_TEMPERATURE"), 0.2),
        max_tokens=parse_int(os.getenv("LLM_MAX_TOKENS"), 1200),
        force_offline=parse_bool(os.getenv("LLM_FORCE_OFFLINE"), False),
        fallback_on_error=parse_bool(os.getenv("LLM_FALLBACK_ON_ERROR"), True),
        env_path=env_path,
    )


def resolve_fallback(
    fallback_json: dict[str, Any] | Callable[[], dict[str, Any]] | None,
) -> dict[str, Any]:
    if callable(fallback_json):
        fallback_json = fallback_json()
    if fallback_json is None:
        return {}
    return dict(fallback_json)


def extract_message_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first_choice = choices[0]
        if isinstance(first_choice, dict):
            message = first_choice.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    text_parts = [
                        str(part.get("text", ""))
                        for part in content
                        if isinstance(part, dict)
                    ]
                    if any(text_parts):
                        return "\n".join(text_parts)
            text = first_choice.get("text")
            if isinstance(text, str):
                return text

    data = payload.get("data")
    if isinstance(data, dict):
        nested = extract_message_text(data)
        if nested:
            return nested

    for key in ("output_text", "reply", "text", "content", "message"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            nested_content = value.get("content") or value.get("text")
            if isinstance(nested_content, str):
                return nested_content

    return json.dumps(payload, ensure_ascii=False)


def parse_json_from_text(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        cleaned = fenced.group(1).strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
        raise ValueError("Parsed JSON is not an object.")
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char not in "{[":
            continue
        try:
            parsed, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            return {"items": parsed}

    raise ValueError(f"No JSON object found in LLM response: {text[:500]}")


def self_test_fallback() -> dict[str, Any]:
    return {
        "ok": True,
        "stage": "stage_9_llm_client",
        "mode": "offline_fallback",
        "message": "No API call was made because online LLM configuration is not complete.",
        "expected_next_step": "Fill 1-Workflow_Files/.env, then rerun llm_client.py.",
    }


def run_self_test(client: LLMClient) -> LLMResponse:
    system_prompt = (
        "You are a strict JSON API. Return only one valid JSON object. "
        "Do not include markdown fences or explanatory prose."
    )
    user_prompt = (
        "Return a JSON object with keys ok, stage, provider, model, and "
        "risk_focus. risk_focus must be 'AI infrastructure geopolitical risk'."
    )
    return client.complete_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        fallback_json=self_test_fallback,
        operation_name="stage_9_connectivity_self_test",
    )


def setup_cli_logger(verbose: bool) -> logging.Logger:
    logger = logging.getLogger("llm_client")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
    return logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Stage 9 LLM client self-test.")
    parser.add_argument(
        "--env-path",
        type=Path,
        default=LLM_ENV_PATH,
        help="Path to the local .env file. Default: 1-Workflow_Files/.env",
    )
    parser.add_argument(
        "--no-env-file",
        action="store_true",
        help="Do not load a .env file; read only the current process environment.",
    )
    parser.add_argument(
        "--require-online",
        action="store_true",
        help="Fail if the API is unavailable and fallback is used.",
    )
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Print sanitized LLM configuration before running the self-test.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable warning/debug logs for API retries.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logger = setup_cli_logger(args.verbose)
    config = load_llm_config(env_path=args.env_path, load_dotenv=not args.no_env_file)
    client = LLMClient(config=config, logger=logger)

    if args.print_config:
        print("Sanitized LLM config:")
        print(json.dumps(client.status(), ensure_ascii=False, indent=2))

    response = run_self_test(client)

    print("\nStage 9 LLM client self-test completed")
    print(f"Provider: {response.provider}")
    print(f"Model: {response.model}")
    print(f"API called: {response.api_called}")
    print(f"API succeeded: {response.api_succeeded}")
    print(f"Used fallback: {response.used_fallback}")
    if response.offline_reason:
        print(f"Offline reason: {response.offline_reason}")
    if response.error:
        print(f"Error: {response.error}")
    print("Parsed JSON:")
    print(json.dumps(response.json_data, ensure_ascii=False, indent=2))

    if args.require_online and not response.api_succeeded:
        return 2
    return 0 if response.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
