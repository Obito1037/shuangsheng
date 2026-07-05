from __future__ import annotations

from pydantic import BaseModel


class MemorySummary(BaseModel):
    documents: int
    chunks: int
    embedded: int
    knowledge_points: int
    edges: int
    dim: int
    projection: str  # "pca" | "pending"


class VectorPoint(BaseModel):
    id: str
    source: str
    doc_index: int
    text_preview: str
    x: float
    y: float
    embedded: bool


class KpNode(BaseModel):
    id: str
    name: str
    p_mastery: float
    attempt_count: int
    source: str
    chunk_count: int


class KpLink(BaseModel):
    source: str
    target: str
    relation: str


class DocLegend(BaseModel):
    index: int
    title: str
    chunks: int


class MemoryMapResponse(BaseModel):
    twin_id: str
    summary: MemorySummary
    documents: list[DocLegend]
    vectors: list[VectorPoint]
    knowledge_points: list[KpNode]
    edges: list[KpLink]
