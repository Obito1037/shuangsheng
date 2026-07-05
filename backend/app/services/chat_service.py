from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from app.core.errors import ProviderError
from app.db.models.conversation import Conversation
from app.db.models.learning_twin import LearningTwin
from app.db.repositories.conversation_repository import ConversationRepository
from app.db.repositories.learning_twin_repository import LearningTwinRepository
from app.db.repositories.message_repository import MessageRepository
from app.integrations.registry import ProviderRegistry, create_provider_registry
from app.schemas.chat import ChatMessageResponse
from app.schemas.llm import LlmMessage, LlmMessageResult
from app.services.permission_service import PermissionService
from app.services.retrieval_service import RetrievalService
from app.services.usage_service import UsageService

logger = logging.getLogger(__name__)
FALLBACK_PROVIDER = "echolearn"
FALLBACK_MODEL = "learning-twin-fallback"


class ChatService:
    def __init__(self, db: Session, provider_registry: ProviderRegistry | None = None) -> None:
        self.db = db
        self.registry = provider_registry or create_provider_registry()
        self.conversations = ConversationRepository(db)
        self.messages = MessageRepository(db)
        self.twins = LearningTwinRepository(db)
        self.permissions = PermissionService(db)
        self.retrieval = RetrievalService(db, self.registry)
        self.usage = UsageService(db)

    def send_message(
        self,
        *,
        user_id: str,
        message: str,
        conversation_id: str | None = None,
        twin_id: str | None = None,
        mode: str = "twin",
    ) -> ChatMessageResponse:
        twin = self._load_twin(user_id=user_id, twin_id=twin_id) if mode == "twin" else None
        effective_twin_id = twin.id if twin else None
        conversation = self._resolve_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            title=message[:80] or "New conversation",
            twin_id=effective_twin_id,
        )
        user_message = self.messages.create(
            user_id=user_id,
            twin_id=effective_twin_id,
            conversation_id=conversation.id,
            role="user",
            content=message,
        )
        llm_messages = self._conversation_messages(
            user_id=user_id,
            conversation_id=conversation.id,
            question=message,
            twin=twin,
            mode=mode,
        )
        try:
            result = self.registry.get_llm_provider().chat(llm_messages)
        except ProviderError as exc:
            logger.warning("LLM provider failed; using fallback: %s", exc.to_safe_dict())
            result = self._fallback_result(message, twin=twin, mode=mode)
        except Exception:
            logger.exception("Unexpected LLM provider failure; using fallback")
            result = self._fallback_result(message, twin=twin, mode=mode)
        assistant_message = self.messages.create(
            user_id=user_id,
            twin_id=effective_twin_id,
            conversation_id=conversation.id,
            role="assistant",
            content=result.content,
            provider=result.provider,
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            total_tokens=result.total_tokens,
        )
        self.usage.record(
            user_id=user_id,
            capability="twin_rag_chat" if twin else "normal_chat",
            provider=result.provider,
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            total_tokens=result.total_tokens,
        )
        return ChatMessageResponse(
            conversation_id=conversation.id,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
            answer=result.content,
            provider=result.provider,
            model=result.model,
        )

    def stream_message(
        self,
        *,
        user_id: str,
        message: str,
        conversation_id: str | None = None,
        twin_id: str | None = None,
        mode: str = "twin",
    ) -> ChatMessageResponse:
        return self.send_message(user_id=user_id, message=message, conversation_id=conversation_id, twin_id=twin_id, mode=mode)

    def _resolve_conversation(self, *, user_id: str, conversation_id: str | None, title: str, twin_id: str | None) -> Conversation:
        if not conversation_id:
            return self.conversations.create(user_id=user_id, title=title, twin_id=twin_id)
        conversation = self.permissions.require_conversation(user_id=user_id, conversation_id=conversation_id)
        if twin_id and conversation.twin_id is None:
            conversation.twin_id = twin_id
            return self.conversations.save(conversation)
        return conversation

    def _load_twin(self, *, user_id: str, twin_id: str | None) -> LearningTwin | None:
        if not twin_id:
            return None
        return self.twins.get(user_id=user_id, twin_id=twin_id)

    def _conversation_messages(
        self,
        *,
        user_id: str,
        conversation_id: str,
        question: str,
        twin: LearningTwin | None,
        mode: str,
    ) -> list[LlmMessage]:
        history = self.messages.list_for_conversation(user_id=user_id, conversation_id=conversation_id)
        llm_messages = [
            LlmMessage(role=m.role if m.role in {"user", "assistant", "system"} else "user", content=m.content)
            for m in history[-10:]
        ]
        system = self._system_message(
            twin=twin,
            mode=mode,
            local_context=self._local_context(user_id=user_id, twin_id=twin.id if twin else None, question=question),
        )
        return [system, *llm_messages]

    def _system_message(self, *, twin: LearningTwin | None, mode: str, local_context: str = "") -> LlmMessage:
        if mode != "twin" or twin is None:
            return LlmMessage(
                role="system",
                content=(
                    "You are the normal AI mode of Shuangsheng. Answer directly with the general model. "
                    "Do not use learning twin memory, uploaded materials, or RAG context in this mode."
                ),
            )
        memories = self._parse_memories(twin.memories_json)
        memory_text = "; ".join(memories[:6]) if memories else "No stable memory yet. Use only this twin profile and this twin's trained materials."
        context_rule = (
            "\nRetrieved RAG chunks for this twin:\n" + local_context
            if local_context
            else "\nNo relevant RAG chunks were retrieved for this twin. State that evidence is insufficient and suggest more training data."
        )
        return LlmMessage(
            role="system",
            content=(
                "You are a growing AI learning twin. Use only the selected twin profile, this twin's trained RAG materials, and the current conversation.\n"
                f"Twin name: {twin.name}\nSubject: {twin.subject}\nGoal: {twin.goal}\nStage: {twin.stage}\nStatus: {twin.status} ({twin.sync_percent}%)\nMemory: {memory_text}\n{context_rule}\n\n"
                "Answer format: identify the task type; cite chunk numbers when chunks exist; state what this twin knows and lacks; give the next training action."
            ),
        )

    def _local_context(self, *, user_id: str, twin_id: str | None, question: str, limit: int = 4) -> str:
        if not twin_id:
            return ""
        return self.retrieval.local_context(user_id=user_id, twin_id=twin_id, question=question, limit=limit)

    def _fallback_result(self, message: str, *, twin: LearningTwin | None, mode: str) -> LlmMessageResult:
        if mode != "twin" or twin is None:
            content = f"Normal AI mode is active. This answer does not use twin memory or RAG.\n\nQuestion: {message}"
        else:
            content = (
                f"Twin mode is active for {twin.name}, but the model or retrieval provider is currently unavailable.\n\n"
                f"Subject: {twin.subject}\nGoal: {twin.goal}\nStatus: {twin.status}\n\n"
                "Upload and parse materials for this twin, then ask again in twin mode to use its RAG context."
            )
        return LlmMessageResult(
            content=content,
            reasoning_content=None,
            provider=FALLBACK_PROVIDER,
            model=FALLBACK_MODEL,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            provider_request_id="local-fallback",
        )

    def _parse_memories(self, value: str) -> list[str]:
        try:
            loaded = json.loads(value or "[]")
        except json.JSONDecodeError:
            return []
        return [str(item) for item in loaded if str(item).strip()]
