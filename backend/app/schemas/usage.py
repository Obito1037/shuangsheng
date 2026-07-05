from __future__ import annotations

from pydantic import BaseModel


class UsageSummary(BaseModel):
    total_tokens: int
    records: int

