from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_provider_registry
from app.core.security import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.integrations.registry import ProviderRegistry
from app.schemas.speech import SpeechSynthesisRequest, SpeechSynthesisResponse, SpokenEnglishAnalyzeRequest, SpokenEnglishResponse
from app.services.spoken_english_service import SpokenEnglishService

router = APIRouter(prefix="/api/speech", tags=["speech"])


@router.post("/english/{file_id}", response_model=SpokenEnglishResponse)
def analyze_spoken_english(
    file_id: str,
    payload: SpokenEnglishAnalyzeRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    registry: ProviderRegistry = Depends(get_provider_registry),
) -> SpokenEnglishResponse:
    try:
        return SpokenEnglishService(db, registry=registry).analyze(user_id=current_user.id, file_id=file_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/tts", response_model=SpeechSynthesisResponse)
def synthesize_speech(
    payload: SpeechSynthesisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    registry: ProviderRegistry = Depends(get_provider_registry),
) -> SpeechSynthesisResponse:
    return SpokenEnglishService(db, registry=registry).synthesize(user_id=current_user.id, payload=payload)
