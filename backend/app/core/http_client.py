from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any
from urllib.parse import urljoin

import requests

from app.core.errors import ProviderErrorType, map_http_error, provider_error
from app.core.logging import get_logger, redact_headers, redact_text


class ProviderHttpClient:
    retry_status_codes = {429, 502, 503, 504}

    def __init__(
        self,
        *,
        provider: str,
        app_key: str | None,
        timeout: float = 30,
        max_retries: int = 2,
        backoff_seconds: float = 0.25,
    ) -> None:
        self.provider = provider
        self.app_key = app_key
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.backoff_seconds = max(0.0, backoff_seconds)
        self.session = requests.Session()
        self.logger = get_logger(f"app.integrations.{provider}.http")

    def get_json(
        self,
        url: str,
        *,
        capability: str,
        request_id: str,
        request_id_param: str = "requestId",
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        response = self._request(
            "GET",
            url,
            capability=capability,
            request_id=request_id,
            request_id_param=request_id_param,
            headers=headers,
            params=params,
        )
        return self._json(response, capability=capability, request_id=request_id)

    def post_json(
        self,
        url: str,
        *,
        capability: str,
        request_id: str,
        payload: dict[str, Any],
        request_id_param: str = "requestId",
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        selected_headers = {"Content-Type": "application/json; charset=utf-8", **(headers or {})}
        response = self._request(
            "POST",
            url,
            capability=capability,
            request_id=request_id,
            request_id_param=request_id_param,
            headers=selected_headers,
            params=params,
            json=payload,
        )
        return self._json(response, capability=capability, request_id=request_id)

    def post_form(
        self,
        url: str,
        *,
        capability: str,
        request_id: str,
        data: dict[str, Any],
        request_id_param: str = "requestId",
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        selected_headers = {"Content-Type": "application/x-www-form-urlencoded", **(headers or {})}
        response = self._request(
            "POST",
            url,
            capability=capability,
            request_id=request_id,
            request_id_param=request_id_param,
            headers=selected_headers,
            params=params,
            data=data,
        )
        return self._json(response, capability=capability, request_id=request_id)

    def post_stream_json(
        self,
        url: str,
        *,
        capability: str,
        request_id: str,
        payload: dict[str, Any],
        request_id_param: str = "request_id",
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Iterator[str]:
        selected_headers = {"Content-Type": "application/json; charset=utf-8", **(headers or {})}
        response = self._request(
            "POST",
            url,
            capability=capability,
            request_id=request_id,
            request_id_param=request_id_param,
            headers=selected_headers,
            params=params,
            json=payload,
            stream=True,
        )
        for raw_line in response.iter_lines():
            if not raw_line:
                continue
            yield raw_line.decode("utf-8").strip()

    def _request(
        self,
        method: str,
        url: str,
        *,
        capability: str,
        request_id: str,
        request_id_param: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        stream: bool = False,
    ) -> requests.Response:
        merged_params = dict(params or {})
        merged_params.setdefault(request_id_param, request_id)
        merged_headers = {"Authorization": f"Bearer {self.app_key or ''}", **(headers or {})}
        self.logger.info(
            "provider_request method=%s url=%s headers=%s params=%s",
            method,
            redact_text(url),
            redact_headers(merged_headers),
            merged_params,
        )
        response: requests.Response | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=merged_headers,
                    params=merged_params,
                    json=json,
                    data=data,
                    files=files,
                    timeout=self.timeout,
                    stream=stream,
                )
            except requests.Timeout as exc:
                if attempt < self.max_retries:
                    self._sleep_before_retry(attempt)
                    continue
                raise provider_error(
                    self.provider,
                    capability,
                    ProviderErrorType.TIMEOUT,
                    "Provider request timed out.",
                    request_id=request_id,
                    raw_error=str(exc),
                ) from exc
            except requests.RequestException as exc:
                if attempt < self.max_retries:
                    self._sleep_before_retry(attempt)
                    continue
                raise provider_error(
                    self.provider,
                    capability,
                    ProviderErrorType.PROVIDER_UNAVAILABLE,
                    "Provider network request failed.",
                    request_id=request_id,
                    raw_error=str(exc),
                ) from exc
            if response.status_code in self.retry_status_codes and attempt < self.max_retries:
                self._sleep_before_retry(attempt)
                continue
            break
        if response is None:
            raise provider_error(
                self.provider,
                capability,
                ProviderErrorType.UNKNOWN_ERROR,
                "Provider request did not return a response.",
                request_id=request_id,
            )
        if response.status_code >= 400:
            raise map_http_error(
                response.status_code,
                self._safe_response_body(response),
                provider=self.provider,
                capability=capability,
                request_id=request_id,
                trace_id=response.headers.get("X-Request-Id"),
            )
        return response

    def _sleep_before_retry(self, attempt: int) -> None:
        if self.backoff_seconds <= 0:
            return
        time.sleep(self.backoff_seconds * (2**attempt))

    def _json(self, response: requests.Response, *, capability: str, request_id: str) -> Any:
        try:
            return response.json()
        except ValueError as exc:
            raise provider_error(
                self.provider,
                capability,
                ProviderErrorType.PARSE_FAILED,
                "Provider returned non-JSON response.",
                status_code=response.status_code,
                request_id=request_id,
                raw_error=response.text[:500],
            ) from exc

    @staticmethod
    def _safe_response_body(response: requests.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return response.text[:500]


def join_url(base_url: str, path: str) -> str:
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
