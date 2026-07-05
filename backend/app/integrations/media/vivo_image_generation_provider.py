from __future__ import annotations

from app.integrations.media.base import MediaProvider


class VivoImageGenerationProvider(MediaProvider):
    def capability_name(self) -> str:
        return "image_generation"

