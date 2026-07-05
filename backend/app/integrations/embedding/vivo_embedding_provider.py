from __future__ import annotations

import uuid
from typing import Any

from app.core.config import VivoSettings, load_settings
from app.core.errors import ProviderError, ProviderErrorType, provider_error
from app.core.http_client import ProviderHttpClient, join_url
from app.integrations.embedding.base import EmbeddingProvider
from app.schemas.embedding import EmbeddingResult


class VivoEmbeddingProvider(EmbeddingProvider):
    provider = "vivo"
    capability = "embedding"
    supported_models = {"m3e-base", "bge-base-zh-v1.5"}
    max_text_length = 8192

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

    def embed(self, texts: str | list[str], *, model: str | None = None) -> EmbeddingResult:
        request_id = str(uuid.uuid4())
        normalized_texts = self._normalize_texts(texts, request_id)
        selected_model = model or self.settings.vivo_embedding_model
        if selected_model not in self.supported_models:
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.INVALID_REQUEST,
                "Embedding model is not supported.",
                request_id=request_id,
                raw_error=selected_model,
            )
        self.settings.require_credentials(self.capability)
        payload = {"model_name": selected_model, "sentences": normalized_texts}
        try:
            data = self.http_client.post_json(
                join_url(self.settings.vivo_base_url, "/embedding-model-api/predict/batch"),
                capability=self.capability,
                request_id=request_id,
                request_id_param="requestId",
                payload=payload,
            )
            vectors = self._parse_vectors(data, len(normalized_texts), request_id)
            return EmbeddingResult(
                texts=normalized_texts,
                vectors=vectors,
                dimension=len(vectors[0]),
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
                "Embedding provider call failed.",
                request_id=request_id,
                raw_error=str(exc),
            ) from exc

    def _normalize_texts(self, texts: str | list[str], request_id: str) -> list[str]:
        values = [texts] if isinstance(texts, str) else list(texts)
        if not values:
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.INVALID_REQUEST,
                "Embedding texts cannot be empty.",
                request_id=request_id,
            )
        for text in values:
            if not isinstance(text, str) or not text.strip():
                raise provider_error(
                    self.provider,
                    self.capability,
                    ProviderErrorType.INVALID_REQUEST,
                    "Embedding text cannot be empty.",
                    request_id=request_id,
                )
            if len(text) > self.max_text_length:
                raise provider_error(
                    self.provider,
                    self.capability,
                    ProviderErrorType.INVALID_REQUEST,
                    "Embedding text is too long.",
                    request_id=request_id,
                )
        return values

    def _parse_vectors(self, data: Any, expected_count: int, request_id: str) -> list[list[float]]:
        raw_vectors = data.get("data") if isinstance(data, dict) else None
        if not isinstance(raw_vectors, list) or not raw_vectors:
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.PARSE_FAILED,
                "Embedding provider response data is empty.",
                request_id=request_id,
                raw_error=data,
            )
        if len(raw_vectors) != expected_count:
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.PARSE_FAILED,
                "Embedding vector count does not match input count.",
                request_id=request_id,
                raw_error=data,
            )
        vectors: list[list[float]] = []
        dimension: int | None = None
        for vector in raw_vectors:
            if not isinstance(vector, list) or not vector:
                raise provider_error(
                    self.provider,
                    self.capability,
                    ProviderErrorType.PARSE_FAILED,
                    "Embedding vector shape is invalid.",
                    request_id=request_id,
                    raw_error=data,
                )
            converted = [float(value) for value in vector]
            if dimension is None:
                dimension = len(converted)
            elif len(converted) != dimension:
                raise provider_error(
                    self.provider,
                    self.capability,
                    ProviderErrorType.PARSE_FAILED,
                    "Embedding vector dimensions are inconsistent.",
                    request_id=request_id,
                    raw_error=data,
                )
            vectors.append(converted)
        return vectors
