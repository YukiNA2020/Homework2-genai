"""Stage 11: image generation and content archiving.

This stage reads the final LinkedIn briefs produced by Stage 5/10, generates
one 16:9 visual per post, updates the post Markdown with image metadata, and
archives the post/image/manifest bundle for handoff review.

The default mode is fully offline and deterministic: it creates a local SVG
placeholder that preserves the workflow shape without reading API credentials.
When MiniMax image credentials are configured, auto/online mode can call the
image generation endpoint and save the returned image bytes.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import logging
import os
import re
import shutil
import sqlite3
import textwrap
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from api_config import (
    CONTENT_ARCHIVE_DIR,
    DATABASE_PATH,
    DEFAULT_IMAGE_CONFIG,
    IMAGE_OUTPUT_DIR,
    LLM_ENV_PATH,
    LOG_DIR,
    SQLITE_SCHEMA_PATH,
)
from llm_client import load_env_file, parse_bool, parse_float, parse_int


PROMPT_VERSION = "image_generation_archive_v1_stage11"
IMAGE_MODE_CHOICES = ("offline", "auto", "online")
MARKER_START = "<!-- STAGE11_IMAGE_ARCHIVE_START -->"
MARKER_END = "<!-- STAGE11_IMAGE_ARCHIVE_END -->"

CATEGORY_SLUGS = {
    "AI算力基础设施地缘风险": "category_1_ai_infrastructure_risk",
    "AI关键矿产供应链与地缘政治": "category_2_ai_critical_minerals_supply_chain",
}


@dataclass(frozen=True)
class ImageConfig:
    provider: str = DEFAULT_IMAGE_CONFIG["provider"]
    model: str = DEFAULT_IMAGE_CONFIG["model"]
    endpoint: str = DEFAULT_IMAGE_CONFIG["endpoint"]
    api_key: str = ""
    aspect_ratio: str = DEFAULT_IMAGE_CONFIG["aspect_ratio"]
    response_format: str = DEFAULT_IMAGE_CONFIG["response_format"]
    timeout_seconds: int = 90
    max_retries: int = 1
    retry_backoff_seconds: float = 2.0
    prompt_optimizer: bool = True
    force_offline: bool = False
    fallback_on_error: bool = True
    env_path: Path = LLM_ENV_PATH


@dataclass
class ImageGenerationStats:
    run_id: str
    started_at: str
    finished_at: str = ""
    image_mode: str = "offline"
    items_seen: int = 0
    images_generated: int = 0
    archives_written: int = 0
    fallback_used: int = 0
    errors: int = 0
    notes: str = ""


@dataclass
class ImageArtifact:
    primary_category: str
    source_content_id: int
    source_post_path: Path
    visual_prompt: str
    image_mode: str
    image_provider: str
    image_model: str
    image_path: Path
    image_mime_type: str
    archive_dir: Path
    archive_post_path: Path
    status: str
    prompt_version: str
    image_metadata: dict[str, Any] = field(default_factory=dict)
    error: str = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def local_date_slug() -> str:
    return datetime.now().date().isoformat()


def apply_schema(db_path: Path, schema_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.executescript(schema_path.read_text(encoding="utf-8"))


def setup_logger(run_id: str) -> tuple[logging.Logger, Path]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{run_id}_image_generation.log"
    logger = logging.getLogger(f"image_generation.{run_id}")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger, log_path


def load_image_config(env_path: Path = LLM_ENV_PATH, load_dotenv: bool = True) -> ImageConfig:
    if load_dotenv:
        load_env_file(env_path, override=False)

    provider = os.getenv("IMAGE_PROVIDER", DEFAULT_IMAGE_CONFIG["provider"]).strip()
    model = (
        os.getenv("IMAGE_MODEL")
        or os.getenv("MINIMAX_IMAGE_MODEL")
        or DEFAULT_IMAGE_CONFIG["model"]
    ).strip()
    endpoint = (
        os.getenv("MINIMAX_IMAGE_ENDPOINT")
        or os.getenv("IMAGE_API_ENDPOINT")
        or DEFAULT_IMAGE_CONFIG["endpoint"]
    ).strip()
    api_key = (os.getenv("MINIMAX_API_KEY") or os.getenv("IMAGE_API_KEY") or "").strip()

    return ImageConfig(
        provider=provider or DEFAULT_IMAGE_CONFIG["provider"],
        model=model or DEFAULT_IMAGE_CONFIG["model"],
        endpoint=endpoint or DEFAULT_IMAGE_CONFIG["endpoint"],
        api_key=api_key,
        aspect_ratio=os.getenv("IMAGE_ASPECT_RATIO", DEFAULT_IMAGE_CONFIG["aspect_ratio"]).strip()
        or DEFAULT_IMAGE_CONFIG["aspect_ratio"],
        response_format=os.getenv("IMAGE_RESPONSE_FORMAT", DEFAULT_IMAGE_CONFIG["response_format"]).strip()
        or DEFAULT_IMAGE_CONFIG["response_format"],
        timeout_seconds=parse_int(os.getenv("IMAGE_TIMEOUT_SECONDS"), 90),
        max_retries=parse_int(os.getenv("IMAGE_MAX_RETRIES"), 1),
        retry_backoff_seconds=parse_float(os.getenv("IMAGE_RETRY_BACKOFF_SECONDS"), 2.0),
        prompt_optimizer=parse_bool(os.getenv("IMAGE_PROMPT_OPTIMIZER"), True),
        force_offline=parse_bool(os.getenv("IMAGE_FORCE_OFFLINE"), False),
        fallback_on_error=parse_bool(os.getenv("IMAGE_FALLBACK_ON_ERROR"), True),
        env_path=env_path,
    )


def image_config_available(config: ImageConfig) -> bool:
    return bool(not config.force_offline and config.api_key and config.endpoint)


def image_config_status(config: ImageConfig) -> dict[str, Any]:
    if config.force_offline:
        reason = "IMAGE_FORCE_OFFLINE=true"
    elif not config.api_key:
        reason = "MiniMax image API key is not configured"
    elif not config.endpoint:
        reason = "MiniMax image endpoint is not configured"
    else:
        reason = "online image generation configuration is available"

    return {
        "provider": config.provider,
        "model": config.model,
        "available": image_config_available(config),
        "reason": reason,
        "endpoint_configured": bool(config.endpoint),
        "api_key_configured": bool(config.api_key),
        "aspect_ratio": config.aspect_ratio,
        "response_format": config.response_format,
        "force_offline": config.force_offline,
        "fallback_on_error": config.fallback_on_error,
    }


def select_content_items(
    connection: sqlite3.Connection,
    max_items: int | None = None,
) -> list[sqlite3.Row]:
    connection.row_factory = sqlite3.Row
    sql = """
        SELECT
            id AS source_content_id,
            primary_category,
            target_audience,
            tone_positioning,
            source_news_ids,
            source_titles,
            evidence_basis,
            linkedin_post,
            visual_prompt,
            output_path,
            prompt_version,
            model_provider,
            updated_at
        FROM linkedin_content_results
        ORDER BY primary_category ASC
    """
    params: tuple[Any, ...] = ()
    if max_items is not None:
        sql += " LIMIT ?"
        params = (max_items,)
    cursor = connection.execute(sql, params)
    return list(cursor.fetchall())


def safe_slug(value: str) -> str:
    if value in CATEGORY_SLUGS:
        return CATEGORY_SLUGS[value]
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.lower()).strip("_")
    return cleaned or "linkedin_visual"


def remove_stage11_section(markdown: str) -> str:
    pattern = re.compile(
        rf"\n?{re.escape(MARKER_START)}.*?{re.escape(MARKER_END)}\n?",
        flags=re.DOTALL,
    )
    return pattern.sub("\n", markdown).rstrip() + "\n"


def relative_markdown_path(target: Path, base_file: Path) -> str:
    try:
        return target.resolve().relative_to(base_file.parent.resolve()).as_posix()
    except ValueError:
        return os.path.relpath(target, start=base_file.parent).replace(os.sep, "/")


def render_stage11_section(artifact: ImageArtifact, generated_at: str) -> str:
    relative_image_path = relative_markdown_path(artifact.image_path, artifact.source_post_path)
    return "\n".join(
        [
            MARKER_START,
            "",
            "## Stage 11 Generated Image",
            "",
            f"![Stage 11 LinkedIn visual]({relative_image_path})",
            "",
            f"- Image file: `{artifact.image_path}`",
            f"- Archive directory: `{artifact.archive_dir}`",
            f"- Archive post: `{artifact.archive_post_path}`",
            f"- Generated at: `{generated_at}`",
            f"- Image mode: `{artifact.image_mode}`",
            f"- Image provider: `{artifact.image_provider}`",
            f"- Image model: `{artifact.image_model}`",
            f"- Status: `{artifact.status}`",
            f"- Prompt version: `{artifact.prompt_version}`",
            "",
            "### Final Image Prompt",
            "",
            artifact.visual_prompt,
            "",
            MARKER_END,
            "",
        ]
    )


def update_post_markdown(artifact: ImageArtifact, generated_at: str) -> None:
    post_path = artifact.source_post_path
    original = post_path.read_text(encoding="utf-8")
    updated = remove_stage11_section(original)
    updated = updated.rstrip() + "\n\n" + render_stage11_section(artifact, generated_at)
    post_path.write_text(updated, encoding="utf-8")


def render_archive_post(source_markdown: str, artifact: ImageArtifact, generated_at: str) -> str:
    archive_image_name = artifact.image_path.name
    header = "\n".join(
        [
            "# Archived LinkedIn Content Bundle",
            "",
            f"- Primary category: {artifact.primary_category}",
            f"- Generated at: `{generated_at}`",
            f"- Image status: `{artifact.status}`",
            f"- Image provider: `{artifact.image_provider}`",
            f"- Image model: `{artifact.image_model}`",
            f"- Image file: `{archive_image_name}`",
            "",
            f"![Archived LinkedIn visual]({archive_image_name})",
            "",
            "---",
            "",
        ]
    )
    return header + remove_stage11_section(source_markdown)


def make_archive_bundle(
    artifact: ImageArtifact,
    item: sqlite3.Row,
    archive_root: Path,
    archive_date: str,
    generated_at: str,
) -> ImageArtifact:
    slug = safe_slug(artifact.primary_category)
    archive_dir = archive_root / archive_date / slug
    archive_dir.mkdir(parents=True, exist_ok=True)

    archived_image_path = archive_dir / artifact.image_path.name
    shutil.copy2(artifact.image_path, archived_image_path)

    source_markdown = artifact.source_post_path.read_text(encoding="utf-8")
    archive_post_path = archive_dir / "linkedin_post.md"
    archive_post_path.write_text(
        render_archive_post(source_markdown, artifact, generated_at),
        encoding="utf-8",
    )

    manifest = {
        "run_generated_at": generated_at,
        "primary_category": artifact.primary_category,
        "source_content_id": artifact.source_content_id,
        "source_post_path": str(artifact.source_post_path),
        "archive_post_path": str(archive_post_path),
        "image_path": str(archived_image_path),
        "image_mime_type": artifact.image_mime_type,
        "status": artifact.status,
        "image_mode": artifact.image_mode,
        "image_provider": artifact.image_provider,
        "image_model": artifact.image_model,
        "prompt_version": artifact.prompt_version,
        "visual_prompt": artifact.visual_prompt,
        "source_news_ids": json.loads(item["source_news_ids"] or "[]"),
        "source_titles": json.loads(item["source_titles"] or "[]"),
        "stage5_prompt_version": item["prompt_version"],
        "stage5_model_provider": item["model_provider"],
        "image_metadata": artifact.image_metadata,
        "error": artifact.error,
    }
    (archive_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return ImageArtifact(
        **{
            **asdict(artifact),
            "archive_dir": archive_dir,
            "archive_post_path": archive_post_path,
            "image_path": artifact.image_path,
        }
    )


def svg_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def offline_svg_for_category(primary_category: str, visual_prompt: str) -> str:
    if primary_category == "AI关键矿产供应链与地缘政治":
        accent = "#C47A30"
        secondary = "#2D7A78"
        tertiary = "#597A3A"
        lower_band = "#E8D4BB"
        node_label = "mineral"
    else:
        accent = "#2B6CB0"
        secondary = "#4D7C3F"
        tertiary = "#7A5AA6"
        lower_band = "#C9DDF0"
        node_label = "compute"

    prompt_hash = base64.urlsafe_b64encode(visual_prompt.encode("utf-8"))[:10].decode("ascii")
    return textwrap.dedent(
        f"""\
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" role="img" aria-label="Professional LinkedIn visual for AI infrastructure risk">
          <defs>
            <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stop-color="#F6F7F9"/>
              <stop offset="0.55" stop-color="#E9EEF3"/>
              <stop offset="1" stop-color="#F2EFE9"/>
            </linearGradient>
            <linearGradient id="glass" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stop-color="#FFFFFF" stop-opacity="0.82"/>
              <stop offset="1" stop-color="#DDE7EF" stop-opacity="0.72"/>
            </linearGradient>
            <filter id="shadow" x="-10%" y="-10%" width="120%" height="130%">
              <feDropShadow dx="0" dy="18" stdDeviation="22" flood-color="#1F2933" flood-opacity="0.16"/>
            </filter>
          </defs>
          <rect width="1600" height="900" fill="url(#bg)"/>
          <path d="M0 610 C210 550 310 640 515 590 C710 545 815 455 1015 505 C1190 548 1320 625 1600 560 L1600 900 L0 900 Z" fill="{lower_band}" opacity="0.72"/>
          <path d="M80 210 C290 120 430 190 600 155 C840 105 1000 145 1200 115 C1345 94 1450 110 1535 160" fill="none" stroke="#9AA8B5" stroke-width="3" opacity="0.38"/>
          <path d="M120 705 L1480 270" fill="none" stroke="{accent}" stroke-width="5" opacity="0.32"/>
          <path d="M185 615 L1360 430" fill="none" stroke="{secondary}" stroke-width="4" opacity="0.34"/>
          <g filter="url(#shadow)">
            <rect x="205" y="315" width="410" height="270" rx="8" fill="url(#glass)" stroke="#B6C3D1" stroke-width="2"/>
            <rect x="250" y="360" width="315" height="34" rx="4" fill="{accent}" opacity="0.82"/>
            <rect x="250" y="418" width="315" height="34" rx="4" fill="{accent}" opacity="0.58"/>
            <rect x="250" y="476" width="315" height="34" rx="4" fill="{accent}" opacity="0.36"/>
            <rect x="630" y="245" width="325" height="455" rx="8" fill="#EFF4F7" stroke="#B6C3D1" stroke-width="2"/>
            <g opacity="0.85">
              <rect x="672" y="298" width="64" height="310" rx="5" fill="#BFCAD6"/>
              <rect x="758" y="298" width="64" height="310" rx="5" fill="#CBD5DF"/>
              <rect x="844" y="298" width="64" height="310" rx="5" fill="#BFCAD6"/>
            </g>
            <rect x="987" y="370" width="380" height="210" rx="8" fill="url(#glass)" stroke="#B6C3D1" stroke-width="2"/>
            <path d="M1058 527 C1110 450 1190 455 1244 500 C1290 540 1320 516 1350 472" fill="none" stroke="{tertiary}" stroke-width="12" stroke-linecap="round" opacity="0.75"/>
          </g>
          <g fill="#FFFFFF" stroke="#738496" stroke-width="3">
            <circle cx="205" cy="615" r="22"/>
            <circle cx="615" cy="470" r="20"/>
            <circle cx="955" cy="330" r="24"/>
            <circle cx="1360" cy="430" r="22"/>
          </g>
          <g fill="{accent}" opacity="0.9">
            <circle cx="205" cy="615" r="9"/>
            <circle cx="615" cy="470" r="8"/>
            <circle cx="955" cy="330" r="10"/>
            <circle cx="1360" cy="430" r="9"/>
          </g>
          <g opacity="0.22" fill="none" stroke="#64748B" stroke-width="2">
            <path d="M1140 174 a170 74 0 1 0 1 0"/>
            <path d="M1140 174 a118 170 0 1 0 1 0"/>
            <path d="M978 174 h326"/>
            <path d="M1008 115 h266"/>
            <path d="M1008 233 h266"/>
          </g>
          <metadata>{svg_escape(node_label)}:{svg_escape(prompt_hash)}</metadata>
        </svg>
        """
    )


def save_offline_svg(
    primary_category: str,
    visual_prompt: str,
    image_output_dir: Path,
    run_id: str,
) -> tuple[Path, str, dict[str, Any]]:
    image_output_dir.mkdir(parents=True, exist_ok=True)
    slug = safe_slug(primary_category)
    image_path = image_output_dir / f"{slug}_{run_id}.svg"
    svg = offline_svg_for_category(primary_category, visual_prompt)
    image_path.write_text(svg, encoding="utf-8")
    return image_path, "image/svg+xml", {
        "fallback_type": "deterministic_svg",
        "aspect_ratio": "16:9",
        "style_constraints": [
            "professional editorial business style",
            "no logos",
            "no text overlays",
            "no sensational crisis imagery",
        ],
    }


def build_minimax_payload(config: ImageConfig, prompt: str) -> dict[str, Any]:
    return {
        "model": config.model,
        "prompt": prompt,
        "aspect_ratio": config.aspect_ratio,
        "response_format": config.response_format,
        "n": 1,
        "prompt_optimizer": config.prompt_optimizer,
        "aigc_watermark": False,
    }


def post_json(config: ImageConfig, payload: dict[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        config.endpoint,
        data=encoded,
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=config.timeout_seconds) as response:  # noqa: S310 - endpoint is user-configured.
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
        raise ValueError(f"Image API returned non-JSON response: {body[:500]}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Image API response root must be a JSON object.")
    return parsed


def decode_data_url(value: str) -> tuple[bytes, str] | None:
    match = re.match(r"^data:(image/[a-zA-Z0-9.+-]+);base64,(.+)$", value.strip(), re.DOTALL)
    if not match:
        return None
    return base64.b64decode(match.group(2), validate=False), match.group(1)


def maybe_decode_base64(value: str) -> bytes | None:
    candidate = value.strip().replace("\n", "")
    if len(candidate) < 500:
        return None
    if not re.fullmatch(r"[A-Za-z0-9+/=_-]+", candidate):
        return None
    try:
        if "-" in candidate or "_" in candidate:
            return base64.urlsafe_b64decode(candidate + "=" * (-len(candidate) % 4))
        return base64.b64decode(candidate, validate=False)
    except (ValueError, binascii.Error):
        return None


def detect_image_mime(data: bytes) -> tuple[str, str]:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return "application/octet-stream", ".bin"


def collect_image_candidates(value: Any) -> list[tuple[bytes, str]]:
    candidates: list[tuple[bytes, str]] = []
    if isinstance(value, str):
        data_url = decode_data_url(value)
        if data_url:
            candidates.append(data_url)
            return candidates
        decoded = maybe_decode_base64(value)
        if decoded:
            mime, _ = detect_image_mime(decoded)
            if mime.startswith("image/"):
                candidates.append((decoded, mime))
        return candidates

    if isinstance(value, list):
        for item in value:
            candidates.extend(collect_image_candidates(item))
        return candidates

    if isinstance(value, dict):
        preferred_keys = [
            "b64_json",
            "image_base64",
            "base64",
            "image",
            "images",
            "image_url",
            "image_urls",
            "url",
            "urls",
            "data",
            "output",
        ]
        for key in preferred_keys:
            if key in value:
                candidates.extend(collect_image_candidates(value[key]))
        for key, nested_value in value.items():
            if key in preferred_keys:
                continue
            candidates.extend(collect_image_candidates(nested_value))
    return candidates


def summarize_image_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Return non-secret API response metadata without image bytes or URLs."""
    data = payload.get("data")
    base_resp = payload.get("base_resp")
    metadata = payload.get("metadata")
    summary: dict[str, Any] = {
        "root_keys": sorted(payload.keys()),
        "data_keys": sorted(data.keys()) if isinstance(data, dict) else [],
        "base_resp": base_resp if isinstance(base_resp, dict) else {},
        "metadata": metadata if isinstance(metadata, dict) else {},
    }
    if isinstance(data, dict):
        for key in ("image_base64", "image_urls", "images", "urls"):
            value = data.get(key)
            if isinstance(value, list):
                summary[f"{key}_count"] = len(value)
                summary[f"{key}_item_types"] = sorted({type(item).__name__ for item in value})
            elif value is not None:
                summary[f"{key}_type"] = type(value).__name__
    return summary


def download_url_image(value: Any, timeout_seconds: int) -> tuple[bytes, str] | None:
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        request = Request(value, headers={"Accept": "image/*"}, method="GET")
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - model-returned URL.
            content_type = response.headers.get_content_type()
            data = response.read()
        if content_type.startswith("image/"):
            return data, content_type
        mime, _ = detect_image_mime(data)
        if mime.startswith("image/"):
            return data, mime
    if isinstance(value, dict):
        for nested_value in value.values():
            image = download_url_image(nested_value, timeout_seconds)
            if image:
                return image
    if isinstance(value, list):
        for item in value:
            image = download_url_image(item, timeout_seconds)
            if image:
                return image
    return None


def save_online_image(
    config: ImageConfig,
    primary_category: str,
    visual_prompt: str,
    image_output_dir: Path,
    run_id: str,
    logger: logging.Logger,
) -> tuple[Path, str, dict[str, Any]]:
    if not image_config_available(config):
        raise RuntimeError(image_config_status(config)["reason"])

    attempts = max(1, config.max_retries + 1)
    last_error = ""
    response_payload: dict[str, Any] = {}
    for attempt in range(1, attempts + 1):
        try:
            payload = build_minimax_payload(config, visual_prompt)
            response_payload = post_json(config, payload)
            candidates = collect_image_candidates(response_payload)
            if candidates:
                image_bytes, mime_type = candidates[0]
            else:
                downloaded = download_url_image(response_payload, config.timeout_seconds)
                if not downloaded:
                    raise ValueError(
                        "Image API response did not contain base64 image bytes or a downloadable image URL. "
                        f"response_summary={json.dumps(summarize_image_response(response_payload), ensure_ascii=False)}"
                    )
                image_bytes, mime_type = downloaded

            _, extension = detect_image_mime(image_bytes)
            if mime_type == "image/svg+xml":
                extension = ".svg"
            image_output_dir.mkdir(parents=True, exist_ok=True)
            image_path = image_output_dir / f"{safe_slug(primary_category)}_{run_id}{extension}"
            image_path.write_bytes(image_bytes)
            return image_path, mime_type, {
                "api_payload": {
                    "model": config.model,
                    "aspect_ratio": config.aspect_ratio,
                    "response_format": config.response_format,
                    "prompt_optimizer": config.prompt_optimizer,
                    "aigc_watermark": False,
                },
                "api_response_keys": sorted(response_payload.keys()),
                "attempts": attempt,
            }
        except Exception as exc:  # noqa: BLE001 - retry then let caller choose fallback.
            last_error = str(exc)
            logger.warning(
                "Image API call failed: category=%s attempt=%s/%s error=%s",
                primary_category,
                attempt,
                attempts,
                last_error,
            )
            if attempt < attempts:
                time.sleep(config.retry_backoff_seconds * attempt)

    raise RuntimeError(last_error or "Image API call failed")


def build_artifact(
    item: sqlite3.Row,
    *,
    image_mode: str,
    config: ImageConfig,
    image_output_dir: Path,
    archive_root: Path,
    archive_date: str,
    run_id: str,
    generated_at: str,
    logger: logging.Logger,
) -> tuple[ImageArtifact, bool]:
    primary_category = item["primary_category"]
    visual_prompt = item["visual_prompt"]
    source_post_path = Path(item["output_path"])
    fallback_used = False
    error = ""

    should_call_api = image_mode in {"auto", "online"} and image_config_available(config)
    if image_mode == "online" and not image_config_available(config):
        raise RuntimeError(image_config_status(config)["reason"])

    if should_call_api:
        try:
            image_path, mime_type, metadata = save_online_image(
                config,
                primary_category,
                visual_prompt,
                image_output_dir,
                run_id,
                logger,
            )
            status = "generated"
            provider = config.provider
            model = config.model
        except Exception as exc:  # noqa: BLE001 - auto mode intentionally falls back.
            if image_mode == "online" or not config.fallback_on_error:
                raise
            error = str(exc)
            image_path, mime_type, metadata = save_offline_svg(
                primary_category,
                visual_prompt,
                image_output_dir,
                run_id,
            )
            status = "api_error_fallback"
            provider = "offline_fallback"
            model = "deterministic_svg"
            fallback_used = True
            metadata["api_error"] = error
    else:
        image_path, mime_type, metadata = save_offline_svg(
            primary_category,
            visual_prompt,
            image_output_dir,
            run_id,
        )
        status = "offline_fallback"
        provider = "offline_fallback"
        model = "deterministic_svg"
        fallback_used = True
        if image_mode == "auto":
            metadata["offline_reason"] = image_config_status(config)["reason"]

    artifact = ImageArtifact(
        primary_category=primary_category,
        source_content_id=int(item["source_content_id"]),
        source_post_path=source_post_path,
        visual_prompt=visual_prompt,
        image_mode=image_mode,
        image_provider=provider,
        image_model=model,
        image_path=image_path,
        image_mime_type=mime_type,
        archive_dir=archive_root / archive_date / safe_slug(primary_category),
        archive_post_path=archive_root / archive_date / safe_slug(primary_category) / "linkedin_post.md",
        status=status,
        error=error,
        prompt_version=PROMPT_VERSION,
        image_metadata=metadata,
    )
    archived = make_archive_bundle(artifact, item, archive_root, archive_date, generated_at)
    update_post_markdown(archived, generated_at)
    return archived, fallback_used


def upsert_image_result(connection: sqlite3.Connection, artifact: ImageArtifact) -> None:
    now = utc_now()
    connection.execute(
        """
        INSERT INTO image_generation_results (
            primary_category, source_content_id, source_post_path, visual_prompt,
            image_mode, image_provider, image_model, image_path, image_mime_type,
            archive_dir, archive_post_path, status, error, prompt_version,
            image_metadata, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(primary_category) DO UPDATE SET
            source_content_id = excluded.source_content_id,
            source_post_path = excluded.source_post_path,
            visual_prompt = excluded.visual_prompt,
            image_mode = excluded.image_mode,
            image_provider = excluded.image_provider,
            image_model = excluded.image_model,
            image_path = excluded.image_path,
            image_mime_type = excluded.image_mime_type,
            archive_dir = excluded.archive_dir,
            archive_post_path = excluded.archive_post_path,
            status = excluded.status,
            error = excluded.error,
            prompt_version = excluded.prompt_version,
            image_metadata = excluded.image_metadata,
            updated_at = excluded.updated_at
        """,
        (
            artifact.primary_category,
            artifact.source_content_id,
            str(artifact.source_post_path),
            artifact.visual_prompt,
            artifact.image_mode,
            artifact.image_provider,
            artifact.image_model,
            str(artifact.image_path),
            artifact.image_mime_type,
            str(artifact.archive_dir),
            str(artifact.archive_post_path),
            artifact.status,
            artifact.error,
            artifact.prompt_version,
            json.dumps(artifact.image_metadata, ensure_ascii=False),
            now,
            now,
        ),
    )


def record_run(connection: sqlite3.Connection, stats: ImageGenerationStats) -> None:
    connection.execute(
        """
        INSERT INTO image_generation_runs (
            run_id, started_at, finished_at, image_mode, items_seen,
            images_generated, archives_written, fallback_used, errors, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            stats.run_id,
            stats.started_at,
            stats.finished_at,
            stats.image_mode,
            stats.items_seen,
            stats.images_generated,
            stats.archives_written,
            stats.fallback_used,
            stats.errors,
            stats.notes,
        ),
    )


def run_image_generation(
    db_path: Path,
    image_output_dir: Path,
    archive_root: Path,
    image_mode: str = "offline",
    max_items: int | None = None,
    archive_date: str | None = None,
) -> tuple[ImageGenerationStats, Path, list[Path]]:
    if image_mode not in IMAGE_MODE_CHOICES:
        raise ValueError(f"Unsupported image_mode: {image_mode}")

    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    logger, log_path = setup_logger(run_id)
    stats = ImageGenerationStats(run_id=run_id, started_at=utc_now(), image_mode=image_mode)
    generated_at = utc_now()
    archive_date = archive_date or local_date_slug()
    output_paths: list[Path] = []

    logger.info("Starting Stage 11 image generation run: %s", run_id)
    logger.info("Image mode: %s", image_mode)
    logger.info("Image output dir: %s", image_output_dir)
    logger.info("Archive root: %s", archive_root)

    config = load_image_config(load_dotenv=image_mode != "offline")
    if image_mode == "offline":
        config = ImageConfig(force_offline=True, fallback_on_error=True)
    elif image_mode == "online":
        config = ImageConfig(**{**asdict(config), "force_offline": False, "fallback_on_error": False})

    logger.info(
        "Sanitized image config: %s",
        json.dumps(image_config_status(config), ensure_ascii=False),
    )

    apply_schema(db_path, SQLITE_SCHEMA_PATH)
    with sqlite3.connect(db_path) as connection:
        items = select_content_items(connection, max_items=max_items)
        stats.items_seen = len(items)

        for item in items:
            try:
                artifact, used_fallback = build_artifact(
                    item,
                    image_mode=image_mode,
                    config=config,
                    image_output_dir=image_output_dir,
                    archive_root=archive_root,
                    archive_date=archive_date,
                    run_id=run_id,
                    generated_at=generated_at,
                    logger=logger,
                )
                upsert_image_result(connection, artifact)
                output_paths.extend([
                    artifact.image_path,
                    artifact.archive_post_path,
                    artifact.archive_dir / "manifest.json",
                ])
                stats.images_generated += 1
                stats.archives_written += 1
                if used_fallback:
                    stats.fallback_used += 1
                logger.info(
                    "IMAGE_READY | %s | status=%s | image=%s | archive=%s",
                    artifact.primary_category,
                    artifact.status,
                    artifact.image_path,
                    artifact.archive_dir,
                )
            except Exception as exc:  # noqa: BLE001 - keep per-category errors isolated.
                stats.errors += 1
                logger.error("Failed image/archive generation for %s: %s", item["primary_category"], exc)

        stats.finished_at = utc_now()
        stats.notes = (
            "Stage 11 generated or fallback-rendered one 16:9 visual per final "
            "LinkedIn content record, updated post Markdown, and wrote archive bundles. "
            f"image_mode={image_mode}."
        )
        record_run(connection, stats)

    logger.info(
        "Completed Stage 11 image generation. items=%s images=%s archives=%s fallback=%s errors=%s",
        stats.items_seen,
        stats.images_generated,
        stats.archives_written,
        stats.fallback_used,
        stats.errors,
    )
    return stats, log_path, output_paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Stage 11 image generation and content archive.")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DATABASE_PATH,
        help="SQLite database path.",
    )
    parser.add_argument(
        "--image-output-dir",
        type=Path,
        default=IMAGE_OUTPUT_DIR,
        help="Directory for generated image files.",
    )
    parser.add_argument(
        "--archive-root",
        type=Path,
        default=CONTENT_ARCHIVE_DIR,
        help="Root directory for archived content bundles.",
    )
    parser.add_argument(
        "--image-mode",
        choices=IMAGE_MODE_CHOICES,
        default="offline",
        help="Image behavior: offline, auto, or online. Default: offline.",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Optional limit for handoff testing.",
    )
    parser.add_argument(
        "--archive-date",
        default=None,
        help="Optional archive date folder in YYYY-MM-DD format. Defaults to today's local date.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    stats, log_path, output_paths = run_image_generation(
        args.db_path,
        args.image_output_dir,
        args.archive_root,
        args.image_mode,
        max_items=args.max_items,
        archive_date=args.archive_date,
    )

    print("\nStage 11 image generation and archive completed")
    print(f"Run ID: {stats.run_id}")
    print(f"Database: {args.db_path}")
    print(f"Image mode: {stats.image_mode}")
    print(f"Items seen: {stats.items_seen}")
    print(f"Images generated: {stats.images_generated}")
    print(f"Archive bundles written: {stats.archives_written}")
    print(f"Fallback used: {stats.fallback_used}")
    print(f"Errors: {stats.errors}")
    print("Output files:")
    for output_path in output_paths:
        print(f"- {output_path}")
    print(f"Log file: {log_path}")
    return 0 if stats.errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
