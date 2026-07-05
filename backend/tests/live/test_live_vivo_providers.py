from __future__ import annotations

from pathlib import Path

import pytest

from app.core.errors import ProviderError, ProviderErrorType
from app.integrations.embedding.vivo_embedding_provider import VivoEmbeddingProvider
from app.integrations.llm.vivo_llm_provider import VivoLlmProvider
from app.integrations.query_rewrite.vivo_query_rewrite_provider import VivoQueryRewriteProvider
from app.integrations.similarity.vivo_similarity_provider import VivoSimilarityProvider
from app.integrations.vision.vivo_ocr_provider import VivoOcrProvider
from app.schemas.llm import LlmMessage
from app.schemas.query_rewrite import QueryRewriteTurn
from tests.integrations.helpers import real_settings_or_skip

ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"


def test_live_llm_sync_stream_and_image_understanding() -> None:
    settings = real_settings_or_skip()
    provider = VivoLlmProvider(settings=settings)

    sync_result = provider.chat([LlmMessage(role="user", content="用一句话介绍 EchoLearn。")], max_tokens=80)
    assert sync_result.content

    stream_result = provider.stream_chat([LlmMessage(role="user", content="用四个字回复：学习助手")], max_tokens=40)
    assert stream_result.content

    image_result = provider.understand_image(
        str(ASSET_DIR / "image_understanding_test.jpg"),
        "用一句话描述图片内容。",
    )
    assert image_result.description


def test_live_ocr_embedding_similarity() -> None:
    settings = real_settings_or_skip()

    ocr_result = VivoOcrProvider(settings=settings).recognize(str(ASSET_DIR / "ocr_test.jpg"))
    assert ocr_result.provider == "vivo"

    embedding_result = VivoEmbeddingProvider(settings=settings).embed(["豫章故郡，洪都新府", "星分翼轸，地接衡庐"])
    assert len(embedding_result.vectors) == 2

    similarity_result = VivoSimilarityProvider(settings=settings).rerank(
        "科技品牌发展",
        ["自动追焦相关报表", "太古汇内云集逾180家知名品牌"],
    )
    assert len(similarity_result.scores) == 2


def test_live_query_rewrite_reports_provider_unavailable_without_fake_success() -> None:
    settings = real_settings_or_skip()
    provider = VivoQueryRewriteProvider(settings=settings)

    try:
        result = provider.rewrite(
            "第一部里有他吗",
            [QueryRewriteTurn(question="战狼2是谁主演的", answer="《战狼2》由吴京主演。")],
        )
    except ProviderError as exc:
        if exc.error_type == ProviderErrorType.PROVIDER_UNAVAILABLE:
            pytest.skip(f"query rewrite provider unavailable; RAG may continue with original query: {exc.raw_error}")
        raise

    assert result.provider == "vivo"
    assert isinstance(result.rewritten_queries, list)

