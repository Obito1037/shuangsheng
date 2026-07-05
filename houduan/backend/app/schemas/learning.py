from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LearningRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    record_type: str
    content: str
    created_at: datetime

