from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from app.schemas.llm import LlmMessage, LlmMessageResult, LlmStreamChunk
from app.schemas.vision import ImageUnderstandingResult


class LlmProvider(ABC):
    @abstractmethod
    def chat(self, messages: list[LlmMessage], **kwargs) -> LlmMessageResult:
        raise NotImplementedError

    @abstractmethod
    def stream_chat(self, messages: list[LlmMessage], **kwargs) -> LlmMessageResult:
        raise NotImplementedError

    def stream_chat_chunks(self, messages: list[LlmMessage], **kwargs) -> Iterator[LlmStreamChunk]:
        """Yield provider stream chunks.

        Providers that do not expose incremental tokens can keep implementing only
        stream_chat; callers still receive an honest one-chunk stream.
        """
        result = self.stream_chat(messages, **kwargs)
        if result.content:
            yield LlmStreamChunk(
                content_delta=result.content,
                reasoning_delta=result.reasoning_content or "",
                provider=result.provider,
                model=result.model,
                provider_request_id=result.provider_request_id,
            )
        yield LlmStreamChunk(
            provider=result.provider,
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            total_tokens=result.total_tokens,
            provider_request_id=result.provider_request_id,
            done=True,
        )

    @abstractmethod
    def understand_image(self, image: str, prompt: str, **kwargs) -> ImageUnderstandingResult:
        raise NotImplementedError
