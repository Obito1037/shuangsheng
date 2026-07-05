from __future__ import annotations

AVATAR_DATA_URL_MAX_LENGTH = 300_000


def normalize_avatar_data_url(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return ""
    if len(cleaned) > AVATAR_DATA_URL_MAX_LENGTH:
        raise ValueError("avatar_data_url_too_large")
    header, separator, _payload = cleaned.partition(",")
    if not separator or not header.startswith("data:image/") or ";base64" not in header:
        raise ValueError("avatar_data_url_must_be_base64_image")
    return cleaned
