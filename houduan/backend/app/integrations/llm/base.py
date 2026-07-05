from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.llm import LlmMessage, LlmMessageResult
from app.schemas.vision import ImageUnderstandingResult


class LlmProvider(ABC):
    @abstractmethod
    def chat(self, messages: list[LlmMessage], **kwargs) -> LlmMessageResult:
        raise NotImplementedError

    @abstractmethod
    def stream_chat(self, messages: list[LlmMessage], **kwargs) -> LlmMessageResult:
        raise NotImplementedError

    @abstractmethod
    def understand_image(self, image: str, prompt: str, **kwargs) -> ImageUnderstandingResult:
        raise NotImplementedError

