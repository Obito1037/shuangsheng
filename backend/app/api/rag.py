from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_provider_registry
from app.core.security import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.integrations.registry import ProviderRegistry
from app.schemas.rag import RagAnswerResponse, RagAskRequest, RagIndexDocumentRequest, RagIndexTextRequest
from app.services.rag_service import RagService

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/index-text")
def index_text(
    payload: RagIndexTextRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    registry: ProviderRegistry = Depends(get_provider_registry),
):
    try:
        return RagService(db, registry).index_text(
            user_id=current_user.id,
            knowledge_base_id=payload.knowledge_base_id,
            title=payload.title,
            text=payload.text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/index-document")
def index_document(
    payload: RagIndexDocumentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    registry: ProviderRegistry = Depends(get_provider_registry),
):
    try:
        return RagService(db, registry).index_document(
            user_id=current_user.id,
            knowledge_base_id=payload.knowledge_base_id,
            document_id=payload.document_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/ask", response_model=RagAnswerResponse)
def ask(
    payload: RagAskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    registry: ProviderRegistry = Depends(get_provider_registry),
) -> RagAnswerResponse:
    return RagService(db, registry).ask(
        user_id=current_user.id,
        knowledge_base_id=payload.knowledge_base_id,
        question=payload.question,
        top_k=payload.top_k,
    )

