from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.core.errors import ProviderError
from app.integrations.registry import ProviderRegistry, create_provider_registry
from app.schemas.llm import LlmMessage
from app.schemas.speech import (
    SpeechSynthesisRequest,
    SpeechSynthesisResponse,
    SpokenEnglishAnalyzeRequest,
    SpokenEnglishIssueRead,
    SpokenEnglishResponse,
)
from app.schemas.twin_brain import AttemptCreateRequest
from app.services.file_service import FileService
from app.services.twin_brain.attempt_service import AttemptService

logger = logging.getLogger(__name__)

AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}


class SpokenFeedbackDraft(BaseModel):
    issues: list[SpokenEnglishIssueRead] = Field(default_factory=list, max_length=8)
    correction_plan: list[str] = Field(default_factory=list, max_length=6)


class SpokenEnglishService:
    def __init__(self, db: Session, *, registry: ProviderRegistry | None = None) -> None:
        self.db = db
        self.registry = registry or create_provider_registry()
        self.files = FileService(db)

    def analyze(self, *, user_id: str, file_id: str, payload: SpokenEnglishAnalyzeRequest | None = None) -> SpokenEnglishResponse:
        payload = payload or SpokenEnglishAnalyzeRequest()
        file = self.files.get(user_id=user_id, file_id=file_id)
        self._ensure_audio(file.original_name, file.content_type)

        transcript = (payload.transcript or "").strip()
        provider = "user-provided-transcript" if transcript else "pending"
        model: str | None = None
        if not transcript:
            transcript, provider, model = self._try_transcribe(user_id=user_id, storage_key=file.storage_key)
        if not transcript:
            return SpokenEnglishResponse(
                status="pending",
                evidence_mode="pending",
                transcript="",
                provider=provider,
                model=model,
                correction_plan=[
                    "音频已缓存，但本次没有生成可用转写；短语音 ASR 需要 16kHz、16-bit、单声道 PCM/WAV 输入。",
                    "可以使用 Android 端语音识别或手动输入 transcript，再重新提交进入口语画像。",
                ],
            )

        scores = self._score_transcript(transcript)
        feedback, feedback_model = self._feedback(transcript=transcript, prompt=payload.prompt)
        model = feedback_model or model
        attempt_id = None
        mastery_updates = []
        if payload.twin_id:
            attempt = AttemptService(self.db).submit(
                user_id=user_id,
                payload=AttemptCreateRequest(
                    twin_id=payload.twin_id,
                    stem=f"口语复述任务：{file.original_name}",
                    correct_answer="清晰、完整、自然地复述目标内容。",
                    solution="口语任务按 transcript 的 fluency/grammar/vocabulary 启发式评分写入画像；pronunciation 需要 ASR/声学模型后再补。",
                    kp_names=["英语口语表达"],
                    is_correct=self._average_score(scores) >= 70,
                    self_rating="good" if self._average_score(scores) >= 70 else "hard",
                    error_type=None if self._average_score(scores) >= 70 else "口语表达待强化",
                    answer_text=transcript,
                ),
            )
            attempt_id = attempt.id
            mastery_updates = attempt.mastery_updates
        return SpokenEnglishResponse(
            status="scored",
            evidence_mode="简化模式",
            transcript=transcript,
            pronunciation=None,
            fluency=scores["fluency"],
            grammar=scores["grammar"],
            vocabulary=scores["vocabulary"],
            issues=feedback.issues,
            correction_plan=feedback.correction_plan,
            provider=provider,
            model=model,
            attempt_id=attempt_id,
            mastery_updates=mastery_updates,
        )

    def synthesize(self, *, user_id: str, payload: SpeechSynthesisRequest) -> SpeechSynthesisResponse:
        provider_getter = getattr(self.registry, "get_tts_provider", None)
        if not callable(provider_getter):
            return self._tts_pending("tts_provider_missing")
        try:
            provider = provider_getter()
            result = provider.synthesize(payload.text, voice=payload.voice)
        except NotImplementedError:
            return self._tts_pending("tts_documented_only")
        except ProviderError as exc:
            logger.warning("TTS provider failed: %s", exc.to_safe_dict())
            return self._tts_pending(exc.error_type.value if hasattr(exc.error_type, "value") else str(exc.error_type))
        except Exception:
            logger.exception("Unexpected TTS failure")
            return self._tts_pending("tts_failed")

        storage_key = self.files.storage.save(user_id=user_id, filename="blackboard-tts.wav", content=result.audio)
        file = self.files.files.create(
            user_id=user_id,
            original_name="blackboard-tts.wav",
            storage_key=storage_key,
            content_type=result.content_type,
            size_bytes=len(result.audio),
        )
        return SpeechSynthesisResponse(
            status="ready",
            provider=result.provider,
            audio_file_id=file.id,
            message="TTS 音频已生成并写入本地文件表。",
        )

    def _try_transcribe(self, *, user_id: str, storage_key: str) -> tuple[str, str, str | None]:
        storage = self.files.storage
        if not hasattr(storage, "resolve_path"):
            return "", "asr_path_unavailable", None
        provider_getter = getattr(self.registry, "get_asr_provider", None)
        if not callable(provider_getter):
            return "", "asr_provider_missing", None
        try:
            provider = provider_getter()
            result = provider.transcribe_file(str(storage.resolve_path(storage_key)), user_id=user_id)
        except NotImplementedError:
            return "", "asr_documented_only", None
        except ProviderError as exc:
            logger.warning("ASR provider failed: %s", exc.to_safe_dict())
            return "", exc.error_type.value if hasattr(exc.error_type, "value") else str(exc.error_type), None
        except Exception:
            logger.exception("Unexpected ASR failure")
            return "", "asr_failed", None
        return result.transcript.strip(), result.provider, result.model

    def _tts_pending(self, provider: str) -> SpeechSynthesisResponse:
        return SpeechSynthesisResponse(
            status="pending",
            provider=provider,
            message="TTS provider 当前未实现或不可用，未生成音频文件。",
        )

    def _score_transcript(self, transcript: str) -> dict[str, int]:
        words = re.findall(r"[A-Za-z']+", transcript.lower())
        word_count = len(words)
        unique_ratio = len(set(words)) / max(1, word_count)
        filler_count = sum(1 for word in words if word in {"um", "uh", "er", "ah", "like"})
        sentence_count = max(1, len(re.findall(r"[.!?。！？]", transcript)) or 1)
        avg_sentence_len = word_count / sentence_count
        fluency = 72 + min(18, word_count // 8) - min(22, filler_count * 4)
        grammar = 76
        if re.search(r"\bi (is|are|amn't)\b|\bhe are\b|\bshe are\b|\bthey is\b", transcript, flags=re.I):
            grammar -= 18
        if avg_sentence_len < 4:
            grammar -= 8
        vocabulary = 64 + round(min(28, unique_ratio * 32)) + min(8, word_count // 30)
        return {
            "fluency": self._clamp_score(fluency),
            "grammar": self._clamp_score(grammar),
            "vocabulary": self._clamp_score(vocabulary),
        }

    def _feedback(self, *, transcript: str, prompt: str | None) -> tuple[SpokenFeedbackDraft, str | None]:
        schema = json.dumps(SpokenFeedbackDraft.model_json_schema(), ensure_ascii=False)
        request = (
            f"口语任务：{prompt or '英语复述/自由表达'}\n"
            f"Transcript:\n{transcript}\n\n"
            f"JSON Schema:\n{schema}\n\n"
            "只输出 JSON。不要给分数，只给逐句问题和 correction_plan。"
        )
        try:
            provider = self.registry.get_llm_provider()
            result = provider.chat(
                [
                    LlmMessage(role="system", content="你是英语口语反馈老师。只负责叙事反馈，不输出或修改分数。"),
                    LlmMessage(role="user", content=request),
                ],
                temperature=0.2,
                max_tokens=800,
            )
            try:
                return self._parse_feedback(result.content), result.model
            except (ValueError, ValidationError) as exc:
                repaired = provider.chat(
                    [
                        LlmMessage(role="system", content="修复为符合 JSON Schema 的严格 JSON，只输出 JSON。"),
                        LlmMessage(role="user", content=f"Schema:\n{schema}\n\n错误：{exc}\n\n原文：{result.content}"),
                    ],
                    temperature=0,
                    max_tokens=800,
                )
                return self._parse_feedback(repaired.content), repaired.model
        except Exception:
            logger.exception("Spoken feedback LLM failed; using fallback")
            return self._fallback_feedback(transcript), "template-fallback"

    def _fallback_feedback(self, transcript: str) -> SpokenFeedbackDraft:
        issues: list[SpokenEnglishIssueRead] = []
        if re.search(r"\bum\b|\buh\b|\ber\b", transcript, flags=re.I):
            issues.append(
                SpokenEnglishIssueRead(
                    text="filler words",
                    issue="简化模式：检测到 um/uh/er 等填充词，可能影响流利度。",
                    suggestion="先停顿半秒再继续说，减少无意义填充词。",
                )
            )
        if len(re.findall(r"[A-Za-z']+", transcript)) < 25:
            issues.append(
                SpokenEnglishIssueRead(
                    text=transcript[:80],
                    issue="简化模式：表达样本较短，证据不足。",
                    suggestion="补充 45 秒以上的完整复述，再进行更稳定的口语画像。",
                )
            )
        return SpokenFeedbackDraft(
            issues=issues,
            correction_plan=[
                "用 3 句话复述同一主题：定义、例子、结论。",
                "录第二遍时刻意减少填充词，并补一个 because/so 连接句。",
                "把第二遍 transcript 再提交一次，让 BKT/Elo/FSRS 写入新的口语练习记录。",
            ],
        )

    def _parse_feedback(self, content: str) -> SpokenFeedbackDraft:
        text = (content or "").strip()
        fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.S | re.I)
        if fenced:
            text = fenced.group(1).strip()
        if not text.startswith("{"):
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                text = text[start : end + 1]
        if not text:
            raise ValueError("empty spoken feedback JSON")
        return SpokenFeedbackDraft.model_validate(json.loads(text))

    def _ensure_audio(self, filename: str, content_type: str) -> None:
        suffix = Path(filename).suffix.lower()
        if suffix not in AUDIO_SUFFIXES and not (content_type or "").lower().startswith("audio/"):
            raise ValueError("spoken_english_requires_audio_file")

    def _average_score(self, scores: dict[str, int]) -> int:
        return round(sum(scores.values()) / max(1, len(scores)))

    def _clamp_score(self, value: int | float) -> int:
        return max(0, min(100, round(value)))
