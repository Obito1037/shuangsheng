from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.document import DocumentDetail, DocumentParseRequest, DocumentRead
from app.services.document_service import DocumentService

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("", response_model=list[DocumentRead])
def list_documents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[DocumentRead]:
    return DocumentService(db).list(current_user.id)


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DocumentDetail:
    try:
        return DocumentService(db).detail(user_id=current_user.id, document_id=document_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/parse", response_model=DocumentRead)
def parse_document(payload: DocumentParseRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        document, _ = DocumentService(db).parse(user_id=current_user.id, payload=payload)
        return document
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
