from __future__ import annotations

from pathlib import Path

import pytest

from app.core.errors import ProviderError, ProviderErrorType
from app.integrations.vision.vivo_ocr_provider import VivoOcrProvider
from app.schemas.vision import OcrResult
from tests.integrations.helpers import FakeHttpClient, fake_settings, missing_settings, real_settings_or_skip

ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"


def test_ocr_input_validation_rejects_missing_file() -> None:
    provider = VivoOcrProvider(settings=fake_settings(), http_client=FakeHttpClient())
    with pytest.raises(ProviderError) as exc:
        provider.recognize(str(ASSET_DIR / "missing.jpg"))
    assert exc.value.error_type == ProviderErrorType.INVALID_REQUEST


def test_ocr_missing_config_raises_missing_config() -> None:
    provider = VivoOcrProvider(settings=missing_settings(), http_client=FakeHttpClient())
    with pytest.raises(ProviderError) as exc:
        provider.recognize(str(ASSET_DIR / "ocr_test.jpg"))
    assert exc.value.error_type == ProviderErrorType.MISSING_CONFIG


def test_ocr_return_model_fields() -> None:
    fake_client = FakeHttpClient(
        form_response={
            "error_code": 0,
            "result": {
                "angle": 0,
                "OCR": [
                    {
                        "words": "EchoLearn",
                        "location": {
                            "top_left": {"x": 1, "y": 2},
                            "top_right": {"x": 10, "y": 2},
                            "down_left": {"x": 1, "y": 9},
                            "down_right": {"x": 10, "y": 9},
                        },
                    }
                ],
            },
        }
    )
    provider = VivoOcrProvider(settings=fake_settings(), http_client=fake_client)
    result = provider.recognize(str(ASSET_DIR / "ocr_test.jpg"))
    assert isinstance(result, OcrResult)
    assert result.full_text == "EchoLearn"
    assert result.blocks[0].bounding_box is not None
    assert result.provider == "vivo"


def test_ocr_error_mapping_for_provider_failure() -> None:
    provider = VivoOcrProvider(
        settings=fake_settings(),
        http_client=FakeHttpClient(form_response={"error_code": 1, "error_msg": "ocr fail"}),
    )
    with pytest.raises(ProviderError) as exc:
        provider.recognize(str(ASSET_DIR / "ocr_test.jpg"))
    assert exc.value.error_type == ProviderErrorType.UNKNOWN_ERROR


def test_ocr_real_api() -> None:
    settings = real_settings_or_skip()
    provider = VivoOcrProvider(settings=settings)
    result = provider.recognize(str(ASSET_DIR / "ocr_test.jpg"))
    assert result.provider == "vivo"
    assert isinstance(result.blocks, list)

