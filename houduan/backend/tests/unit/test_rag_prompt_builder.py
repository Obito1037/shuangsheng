from __future__ import annotations

from app.schemas.rag import RagReferenceRead
from app.services.rag_service import RagPromptBuilder


def test_rag_prompt_builder_includes_question_and_references() -> None:
    prompt = RagPromptBuilder().build(
        question="什么是 EchoLearn?",
        references=[RagReferenceRead(chunk_id="c1", source="doc", text="EchoLearn 是学习助手。", rank=1, score=0.9)],
    )

    assert "EchoLearn 是学习助手" in prompt
    assert "什么是 EchoLearn" in prompt

