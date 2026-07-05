from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from app.core.errors import ProviderError
from app.db.models.learning_twin import LearningTwin
from app.db.repositories.conversation_repository import ConversationRepository
from app.db.repositories.learning_twin_repository import LearningTwinRepository
from app.db.repositories.message_repository import MessageRepository
from app.integrations.registry import ProviderRegistry, create_provider_registry
from app.schemas.chat import ChatMessageResponse
from app.schemas.llm import LlmMessage, LlmMessageResult
from app.services.permission_service import PermissionService
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
        conversation = (
            self.permissions.require_conversation(user_id=user_id, conversation_id=conversation_id)
            if conversation_id
            else self.conversations.create(user_id=user_id, title=message[:80] or "New conversation")
        )
        user_message = self.messages.create(user_id=user_id, conversation_id=conversation.id, role="user", content=message)
        llm_messages = self._conversation_messages(user_id=user_id, conversation_id=conversation.id, twin=twin, mode=mode)
        try:
            result = self.registry.get_llm_provider().chat(llm_messages)
        except ProviderError as exc:
            logger.warning("LLM provider failed; using learning twin fallback: %s", exc.to_safe_dict())
            result = self._fallback_result(message, twin=twin, mode=mode)
        except Exception:
            logger.exception("Unexpected LLM provider failure; using learning twin fallback")
            result = self._fallback_result(message, twin=twin, mode=mode)
        assistant_message = self.messages.create(
            user_id=user_id,
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
            capability="llm_chat",
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
        twin = self._load_twin(user_id=user_id, twin_id=twin_id) if mode == "twin" else None
        conversation = (
            self.permissions.require_conversation(user_id=user_id, conversation_id=conversation_id)
            if conversation_id
            else self.conversations.create(user_id=user_id, title=message[:80] or "New conversation")
        )
        user_message = self.messages.create(user_id=user_id, conversation_id=conversation.id, role="user", content=message)
        try:
            result = self.registry.get_llm_provider().stream_chat(
                [self._system_message(twin=twin, mode=mode), LlmMessage(role="user", content=message)]
            )
        except ProviderError as exc:
            logger.warning("Streaming LLM provider failed; using learning twin fallback: %s", exc.to_safe_dict())
            result = self._fallback_result(message, twin=twin, mode=mode)
        except Exception:
            logger.exception("Unexpected streaming LLM provider failure; using learning twin fallback")
            result = self._fallback_result(message, twin=twin, mode=mode)
        assistant_message = self.messages.create(
            user_id=user_id,
            conversation_id=conversation.id,
            role="assistant",
            content=result.content,
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

    def _load_twin(self, *, user_id: str, twin_id: str | None) -> LearningTwin | None:
        if not twin_id:
            return None
        return self.twins.get(user_id=user_id, twin_id=twin_id)

    def _conversation_messages(
        self,
        *,
        user_id: str,
        conversation_id: str,
        twin: LearningTwin | None,
        mode: str,
    ) -> list[LlmMessage]:
        history = self.messages.list_for_conversation(user_id=user_id, conversation_id=conversation_id)
        llm_messages = [
            LlmMessage(role=m.role if m.role in {"user", "assistant", "system"} else "user", content=m.content)
            for m in history[-10:]
        ]
        return [self._system_message(twin=twin, mode=mode), *llm_messages]

    def _system_message(self, *, twin: LearningTwin | None, mode: str) -> LlmMessage:
        if mode != "twin" or twin is None:
            return LlmMessage(
                role="system",
                content=(
                    "你是双生的基础 AI 模式。直接回答用户问题，不要声称已经使用分身记忆、上传资料或 RAG。"
                    "如果需要资料支撑，明确要求用户上传或切换到学习分身模式。"
                ),
            )
        memories = self._parse_memories(twin.memories_json)
        memory_text = "；".join(memories[:6]) if memories else "暂无稳定长期记忆，只能依据当前对话和用户目标回答"
        return LlmMessage(
            role="system",
            content=(
                "你是双生的 AI 学习分身执行器。必须基于分身画像回答，不能伪造不存在的资料引用或文件产物。\n"
                f"分身名称：{twin.name}\n"
                f"学习方向：{twin.subject}\n"
                f"学习目标：{twin.goal}\n"
                f"当前阶段：{twin.stage}\n"
                f"训练状态：{twin.status}（{twin.sync_percent}%）\n"
                f"记忆候选：{memory_text}\n\n"
                "回答结构：1）先判断当前问题属于概念、解题、复习、规划还是资料理解；"
                "2）给出直接帮助；3）给出下一步训练动作；4）需要时建议生成学习路径或黑板讲解。"
            ),
        )

    def _fallback_result(self, message: str, *, twin: LearningTwin | None, mode: str) -> LlmMessageResult:
        if mode != "twin" or twin is None:
            content = (
                "我会先按基础 AI 模式回答，不使用分身记忆。\n\n"
                f"你当前的问题是：{message}\n\n"
                "建议你补充题目、资料或目标；如果要生成个性化学习路径，请先创建并训练学习分身。"
            )
        else:
            content = (
                f"我已按“{twin.name}”的分身画像进入学习工作流。\n\n"
                f"方向：{twin.subject}\n目标：{twin.goal}\n训练状态：{twin.status}\n\n"
                "下一步建议：\n"
                "1. 先把当前问题拆成概念、条件和目标；\n"
                "2. 如果已有资料，优先用资料中的定义和例题校准理解；\n"
                "3. 完成 2 道变式题或一次口头复述；\n"
                "4. 进入“今日学习路线”页面生成本轮训练路径和交付清单。\n\n"
                "注意：当前回答没有伪造 PDF、Word 或视频文件，只给出可执行学习动作。"
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
