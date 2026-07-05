from __future__ import annotations

import uuid
from typing import Any

from app.core.config import VivoSettings, load_settings
from app.core.errors import (
    ProviderError,
    ProviderErrorType,
    map_query_rewrite_code,
    provider_error,
)
from app.core.http_client import ProviderHttpClient, join_url
from app.integrations.query_rewrite.base import QueryRewriteProvider
from app.schemas.query_rewrite import QueryRewriteResult, QueryRewriteTurn


class VivoQueryRewriteProvider(QueryRewriteProvider):
    provider = "vivo"
    capability = "query_rewrite"
    max_history_turns = 3
    max_query_length = 50

    def __init__(
        self,
        *,
        settings: VivoSettings | None = None,
        http_client: Any | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.http_client = http_client or ProviderHttpClient(
            provider=self.provider,
            app_key=self.settings.vivo_app_key,
            timeout=self.settings.http_timeout_seconds,
            max_retries=self.settings.http_max_retries,
            backoff_seconds=self.settings.http_backoff_seconds,
        )

    def rewrite(self, query: str, history: list[QueryRewriteTurn] | None = None) -> QueryRewriteResult:
        request_id = str(uuid.uuid4())
        self._validate_query(query, request_id)
        turns = list(history or [])
        if len(turns) > self.max_history_turns:
            turns = turns[-self.max_history_turns :]
        self.settings.require_credentials(self.capability)
        payload = {"prompts": self._build_prompts(query, turns)}
        try:
            data = self.http_client.post_json(
                join_url(self.settings.vivo_base_url, "/query_rewrite_base"),
                capability=self.capability,
                request_id=request_id,
                request_id_param="requestId",
                payload=payload,
            )
            return self._parse_result(data, query=query, request_id=request_id)
        except ProviderError:
            raise
        except Exception as exc:
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.UNKNOWN_ERROR,
                "Query rewrite provider call failed.",
                request_id=request_id,
                raw_error=str(exc),
            ) from exc

    def _validate_query(self, query: str, request_id: str) -> None:
        if not isinstance(query, str) or not query.strip():
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.INVALID_REQUEST,
                "Query rewrite query cannot be empty.",
                request_id=request_id,
            )
        if len(query) > self.max_query_length:
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.INVALID_REQUEST,
                "Query rewrite query is too long.",
                request_id=request_id,
            )

    def _build_prompts(self, query: str, history: list[QueryRewriteTurn]) -> list[list[str]]:
        slots = ["", "", "", "", "", ""]
        selected = history[-3:]
        offset = 3 - len(selected)
        for index, turn in enumerate(selected):
            base = (offset + index) * 2
            slots[base] = turn.question
            slots[base + 1] = turn.answer
        return [slots, [query]]

    def _parse_result(self, data: Any, *, query: str, request_id: str) -> QueryRewriteResult:
        if not isinstance(data, dict) or "code" not in data:
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.PARSE_FAILED,
                "Query rewrite response shape is invalid.",
                request_id=request_id,
                raw_error=data,
            )
        code = data.get("code")
        if code == -9:
            return QueryRewriteResult(original_query=query, rewritten_queries=[query], provider=self.provider)
        if code != 0:
            if code is None:
                raise provider_error(
                    self.provider,
                    self.capability,
                    ProviderErrorType.PARSE_FAILED,
                    "Query rewrite response code is missing.",
                    request_id=request_id,
                    raw_error=data,
                )
            raise map_query_rewrite_code(
                int(code),
                provider=self.provider,
                request_id=request_id,
                raw_error=data,
            )
        result = data.get("result")
        if not isinstance(result, list) or any(not isinstance(item, str) for item in result):
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.PARSE_FAILED,
                "Query rewrite result is invalid.",
                request_id=request_id,
                raw_error=data,
            )
        return QueryRewriteResult(original_query=query, rewritten_queries=result, provider=self.provider)
