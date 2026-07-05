from __future__ import annotations

import logging
import re
from collections.abc import Mapping

AUTH_RE = re.compile(r"(Bearer\s+)([A-Za-z0-9._=+\-/]+)")


def mask_secret(value: str | None, visible: int = 4) -> str | None:
    if value is None:
        return None
    if len(value) <= visible:
        return "***"
    return f"{value[:visible]}***"


def redact_text(value: object) -> str:
    return AUTH_RE.sub(r"\1***", str(value))


def redact_headers(headers: Mapping[str, str] | None) -> dict[str, str]:
    if not headers:
        return {}
    redacted: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() == "authorization":
            redacted[key] = "Bearer ***" if value else ""
        else:
            redacted[key] = redact_text(value)
    return redacted


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

