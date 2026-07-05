from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from app.core.config import VivoSettings, load_settings

CapabilityName = Literal[
    "llm_chat",
    "llm_stream_chat",
    "image_understanding",
    "ocr",
    "embedding",
    "similarity",
    "query_rewrite",
    "text_translation",
    "realtime_short_asr",
    "long_audio_listen",
    "long_audio_transcribe",
    "tts",
    "image_generation",
    "video_generation",
    "dialect_asr",
    "simultaneous_interpretation",
    "voice_clone",
    "poi",
    "android_side_llm",
    "android_side_text_moderation",
]


@dataclass(frozen=True, slots=True)
class CapabilityMetadata:
    name: str
    provider: str
    default_model: str | None
    supports_streaming: bool
    supports_image: bool
    requires_app_id: bool
    requires_app_key: bool
    implemented: bool
    documented_only: bool
    android_side: bool
    provider_unavailable: bool
    live_test_passed: bool
    live_test_failed: bool
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_capability_registry(settings: VivoSettings | None = None) -> dict[str, CapabilityMetadata]:
    selected = settings or load_settings()
    return {
        "llm_chat": CapabilityMetadata(
            name="llm_chat",
            provider="vivo",
            default_model=selected.vivo_llm_text_model,
            supports_streaming=False,
            supports_image=False,
            requires_app_id=False,
            requires_app_key=True,
            implemented=True,
            documented_only=False,
            android_side=False,
            provider_unavailable=False,
            live_test_passed=True,
            live_test_failed=False,
        ),
        "llm_stream_chat": CapabilityMetadata(
            name="llm_stream_chat",
            provider="vivo",
            default_model=selected.vivo_llm_stream_model,
            supports_streaming=True,
            supports_image=False,
            requires_app_id=False,
            requires_app_key=True,
            implemented=True,
            documented_only=False,
            android_side=False,
            provider_unavailable=False,
            live_test_passed=True,
            live_test_failed=False,
        ),
        "image_understanding": CapabilityMetadata(
            name="image_understanding",
            provider="vivo",
            default_model=selected.vivo_image_understanding_model,
            supports_streaming=False,
            supports_image=True,
            requires_app_id=False,
            requires_app_key=True,
            implemented=True,
            documented_only=False,
            android_side=False,
            provider_unavailable=False,
            live_test_passed=True,
            live_test_failed=False,
            notes="Route to an image-capable chat model; avoid Volc-DeepSeek-V3.2 for image input.",
        ),
        "ocr": CapabilityMetadata(
            name="ocr",
            provider="vivo",
            default_model=None,
            supports_streaming=False,
            supports_image=True,
            requires_app_id=True,
            requires_app_key=True,
            implemented=True,
            documented_only=False,
            android_side=False,
            provider_unavailable=False,
            live_test_passed=True,
            live_test_failed=False,
        ),
        "embedding": CapabilityMetadata(
            name="embedding",
            provider="vivo",
            default_model=selected.vivo_embedding_model,
            supports_streaming=False,
            supports_image=False,
            requires_app_id=False,
            requires_app_key=True,
            implemented=True,
            documented_only=False,
            android_side=False,
            provider_unavailable=False,
            live_test_passed=True,
            live_test_failed=False,
        ),
        "similarity": CapabilityMetadata(
            name="similarity",
            provider="vivo",
            default_model=selected.vivo_rerank_model,
            supports_streaming=False,
            supports_image=False,
            requires_app_id=False,
            requires_app_key=True,
            implemented=True,
            documented_only=False,
            android_side=False,
            provider_unavailable=False,
            live_test_passed=True,
            live_test_failed=False,
        ),
        "query_rewrite": CapabilityMetadata(
            name="query_rewrite",
            provider="vivo",
            default_model=None,
            supports_streaming=False,
            supports_image=False,
            requires_app_id=False,
            requires_app_key=True,
            implemented=True,
            documented_only=False,
            android_side=False,
            provider_unavailable=True,
            live_test_passed=False,
            live_test_failed=False,
            notes="Live API currently returns code=-3002, mapped to provider_unavailable.",
        ),
        "realtime_short_asr": CapabilityMetadata(
            name="realtime_short_asr",
            provider="vivo",
            default_model="shortasrinput",
            supports_streaming=True,
            supports_image=False,
            requires_app_id=True,
            requires_app_key=True,
            implemented=True,
            documented_only=False,
            android_side=False,
            provider_unavailable=False,
            live_test_passed=False,
            live_test_failed=False,
            notes="WebSocket asr/v2; local backend accepts 16k/16bit/mono wav/pcm files.",
        ),
        **_documented_only_capabilities(),
    }


def _documented_only_capabilities() -> dict[str, CapabilityMetadata]:
    cloud_names = {
        "text_translation": "translation/query/self",
        "long_audio_listen": "long audio websocket",
        "long_audio_transcribe": "long audio file transcription",
        "tts": "TTS audio generation",
        "image_generation": "api/v1/image_generation",
        "video_generation": "api/v1/submit_task",
        "dialect_asr": "dialect websocket ASR",
        "simultaneous_interpretation": "simultaneous interpretation",
        "voice_clone": "voice clone",
        "poi": "geocoding/POI",
    }
    records = {
        name: CapabilityMetadata(
            name=name,
            provider="vivo",
            default_model=None,
            supports_streaming="websocket" in note.lower(),
            supports_image=name in {"image_generation", "video_generation"},
            requires_app_id=True,
            requires_app_key=True,
            implemented=False,
            documented_only=True,
            android_side=False,
            provider_unavailable=False,
            live_test_passed=False,
            live_test_failed=False,
            notes=note,
        )
        for name, note in cloud_names.items()
    }
    records["android_side_llm"] = CapabilityMetadata(
        name="android_side_llm",
        provider="vivo",
        default_model=None,
        supports_streaming=True,
        supports_image=True,
        requires_app_id=False,
        requires_app_key=False,
        implemented=False,
        documented_only=True,
        android_side=True,
        provider_unavailable=False,
        live_test_passed=False,
        live_test_failed=False,
        notes="Android SDK capability, not backend Provider.",
    )
    records["android_side_text_moderation"] = CapabilityMetadata(
        name="android_side_text_moderation",
        provider="vivo",
        default_model=None,
        supports_streaming=False,
        supports_image=False,
        requires_app_id=False,
        requires_app_key=False,
        implemented=False,
        documented_only=True,
        android_side=True,
        provider_unavailable=False,
        live_test_passed=False,
        live_test_failed=False,
        notes="Android SDK capability, not backend Provider.",
    )
    return records


CAPABILITY_REGISTRY = build_capability_registry()
