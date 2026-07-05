from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.errors import ProviderError
from app.db.repositories.conversation_repository import ConversationRepository
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
        self.permissions = PermissionService(db)
        self.usage = UsageService(db)

    def send_message(self, *, user_id: str, message: str, conversation_id: str | None = None) -> ChatMessageResponse:
        conversation = (
            self.permissions.require_conversation(user_id=user_id, conversation_id=conversation_id)
            if conversation_id
            else self.conversations.create(user_id=user_id, title=message[:80] or "New conversation")
        )
        user_message = self.messages.create(user_id=user_id, conversation_id=conversation.id, role="user", content=message)
        llm_messages = self._conversation_messages(user_id=user_id, conversation_id=conversation.id)
        try:
            result = self.registry.get_llm_provider().chat(llm_messages)
        except ProviderError as exc:
            logger.warning("LLM provider failed; using learning twin fallback: %s", exc.to_safe_dict())
            result = self._fallback_result(message)
        except Exception:
            logger.exception("Unexpected LLM provider failure; using learning twin fallback")
            result = self._fallback_result(message)
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

    def stream_message(self, *, user_id: str, message: str, conversation_id: str | None = None) -> ChatMessageResponse:
        conversation = (
            self.permissions.require_conversation(user_id=user_id, conversation_id=conversation_id)
            if conversation_id
            else self.conversations.create(user_id=user_id, title=message[:80] or "New conversation")
        )
        user_message = self.messages.create(user_id=user_id, conversation_id=conversation.id, role="user", content=message)
        try:
            result = self.registry.get_llm_provider().stream_chat(
                [self._system_message(), LlmMessage(role="user", content=message)]
            )
        except ProviderError as exc:
            logger.warning("Streaming LLM provider failed; using learning twin fallback: %s", exc.to_safe_dict())
            result = self._fallback_result(message)
        except Exception:
            logger.exception("Unexpected streaming LLM provider failure; using learning twin fallback")
            result = self._fallback_result(message)
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

    def _conversation_messages(self, *, user_id: str, conversation_id: str) -> list[LlmMessage]:
        history = self.messages.list_for_conversation(user_id=user_id, conversation_id=conversation_id)
        llm_messages = [
            LlmMessage(role=m.role if m.role in {"user", "assistant", "system"} else "user", content=m.content)
            for m in history[-10:]
        ]
        return [self._system_message(), *llm_messages]

    def _system_message(self) -> LlmMessage:
        return LlmMessage(
            role="system",
            content=(
                "你是 EchoLearn 的 AI 学习分身执行器。回答时不要只给答案，要先说明你如何结合用户资料、"
                "长期记忆、错因模式和路线模拟来判断下一步；再给出可执行的学习动作。优先使用中文，"
                "保持简洁，并在合适时提供黑板讲解、变式训练、PDF/Word 或视频讲解等产出选项。"
            ),
        )

    def _fallback_result(self, message: str) -> LlmMessageResult:
        lowered_message = message.lower()
        if any(keyword in lowered_message for keyword in ("sql", "数据库", "group", "having", "范式")):
            focus = "数据库考试学习分身会先补 SQL 聚合与范式依赖，再用变式题验证是否真正掌握。"
        elif any(keyword in lowered_message for keyword in ("英语", "口语", "听力", "pronunciation")):
            focus = "英语分身会先抽取发音、表达和复述卡点，再安排跟读、复述和间隔复测。"
        else:
            focus = "学习分身会先从资料库和历史对话中检索证据，再判断当前最值得投入的补漏任务。"
        content = (
            f"{focus}\n\n"
            "我已进入分身工作流：\n"
            "1. 检索 RAG 资料、长期记忆和最近错因；\n"
            "2. 标记可能只是短暂记住、还没稳定掌握的知识点；\n"
            "3. 并发比较概念补课、变式训练和输出复述三条路线；\n"
            "4. 当前建议先走“概念澄清 -> 2 道变式题 -> 黑板复述”的路径。\n\n"
            "你可以继续发题目或资料，我会把下一步拆成可执行任务，并可生成黑板讲解、视频脚本或 PDF/Word 总结。"
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
