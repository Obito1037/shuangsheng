from __future__ import annotations

import uuid
from typing import Any

from app.core.config import VivoSettings, load_settings
from app.core.errors import ProviderError, ProviderErrorType, provider_error
from app.core.http_client import ProviderHttpClient, join_url
from app.integrations.similarity.base import SimilarityProvider
from app.schemas.similarity import SimilarityResult


class VivoSimilarityProvider(SimilarityProvider):
    provider = "vivo"
    capability = "similarity"
    supported_models = {"bge-reranker-large"}

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

    def rerank(self, query: str, sentences: list[str], *, model: str | None = None) -> SimilarityResult:
        request_id = str(uuid.uuid4())
        self._validate_input(query, sentences, request_id)
        selected_model = model or self.settings.vivo_rerank_model
        if selected_model not in self.supported_models:
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.INVALID_REQUEST,
                "Similarity model is not supported.",
                request_id=request_id,
                raw_error=selected_model,
            )
        self.settings.require_credentials(self.capability)
        payload = {"model_name": selected_model, "query": query, "sentences": sentences}
        try:
            data = self.http_client.post_json(
                join_url(self.settings.vivo_base_url, "/rerank"),
                capability=self.capability,
                request_id=request_id,
                request_id_param="requestId",
                payload=payload,
            )
            scores = self._parse_scores(data, len(sentences), request_id)
            return SimilarityResult(
                query=query,
                sentences=sentences,
                scores=scores,
                provider=self.provider,
                model=selected_model,
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.UNKNOWN_ERROR,
                "Similarity provider call failed.",
                request_id=request_id,
                raw_error=str(exc),
            ) from exc

    def _validate_input(self, query: str, sentences: list[str], request_id: str) -> None:
        if not isinstance(query, str) or not query.strip():
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.INVALID_REQUEST,
                "Similarity query cannot be empty.",
                request_id=request_id,
            )
        if not sentences:
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.INVALID_REQUEST,
                "Similarity sentences cannot be empty.",
                request_id=request_id,
            )
        if any(not isinstance(sentence, str) or not sentence.strip() for sentence in sentences):
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.INVALID_REQUEST,
                "Similarity sentence cannot be empty.",
                request_id=request_id,
            )

    def _parse_scores(self, data: Any, expected_count: int, request_id: str) -> list[float]:
        raw_scores = data.get("data") if isinstance(data, dict) else None
        if not isinstance(raw_scores, list) or len(raw_scores) != expected_count:
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.PARSE_FAILED,
                "Similarity score count does not match input count.",
                request_id=request_id,
                raw_error=data,
            )
        try:
            return [float(score) for score in raw_scores]
        except (TypeError, ValueError) as exc:
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.PARSE_FAILED,
                "Similarity scores must be numeric.",
                request_id=request_id,
                raw_error=data,
            ) from exc
