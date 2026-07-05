from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from app.core.errors import ProviderErrorType, provider_error

BACKEND_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = BACKEND_ROOT.parent
DEFAULT_CORS_ALLOW_ORIGINS = (
    "https://appassets.androidplatform.net,"
    "http://8.148.69.255,http://8.148.69.255:8000,"
    "http://localhost,http://localhost:3000,http://localhost:5173,"
    "http://127.0.0.1,http://127.0.0.1:3000,http://127.0.0.1:5173,"
    "http://10.0.2.2,http://10.0.2.2:8000"
)


@dataclass(frozen=True, slots=True)
class VivoSettings:
    database_url: str = f"sqlite:///{BACKEND_ROOT / 'echolearn.db'}"
    jwt_secret_key: str = "local-dev-secret-change-me"
    access_token_minutes: int = 60
    refresh_token_days: int = 30
    local_storage_dir: str = str(BACKEND_ROOT / "storage_data")
    max_upload_bytes: int = 50 * 1024 * 1024
    allowed_upload_extensions: str = ".txt,.md,.pdf,.doc,.docx,.ppt,.pptx,.jpg,.jpeg,.png,.webp,.wav,.mp3,.m4a"
    vivo_app_id: str | None = None
    vivo_app_key: str | None = None
    vivo_base_url: str = "https://api-ai.vivo.com.cn"
    vivo_llm_base_url: str = "https://api-ai.vivo.com.cn/v1"
    vivo_llm_model: str = "Doubao-Seed-2.0-mini"
    vivo_llm_text_model: str = "Doubao-Seed-2.0-mini"
    vivo_llm_stream_model: str = "Doubao-Seed-2.0-mini"
    vivo_image_understanding_model: str = "Doubao-Seed-2.0-mini"
    vivo_reasoning_model: str = "Doubao-Seed-2.0-mini"
    vivo_vision_model: str = "Volc-DeepSeek-V3.2"
    vivo_embedding_model: str = "m3e-base"
    vivo_rerank_model: str = "bge-reranker-large"
    http_timeout_seconds: float = 30
    http_max_retries: int = 2
    http_backoff_seconds: float = 0.25
    cors_allow_origins: str = DEFAULT_CORS_ALLOW_ORIGINS
    email_enabled: bool = False
    smtp_host: str | None = None
    smtp_port: int = 465
    smtp_use_ssl: bool = True
    smtp_use_tls: bool = False
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_from_name: str = "双生"
    email_code_expire_minutes: int = 10
    email_code_length: int = 6

    def require_credentials(self, capability: str) -> None:
        missing: list[str] = []
        if not self.vivo_app_id:
            missing.append("VIVO_APP_ID")
        if not self.vivo_app_key:
            missing.append("VIVO_APP_KEY")
        if missing:
            raise provider_error(
                "vivo",
                capability,
                ProviderErrorType.MISSING_CONFIG,
                f"Missing required provider config: {', '.join(missing)}.",
                raw_error={"missing": missing},
            )


def _normalize_key(key: str) -> str:
    cleaned = key.strip().upper().replace("-", "_")
    aliases = {
        "APPID": "VIVO_APP_ID",
        "APP_ID": "VIVO_APP_ID",
        "VIVO_APPID": "VIVO_APP_ID",
        "APPKEY": "VIVO_APP_KEY",
        "APP_KEY": "VIVO_APP_KEY",
        "VIVO_APPKEY": "VIVO_APP_KEY",
    }
    return aliases.get(cleaned, cleaned)


def _parse_env_lines(lines: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    pending_key: str | None = None
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line and not line.upper().startswith("SK-"):
            key, value = line.split("=", 1)
            values[_normalize_key(key)] = value.strip().strip("\"'")
            pending_key = None
            continue
        if ":" in line and not line.upper().startswith(("HTTP:", "HTTPS:")):
            key, value = line.split(":", 1)
            values[_normalize_key(key)] = value.strip().strip("\"'")
            pending_key = None
            continue
        normalized = _normalize_key(line)
        if normalized in {"VIVO_APP_ID", "VIVO_APP_KEY"}:
            pending_key = normalized
            continue
        if pending_key:
            values[pending_key] = line.strip().strip("\"'")
            pending_key = None
    return values


def read_env_file(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = path.read_text(encoding="gbk")
    return _parse_env_lines(text.splitlines())


def default_env_files() -> list[Path]:
    return [
        BACKEND_ROOT / ".env",
        WORKSPACE_ROOT / ".env",
    ]


def load_settings(
    env_file: str | Path | None = None,
    *,
    include_os_environ: bool = True,
    search_default_env_files: bool = True,
    require_credentials: bool = False,
    capability: str = "config",
) -> VivoSettings:
    raw: dict[str, str] = {}
    paths: list[Path] = []
    if search_default_env_files:
        paths.extend(default_env_files())
    if env_file is not None:
        paths.insert(0, Path(env_file))
    for path in paths:
        if path.exists():
            raw.update(read_env_file(path))
            break
    if include_os_environ:
        raw.update({k: v for k, v in os.environ.items() if k.startswith(("VIVO_", "HTTP_", "EMAIL_", "SMTP_"))})
    settings = settings_from_mapping(raw)
    if require_credentials:
        settings.require_credentials(capability)
    return settings


def settings_from_mapping(raw: Mapping[str, str | None]) -> VivoSettings:
    def get(name: str, default: str | None = None) -> str | None:
        value = raw.get(name)
        return value if value not in {"", None} else default

    timeout_raw = get("HTTP_TIMEOUT_SECONDS", "30")
    try:
        timeout = float(timeout_raw or "30")
    except ValueError:
        timeout = 30.0
    return VivoSettings(
        database_url=get("DATABASE_URL", f"sqlite:///{BACKEND_ROOT / 'echolearn.db'}") or f"sqlite:///{BACKEND_ROOT / 'echolearn.db'}",
        jwt_secret_key=get("JWT_SECRET_KEY", "local-dev-secret-change-me") or "local-dev-secret-change-me",
        access_token_minutes=_parse_int(get("ACCESS_TOKEN_MINUTES", "60"), default=60),
        refresh_token_days=_parse_int(get("REFRESH_TOKEN_DAYS", "30"), default=30),
        local_storage_dir=get("LOCAL_STORAGE_DIR", str(BACKEND_ROOT / "storage_data")) or str(BACKEND_ROOT / "storage_data"),
        max_upload_bytes=_parse_int(get("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)), default=50 * 1024 * 1024),
        allowed_upload_extensions=get(
            "ALLOWED_UPLOAD_EXTENSIONS",
            ".txt,.md,.pdf,.doc,.docx,.ppt,.pptx,.jpg,.jpeg,.png,.webp,.wav,.mp3,.m4a",
        )
        or ".txt,.md,.pdf,.doc,.docx,.ppt,.pptx,.jpg,.jpeg,.png,.webp,.wav,.mp3,.m4a",
        vivo_app_id=get("VIVO_APP_ID"),
        vivo_app_key=get("VIVO_APP_KEY"),
        vivo_base_url=get("VIVO_BASE_URL", "https://api-ai.vivo.com.cn") or "https://api-ai.vivo.com.cn",
        vivo_llm_base_url=get("VIVO_LLM_BASE_URL", "https://api-ai.vivo.com.cn/v1")
        or "https://api-ai.vivo.com.cn/v1",
        vivo_llm_model=get("VIVO_LLM_MODEL", "Doubao-Seed-2.0-mini") or "Doubao-Seed-2.0-mini",
        vivo_llm_text_model=get(
            "VIVO_LLM_TEXT_MODEL",
            get("VIVO_LLM_MODEL", "Doubao-Seed-2.0-mini"),
        )
        or "Doubao-Seed-2.0-mini",
        vivo_llm_stream_model=get(
            "VIVO_LLM_STREAM_MODEL",
            get("VIVO_LLM_MODEL", "Doubao-Seed-2.0-mini"),
        )
        or "Doubao-Seed-2.0-mini",
        vivo_image_understanding_model=get("VIVO_IMAGE_UNDERSTANDING_MODEL", "Doubao-Seed-2.0-mini")
        or "Doubao-Seed-2.0-mini",
        vivo_reasoning_model=get(
            "VIVO_REASONING_MODEL",
            get("VIVO_LLM_MODEL", "Doubao-Seed-2.0-mini"),
        )
        or "Doubao-Seed-2.0-mini",
        vivo_vision_model=get("VIVO_VISION_MODEL", "Volc-DeepSeek-V3.2") or "Volc-DeepSeek-V3.2",
        vivo_embedding_model=get("VIVO_EMBEDDING_MODEL", "m3e-base") or "m3e-base",
        vivo_rerank_model=get("VIVO_RERANK_MODEL", "bge-reranker-large") or "bge-reranker-large",
        http_timeout_seconds=timeout,
        http_max_retries=_parse_int(get("HTTP_MAX_RETRIES", "2"), default=2),
        http_backoff_seconds=_parse_float(get("HTTP_BACKOFF_SECONDS", "0.25"), default=0.25),
        cors_allow_origins=get(
            "CORS_ALLOW_ORIGINS",
            DEFAULT_CORS_ALLOW_ORIGINS,
        )
        or DEFAULT_CORS_ALLOW_ORIGINS,
        email_enabled=_parse_bool(get("EMAIL_ENABLED", "false"), default=False),
        smtp_host=get("SMTP_HOST"),
        smtp_port=_parse_int(get("SMTP_PORT", "465"), default=465),
        smtp_use_ssl=_parse_bool(get("SMTP_USE_SSL", "true"), default=True),
        smtp_use_tls=_parse_bool(get("SMTP_USE_TLS", "false"), default=False),
        smtp_username=get("SMTP_USERNAME"),
        smtp_password=get("SMTP_PASSWORD"),
        smtp_from_email=get("SMTP_FROM_EMAIL", get("SMTP_USERNAME")),
        smtp_from_name=get("SMTP_FROM_NAME", "双生") or "双生",
        email_code_expire_minutes=_parse_int(get("EMAIL_CODE_EXPIRE_MINUTES", "10"), default=10),
        email_code_length=_parse_int(get("EMAIL_CODE_LENGTH", "6"), default=6),
    )


def _parse_int(value: str | None, *, default: int) -> int:
    try:
        return int(value or default)
    except ValueError:
        return default


def _parse_float(value: str | None, *, default: float) -> float:
    try:
        return float(value or default)
    except ValueError:
        return default


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return default


def has_real_vivo_credentials(settings: VivoSettings | None = None) -> bool:
    selected = settings or load_settings()
    return bool(
        selected.vivo_app_id
        and selected.vivo_app_key
        and selected.vivo_app_id != "your_app_id"
        and selected.vivo_app_key != "your_app_key"
    )
