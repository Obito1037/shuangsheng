from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import load_settings
from app.core.errors import ProviderError, ProviderErrorType, map_http_error
from app.integrations.embedding.vivo_embedding_provider import VivoEmbeddingProvider
from app.integrations.similarity.vivo_similarity_provider import VivoSimilarityProvider
from app.integrations.vision.vivo_ocr_provider import VivoOcrProvider
from tests.integrations.helpers import FakeHttpClient, fake_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_static_structure_files_exist() -> None:
    expected = [
        "app/integrations/llm/base.py",
        "app/integrations/llm/vivo_llm_provider.py",
        "app/integrations/vision/vivo_ocr_provider.py",
        "app/integrations/embedding/vivo_embedding_provider.py",
        "app/integrations/similarity/vivo_similarity_provider.py",
        "app/integrations/query_rewrite/vivo_query_rewrite_provider.py",
        "app/core/config.py",
        "app/core/errors.py",
        "app/core/http_client.py",
    ]
    missing = [path for path in expected if not (BACKEND_ROOT / path).exists()]
    assert missing == []


def test_missing_config_error_type_without_real_env(tmp_path: Path) -> None:
    with pytest.raises(ProviderError) as exc:
        load_settings(
            env_file=tmp_path / "empty.env",
            include_os_environ=False,
            search_default_env_files=False,
            require_credentials=True,
        )
    assert exc.value.error_type == ProviderErrorType.MISSING_CONFIG


def test_unsupported_image_format_maps_to_unsupported_format(tmp_path: Path) -> None:
    image = tmp_path / "bad.gif"
    image.write_bytes(b"gif")
    provider = VivoOcrProvider(settings=fake_settings(), http_client=FakeHttpClient())
    with pytest.raises(ProviderError) as exc:
        provider.recognize(str(image))
    assert exc.value.error_type == ProviderErrorType.UNSUPPORTED_FORMAT


def test_empty_text_maps_to_invalid_request() -> None:
    provider = VivoEmbeddingProvider(settings=fake_settings(), http_client=FakeHttpClient())
    with pytest.raises(ProviderError) as exc:
        provider.embed("")
    assert exc.value.error_type == ProviderErrorType.INVALID_REQUEST


def test_scores_count_mismatch_maps_to_parse_failed() -> None:
    provider = VivoSimilarityProvider(
        settings=fake_settings(),
        http_client=FakeHttpClient(json_response={"data": [0.1]}),
    )
    with pytest.raises(ProviderError) as exc:
        provider.rerank("query", ["a", "b"])
    assert exc.value.error_type == ProviderErrorType.PARSE_FAILED


def test_http_401_maps_to_auth_failed() -> None:
    error = map_http_error(
        401,
        {"message": "invalid api-key"},
        provider="vivo",
        capability="llm",
        request_id="request-id",
    )
    assert error.error_type == ProviderErrorType.AUTH_FAILED
    assert error.to_safe_dict()["raw_error"] if "raw_error" in error.to_safe_dict() else True

