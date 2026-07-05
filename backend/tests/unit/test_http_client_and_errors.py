from __future__ import annotations

import json
import logging

import pytest
import requests

from app.core.errors import (
    ProviderError,
    ProviderErrorType,
    map_http_error,
    map_provider_body_error,
    provider_error,
)
from app.core.http_client import ProviderHttpClient


class SequenceSession:
    def __init__(self, responses: list[requests.Response]) -> None:
        self.responses = responses
        self.calls = 0

    def request(self, **kwargs: object) -> requests.Response:
        self.calls += 1
        return self.responses.pop(0)


def response(status_code: int, body: object, content_type: str = "application/json") -> requests.Response:
    selected = requests.Response()
    selected.status_code = status_code
    selected.headers["Content-Type"] = content_type
    selected._content = json.dumps(body).encode("utf-8") if content_type == "application/json" else str(body).encode()
    return selected


def test_http_client_retries_429_then_succeeds() -> None:
    client = ProviderHttpClient(provider="vivo", app_key="secret-key", max_retries=1, backoff_seconds=0)
    session = SequenceSession([response(429, {"message": "Rate limit exceeded"}), response(200, {"ok": True})])
    client.session = session  # type: ignore[assignment]

    assert client.post_json("https://example.test", capability="llm", request_id="rid", payload={}) == {"ok": True}
    assert session.calls == 2


def test_http_client_maps_non_json_response_to_parse_failed() -> None:
    client = ProviderHttpClient(provider="vivo", app_key="secret-key", max_retries=0)
    client.session = SequenceSession([response(200, "<html>bad</html>", content_type="text/html")])  # type: ignore[assignment]

    with pytest.raises(ProviderError) as exc:
        client.post_json("https://example.test", capability="llm", request_id="rid", payload={})

    assert exc.value.error_type == ProviderErrorType.PARSE_FAILED


def test_error_mapping_covers_http_and_body_cases() -> None:
    assert map_http_error(401, {"message": "invalid api-key"}, provider="vivo", capability="llm").error_type == (
        ProviderErrorType.AUTH_FAILED
    )
    assert map_http_error(429, {"message": "Rate limit exceeded"}, provider="vivo", capability="llm").error_type == (
        ProviderErrorType.RATE_LIMITED
    )
    body_error = map_provider_body_error(
        {"code": 1001, "message": "bad"},
        provider="vivo",
        capability="media",
    )
    assert body_error is not None
    assert body_error.error_type == ProviderErrorType.UNKNOWN_ERROR
    data_null_error = map_provider_body_error({"data": None}, provider="vivo", capability="embedding")
    assert data_null_error is not None
    assert data_null_error.error_type == ProviderErrorType.PARSE_FAILED


def test_authorization_is_redacted_from_logs(caplog: pytest.LogCaptureFixture) -> None:
    client = ProviderHttpClient(provider="vivo", app_key="dummy-redaction-token", max_retries=0)
    client.session = SequenceSession([response(200, {"ok": True})])  # type: ignore[assignment]

    with caplog.at_level(logging.INFO, logger="app.integrations.vivo.http"):
        client.post_json("https://example.test", capability="llm", request_id="rid", payload={})

    log_output = caplog.text
    assert "dummy-redaction-token" not in log_output
    assert "Bearer ***" in log_output


def test_provider_error_str_does_not_include_raw_secret() -> None:
    error = provider_error(
        "vivo",
        "llm",
        ProviderErrorType.AUTH_FAILED,
        "Provider authentication failed.",
        raw_error={"Authorization": "Bearer dummy-redaction-token", "VIVO_APP_KEY": "dummy-redaction-token"},
    )

    assert "dummy-redaction-token" not in str(error)
    assert "Provider authentication failed." in str(error)
