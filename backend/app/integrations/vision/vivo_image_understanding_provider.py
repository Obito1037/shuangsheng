from __future__ import annotations

from typing import Any

from app.core.config import VivoSettings
from app.integrations.llm.vivo_llm_provider import VivoLlmProvider
from app.integrations.vision.base import ImageUnderstandingProvider
from app.schemas.vision import ImageUnderstandingResult


class VivoImageUnderstandingProvider(ImageUnderstandingProvider):
    def __init__(
        self,
        *,
        settings: VivoSettings | None = None,
        http_client: Any | None = None,
    ) -> None:
        self.llm_provider = VivoLlmProvider(settings=settings, http_client=http_client)

    def understand(self, image: str, prompt: str) -> ImageUnderstandingResult:
        return self.llm_provider.understand_image(image, prompt)
