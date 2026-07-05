from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, cast


class ProviderErrorType(StrEnum):
    MISSING_CONFIG = "missing_config"
    AUTH_FAILED = "auth_failed"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMITED = "rate_limited"
    DAILY_LIMIT = "daily_limit"
    INVALID_REQUEST = "invalid_request"
    TIMEOUT = "timeout"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PARSE_FAILED = "parse_failed"
    CONTENT_BLOCKED = "content_blocked"
    UNSUPPORTED_FORMAT = "unsupported_format"
    UNKNOWN_ERROR = "unknown_error"


@dataclass(slots=True)
class ProviderError(Exception):
    provider: str
    capability: str
    error_type: ProviderErrorType | str
    safe_message: str
    status_code: int | None = None
    request_id: str | None = None
    trace_id: str | None = None
    raw_error: Any | None = None

    def __post_init__(self) -> None:
        Exception.__init__(self, self.safe_message)
        if isinstance(self.error_type, str):
            self.error_type = ProviderErrorType(self.error_type)

    def to_safe_dict(self) -> dict[str, Any]:
        error_type = cast(ProviderErrorType, self.error_type)
        return {
            "provider": self.provider,
            "capability": self.capability,
            "error_type": error_type.value,
            "safe_message": self.safe_message,
            "status_code": self.status_code,
            "request_id": self.request_id,
            "trace_id": self.trace_id,
        }

    def to_debug_dict(self) -> dict[str, Any]:
        error_type = cast(ProviderErrorType, self.error_type)
        data = asdict(self)
        data["error_type"] = error_type.value
        return data


def provider_error(
    provider: str,
    capability: str,
    error_type: ProviderErrorType,
    safe_message: str,
    *,
    status_code: int | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    raw_error: Any | None = None,
) -> ProviderError:
    return ProviderError(
        provider=provider,
        capability=capability,
        error_type=error_type,
        safe_message=safe_message,
        status_code=status_code,
        request_id=request_id,
        trace_id=trace_id,
        raw_error=raw_error,
    )


def map_http_error(
    status_code: int,
    body: Any,
    *,
    provider: str,
    capability: str,
    request_id: str | None = None,
    trace_id: str | None = None,
) -> ProviderError:
    text = str(body).lower()
    if status_code == 401:
        error_type = ProviderErrorType.AUTH_FAILED
        safe_message = "Provider authentication failed."
    elif status_code == 403 or "not having this ability" in text or "permission" in text:
        error_type = ProviderErrorType.PERMISSION_DENIED
        safe_message = "Provider permission denied for this capability."
    elif status_code == 429 or "rate limit" in text or "too many" in text:
        error_type = ProviderErrorType.RATE_LIMITED
        safe_message = "Provider rate limit exceeded."
    elif "daily" in text or "quota" in text or "limit" in text and "day" in text:
        error_type = ProviderErrorType.DAILY_LIMIT
        safe_message = "Provider daily limit exceeded."
    elif "content" in text and ("blocked" in text or "audit" in text or "sensitive" in text):
        error_type = ProviderErrorType.CONTENT_BLOCKED
        safe_message = "Provider blocked the content."
    elif 400 <= status_code < 500:
        error_type = ProviderErrorType.INVALID_REQUEST
        safe_message = "Provider rejected the request."
    elif status_code in {502, 503, 504}:
        error_type = ProviderErrorType.PROVIDER_UNAVAILABLE
        safe_message = "Provider service is unavailable."
    else:
        error_type = ProviderErrorType.UNKNOWN_ERROR
        safe_message = "Provider returned an unexpected error."
    return provider_error(
        provider,
        capability,
        error_type,
        safe_message,
        status_code=status_code,
        request_id=request_id,
        trace_id=trace_id,
        raw_error=body,
    )


def map_provider_body_error(
    body: Any,
    *,
    provider: str,
    capability: str,
    request_id: str | None = None,
    trace_id: str | None = None,
) -> ProviderError | None:
    if not isinstance(body, dict):
        return None
    if isinstance(body.get("error"), dict):
        text = str(body["error"]).lower()
        if "not support" in text or "invalid" in text:
            error_type = ProviderErrorType.INVALID_REQUEST
        elif "rate" in text or "too many" in text:
            error_type = ProviderErrorType.RATE_LIMITED
        elif "permission" in text or "not having this ability" in text:
            error_type = ProviderErrorType.PERMISSION_DENIED
        else:
            error_type = ProviderErrorType.UNKNOWN_ERROR
        return provider_error(
            provider,
            capability,
            error_type,
            "Provider returned an error response.",
            request_id=request_id,
            trace_id=trace_id,
            raw_error=body,
        )
    if "code" in body and body.get("code") not in {0, "0", None}:
        code_text = str(body.get("code"))
        if code_text == "-3002":
            error_type = ProviderErrorType.PROVIDER_UNAVAILABLE
            safe_message = "Provider service is unavailable."
        elif "rate" in str(body).lower():
            error_type = ProviderErrorType.RATE_LIMITED
            safe_message = "Provider rate limit exceeded."
        else:
            error_type = ProviderErrorType.UNKNOWN_ERROR
            safe_message = "Provider returned a non-zero code."
        return provider_error(
            provider,
            capability,
            error_type,
            safe_message,
            request_id=request_id,
            trace_id=trace_id,
            raw_error=body,
        )
    if "data" in body and body.get("data") is None:
        return provider_error(
            provider,
            capability,
            ProviderErrorType.PARSE_FAILED,
            "Provider response data is empty.",
            request_id=request_id,
            trace_id=trace_id,
            raw_error=body,
        )
    return None


def map_query_rewrite_code(
    code: int,
    *,
    provider: str,
    request_id: str | None = None,
    raw_error: Any | None = None,
) -> ProviderError:
    code_map: dict[int, tuple[ProviderErrorType, str]] = {
        -2: (ProviderErrorType.INVALID_REQUEST, "Query rewrite prompt format is invalid."),
        -3: (ProviderErrorType.INVALID_REQUEST, "Query is too long for rewrite."),
        -4: (ProviderErrorType.CONTENT_BLOCKED, "Query rewrite content was blocked."),
        -5: (ProviderErrorType.CONTENT_BLOCKED, "Query rewrite content was blocked."),
        -6: (ProviderErrorType.INVALID_REQUEST, "Query rewrite history is incomplete."),
        -8: (ProviderErrorType.INVALID_REQUEST, "Query rewrite template is unsupported."),
        -3002: (ProviderErrorType.PROVIDER_UNAVAILABLE, "Query rewrite service failed."),
    }
    error_type, safe_message = code_map.get(
        code,
        (ProviderErrorType.UNKNOWN_ERROR, "Query rewrite returned an unknown error."),
    )
    return provider_error(
        provider,
        "query_rewrite",
        error_type,
        safe_message,
        request_id=request_id,
        raw_error=raw_error,
    )
