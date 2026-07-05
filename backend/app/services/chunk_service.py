from __future__ import annotations

import re


class ChunkService:
    def clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def split_text(self, text: str, *, chunk_size: int = 500, overlap: int = 80) -> list[str]:
        cleaned = self.clean_text(text)
        if not cleaned:
            return []
        chunks: list[str] = []
        start = 0
        while start < len(cleaned):
            end = min(len(cleaned), start + chunk_size)
            chunks.append(cleaned[start:end])
            if end == len(cleaned):
                break
            start = max(0, end - overlap)
        return chunks

