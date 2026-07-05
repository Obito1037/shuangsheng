from __future__ import annotations

import json
import math
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.errors import ProviderError, ProviderErrorType
from app.db.models.document_chunk import DocumentChunk
from app.db.repositories.document_repository import DocumentRepository
from app.db.repositories.knowledge_repository import KnowledgeRepository
from app.integrations.registry import ProviderRegistry, create_provider_registry
from app.schemas.llm import LlmMessage
from app.schemas.rag import RagAnswerResponse, RagReferenceRead
from app.services.chunk_service import ChunkService
from app.services.permission_service import PermissionService
from app.services.usage_service import UsageService


@dataclass(frozen=True, slots=True)
class VectorMatch:
    chunk: DocumentChunk
    score: float


class MemoryVectorStore:
    def search(self, query_vector: list[float], chunks: list[DocumentChunk], *, top_k: int) -> list[VectorMatch]:
        matches: list[VectorMatch] = []
        for chunk in chunks:
            if not chunk.embedding_json:
                continue
            vector = [float(value) for value in json.loads(chunk.embedding_json)]
            matches.append(VectorMatch(chunk=chunk, score=self._cosine(query_vector, vector)))
        return sorted(matches, key=lambda item: item.score, reverse=True)[:top_k]

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        dot = sum(a * b for a, b in zip(left, right, strict=True))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot / (left_norm * right_norm)


class RagPromptBuilder:
    def build(self, *, question: str, references: list[RagReferenceRead]) -> str:
        context = "\n\n".join(f"[{ref.rank}] {ref.source}\n{ref.text}" for ref in references)
        return (
            "Answer the question using only the references below. "
            "If the references are insufficient, say so clearly.\n\n"
            f"References:\n{context}\n\nQuestion: {question}"
        )


class RagService:
    def __init__(
        self,
        db: Session,
        provider_registry: ProviderRegistry | None = None,
        vector_store: MemoryVectorStore | None = None,
    ) -> None:
        self.db = db
        self.registry = provider_registry or create_provider_registry()
        self.documents = DocumentRepository(db)
        self.knowledge = KnowledgeRepository(db)
        self.permissions = PermissionService(db)
        self.chunks = ChunkService()
        self.vector_store = vector_store or MemoryVectorStore()
        self.prompt_builder = RagPromptBuilder()
        self.usage = UsageService(db)

    def index_text(self, *, user_id: str, knowledge_base_id: str, title: str, text: str) -> dict[str, int | str]:
        self.permissions.require_knowledge_base(user_id=user_id, knowledge_base_id=knowledge_base_id)
        document = self.documents.create(user_id=user_id, title=title, raw_text=text)
        return self._index_document_text(
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            document_id=document.id,
            title=title,
            text=text,
        )

    def index_document(self, *, user_id: str, knowledge_base_id: str, document_id: str) -> dict[str, int | str]:
        self.permissions.require_knowledge_base(user_id=user_id, knowledge_base_id=knowledge_base_id)
        document = self.permissions.require_document(user_id=user_id, document_id=document_id)
        return self._index_document_text(
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            document_id=document.id,
            title=document.title,
            text=document.raw_text,
        )

    def ask(self, *, user_id: str, knowledge_base_id: str, question: str, top_k: int = 5) -> RagAnswerResponse:
        self.permissions.require_knowledge_base(user_id=user_id, knowledge_base_id=knowledge_base_id)
        rewritten_query = self._rewrite_query(question)
        chunks = self.documents.list_chunks(user_id=user_id, knowledge_base_id=knowledge_base_id)
        query_vector = self.registry.get_embedding_provider().embed(rewritten_query).vectors[0]
        initial_matches = self.vector_store.search(query_vector, chunks, top_k=max(top_k * 2, top_k))
        references = self._rerank_matches(rewritten_query=rewritten_query, matches=initial_matches, top_k=top_k)
        prompt = self.prompt_builder.build(question=question, references=references)
        answer_result = self.registry.get_llm_provider().chat([LlmMessage(role="user", content=prompt)])
        run = self.knowledge.create_rag_run(
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            question=question,
            rewritten_query=rewritten_query,
            answer=answer_result.content,
            provider=answer_result.provider,
            model=answer_result.model,
            total_tokens=answer_result.total_tokens,
        )
        for reference in references:
            self.knowledge.create_rag_reference(
                rag_run_id=run.id,
                chunk_id=reference.chunk_id,
                source=reference.source,
                text=reference.text,
                rank=reference.rank,
                score=reference.score,
            )
        self.usage.record(
            user_id=user_id,
            capability="rag_ask",
            provider=answer_result.provider,
            model=answer_result.model,
            total_tokens=answer_result.total_tokens,
        )
        return RagAnswerResponse(run_id=run.id, answer=answer_result.content, references=references, rewritten_query=rewritten_query)

    def _index_document_text(
        self,
        *,
        user_id: str,
        knowledge_base_id: str,
        document_id: str,
        title: str,
        text: str,
    ) -> dict[str, int | str]:
        chunks = self.chunks.split_text(text)
        if not chunks:
            raise ValueError("Document has no indexable text")
        embeddings = self.registry.get_embedding_provider().embed(chunks).vectors
        for index, (chunk, vector) in enumerate(zip(chunks, embeddings, strict=True)):
            self.documents.create_chunk(
                user_id=user_id,
                document_id=document_id,
                knowledge_base_id=knowledge_base_id,
                chunk_index=index,
                source=title,
                text=chunk,
                embedding_json=json.dumps(vector),
            )
        return {"document_id": document_id, "chunks": len(chunks)}

    def _rerank_matches(self, *, rewritten_query: str, matches: list[VectorMatch], top_k: int) -> list[RagReferenceRead]:
        if not matches:
            return []
        sentences = [match.chunk.text for match in matches]
        scores = self.registry.get_similarity_provider().rerank(rewritten_query, sentences).scores
        reranked = sorted(zip(matches, scores, strict=True), key=lambda item: item[1], reverse=True)[:top_k]
        return [
            RagReferenceRead(
                chunk_id=match.chunk.id,
                source=match.chunk.source,
                text=match.chunk.text,
                score=float(score),
                rank=index + 1,
            )
            for index, (match, score) in enumerate(reranked)
        ]

    def _rewrite_query(self, question: str) -> str:
        try:
            rewritten = self.registry.get_query_rewrite_provider().rewrite(question)
        except ProviderError as exc:
            if exc.error_type == ProviderErrorType.PROVIDER_UNAVAILABLE:
                return question
            raise
        return rewritten.rewritten_queries[0] if rewritten.rewritten_queries else question
