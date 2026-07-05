from __future__ import annotations

from pydantic import BaseModel


class RagIndexTextRequest(BaseModel):
    knowledge_base_id: str
    title: str
    text: str


class RagIndexDocumentRequest(BaseModel):
    knowledge_base_id: str
    document_id: str


class RagAskRequest(BaseModel):
    knowledge_base_id: str
    question: str
    top_k: int = 5


class RagReferenceRead(BaseModel):
    chunk_id: str
    source: str
    text: str
    score: float | None = None
    rank: int


class RagAnswerResponse(BaseModel):
    run_id: str
    answer: str
    references: list[RagReferenceRead]
    rewritten_query: str

