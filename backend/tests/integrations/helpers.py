from __future__ import annotations

from typing import Any

import pytest

from app.core.config import VivoSettings, has_real_vivo_credentials, load_settings


class FakeHttpClient:
    def __init__(self, *, json_response: Any = None, form_response: Any = None, stream_lines: list[str] | None = None) -> None:
        self.json_response = json_response
        self.form_response = form_response
        self.stream_lines = stream_lines or []
        self.calls: list[dict[str, Any]] = []

    def post_json(self, url: str, **kwargs: Any) -> Any:
        self.calls.append({"method": "post_json", "url": url, **kwargs})
        return self.json_response

    def post_form(self, url: str, **kwargs: Any) -> Any:
        self.calls.append({"method": "post_form", "url": url, **kwargs})
        return self.form_response

    def post_stream_json(self, url: str, **kwargs: Any):
        self.calls.append({"method": "post_stream_json", "url": url, **kwargs})
        yield from self.stream_lines


def fake_settings() -> VivoSettings:
    return VivoSettings(vivo_app_id="test_app_id", vivo_app_key="test_app_key")


def missing_settings() -> VivoSettings:
    return VivoSettings(vivo_app_id=None, vivo_app_key=None)


def real_settings_or_skip() -> VivoSettings:
    settings = load_settings()
    if not has_real_vivo_credentials(settings):
        pytest.skip("missing real VIVO_APP_ID/VIVO_APP_KEY; real provider API test skipped")
    return settings

