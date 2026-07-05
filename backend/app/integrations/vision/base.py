from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.vision import ImageUnderstandingResult, OcrResult


class OcrProvider(ABC):
    @abstractmethod
    def recognize(self, image_path: str, *, pos: int = 2) -> OcrResult:
        raise NotImplementedError


class ImageUnderstandingProvider(ABC):
    @abstractmethod
    def understand(self, image: str, prompt: str) -> ImageUnderstandingResult:
        raise NotImplementedError

