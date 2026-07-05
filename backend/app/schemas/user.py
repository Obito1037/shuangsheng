from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.avatar import AVATAR_DATA_URL_MAX_LENGTH, normalize_avatar_data_url


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    phone: str | None = None
    display_name: str
    avatar_data_url: str = ""
    created_at: datetime


class UserUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    avatar_data_url: str | None = Field(default=None, max_length=AVATAR_DATA_URL_MAX_LENGTH)

    @field_validator("display_name")
    @classmethod
    def clean_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("display_name_required")
        return cleaned

    @field_validator("avatar_data_url")
    @classmethod
    def clean_avatar_data_url(cls, value: str | None) -> str | None:
        return normalize_avatar_data_url(value)
