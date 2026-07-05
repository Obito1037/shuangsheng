from __future__ import annotations

import base64
import json
import mimetypes
import uuid
from pathlib import Path
from typing import Any

from app.core.config import VivoSettings, load_settings
from app.core.errors import ProviderError, ProviderErrorType, provider_error
from app.core.http_client import ProviderHttpClient, join_url
from app.integrations.llm.base import LlmProvider
from app.schemas.llm import LlmMessage, LlmMessageResult
from app.schemas.vision import ImageUnderstandingResult


class VivoLlmProvider(LlmProvider):
    provider = "vivo"
    capability = "llm"
    image_capable_models = {
        "Doubao-Seed-2.0-mini",
        "Doubao-Seed-2.0-lite",
        "Doubao-Seed-2.0-pro",
    }

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

    def chat(self, messages: list[LlmMessage], **kwargs: Any) -> LlmMessageResult:
        request_id = str(uuid.uuid4())
        self._validate_messages(messages, request_id)
        self.settings.require_credentials(self.capability)
        kwargs.setdefault("model", self.settings.vivo_llm_text_model)
        payload = self._chat_payload(messages, stream=False, **kwargs)
        try:
            data = self.http_client.post_json(
                join_url(self.settings.vivo_llm_base_url, "/chat/completions"),
                capability=self.capability,
                request_id=request_id,
                request_id_param="request_id",
                payload=payload,
            )
            return self._parse_message_result(data, request_id=request_id, model=payload["model"])
        except ProviderError:
            raise
        except Exception as exc:
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.UNKNOWN_ERROR,
                "LLM provider call failed.",
                request_id=request_id,
                raw_error=str(exc),
            ) from exc

    def stream_chat(self, messages: list[LlmMessage], **kwargs: Any) -> LlmMessageResult:
        request_id = str(uuid.uuid4())
        self._validate_messages(messages, request_id)
        self.settings.require_credentials(self.capability)
        kwargs.setdefault("model", self.settings.vivo_llm_stream_model)
        payload = self._chat_payload(messages, stream=True, **kwargs)
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        usage: dict[str, Any] = {}
        try:
            lines = self.http_client.post_stream_json(
                join_url(self.settings.vivo_llm_base_url, "/chat/completions"),
                capability=self.capability,
                request_id=request_id,
                request_id_param="request_id",
                payload=payload,
            )
            for line in lines:
                chunk = line[5:].strip() if line.startswith("data:") else line
                if chunk == "[DONE]":
                    break
                if not chunk:
                    continue
                try:
                    data = json.loads(chunk)
                except ValueError:
                    continue
                if data.get("usage"):
                    usage = data["usage"]
                choices = data.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                if delta.get("content"):
                    content_parts.append(delta["content"])
                if delta.get("reasoning_content"):
                    reasoning_parts.append(delta["reasoning_content"])
            return LlmMessageResult(
                content="".join(content_parts),
                reasoning_content="".join(reasoning_parts) or None,
                provider=self.provider,
                model=payload["model"],
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
                provider_request_id=request_id,
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.UNKNOWN_ERROR,
                "LLM stream provider call failed.",
                request_id=request_id,
                raw_error=str(exc),
            ) from exc

    def understand_image(self, image: str, prompt: str, **kwargs: Any) -> ImageUnderstandingResult:
        request_id = str(uuid.uuid4())
        if not prompt.strip():
            raise provider_error(
                self.provider,
                "image_understanding",
                ProviderErrorType.INVALID_REQUEST,
                "Image understanding prompt cannot be empty.",
                request_id=request_id,
            )
        selected_model = kwargs.pop("model", self.settings.vivo_image_understanding_model)
        if selected_model not in self.image_capable_models:
            raise provider_error(
                self.provider,
                "image_understanding",
                ProviderErrorType.INVALID_REQUEST,
                "Configured image understanding model does not support image input.",
                request_id=request_id,
                raw_error={"model": selected_model},
            )
        image_url = self._image_to_url(image, request_id=request_id)
        message = LlmMessage(
            role="user",
            content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        )
        llm_result = self.chat(
            [message],
            model=selected_model,
            **kwargs,
        )
        return ImageUnderstandingResult(
            description=llm_result.content,
            provider=llm_result.provider,
            model=llm_result.model,
            input_tokens=llm_result.input_tokens,
            output_tokens=llm_result.output_tokens,
            total_tokens=llm_result.total_tokens,
        )

    def _chat_payload(self, messages: list[LlmMessage], *, stream: bool, **kwargs: Any) -> dict[str, Any]:
        model = kwargs.pop("model", None) or self.settings.vivo_llm_model
        payload: dict[str, Any] = {
            "model": model,
            "messages": [self._message_to_payload(message) for message in messages],
            "stream": stream,
        }
        for key in (
            "temperature",
            "max_tokens",
            "max_completion_tokens",
            "reasoning_effort",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "tools",
            "thinking",
            "enable_thinking",
            "stream_options",
        ):
            if key in kwargs and kwargs[key] is not None:
                payload[key] = kwargs[key]
        if stream:
            payload.setdefault("stream_options", {"include_usage": True})
        return payload

    def _validate_messages(self, messages: list[LlmMessage], request_id: str) -> None:
        if not messages:
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.INVALID_REQUEST,
                "LLM messages cannot be empty.",
                request_id=request_id,
            )
        for message in messages:
            if message.role not in {"system", "user", "assistant"}:
                raise provider_error(
                    self.provider,
                    self.capability,
                    ProviderErrorType.INVALID_REQUEST,
                    "LLM message role is invalid.",
                    request_id=request_id,
                )
            if isinstance(message.content, str) and not message.content.strip():
                raise provider_error(
                    self.provider,
                    self.capability,
                    ProviderErrorType.INVALID_REQUEST,
                    "LLM message content cannot be empty.",
                    request_id=request_id,
                )

    @staticmethod
    def _message_to_payload(message: LlmMessage) -> dict[str, Any]:
        return {"role": message.role, "content": message.content}

    def _parse_message_result(self, data: Any, *, request_id: str, model: str) -> LlmMessageResult:
        if isinstance(data, dict) and isinstance(data.get("error"), dict):
            message = str(data["error"].get("message", "Provider returned an error."))
            error_type = (
                ProviderErrorType.INVALID_REQUEST
                if "do not support" in message.lower() or "invalid" in message.lower()
                else ProviderErrorType.UNKNOWN_ERROR
            )
            raise provider_error(
                self.provider,
                self.capability,
                error_type,
                "LLM provider returned an error.",
                request_id=request_id,
                raw_error=data,
            )
        try:
            choices = data["choices"]
            message = choices[0]["message"]
            usage = data.get("usage") or {}
            content = message.get("content") or ""
            return LlmMessageResult(
                content=content,
                reasoning_content=message.get("reasoning_content"),
                provider=self.provider,
                model=model,
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
                provider_request_id=request_id,
            )
        except (KeyError, IndexError, TypeError) as exc:
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.PARSE_FAILED,
                "LLM provider response shape is invalid.",
                request_id=request_id,
                raw_error=data,
            ) from exc

    def _image_to_url(self, image: str, *, request_id: str) -> str:
        if image.startswith(("http://", "https://", "data:image/")):
            return image
        path = Path(image)
        if not path.exists():
            raise provider_error(
                self.provider,
                "image_understanding",
                ProviderErrorType.INVALID_REQUEST,
                "Image file does not exist.",
                request_id=request_id,
                raw_error=str(path),
            )
        suffix = path.suffix.lower().lstrip(".")
        if suffix == "jpg":
            suffix = "jpeg"
        if suffix not in {"jpeg", "png", "webp"}:
            raise provider_error(
                self.provider,
                "image_understanding",
                ProviderErrorType.UNSUPPORTED_FORMAT,
                "Image format is not supported.",
                request_id=request_id,
                raw_error=suffix,
            )
        mime_type = mimetypes.types_map.get(path.suffix.lower(), f"image/{suffix}")
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"
