from __future__ import annotations

from app.integrations.media.base import MediaProvider


class VivoVideoGenerationProvider(MediaProvider):
    def capability_name(self) -> str:
        return "video_generation"

