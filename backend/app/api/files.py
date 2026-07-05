from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.file import FileRead, FileUploadResponse
from app.services.enhanced_document_service import EnhancedDocumentService
from app.services.file_service import FileService

router = APIRouter(prefix="/api/files", tags=["files"])


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(upload: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        file = await FileService(db).upload(user_id=current_user.id, upload=upload)
        documents = EnhancedDocumentService(db)
        document = documents.register_upload(user_id=current_user.id, file=file)
        file_read = FileRead.model_validate(file)
        document_read = documents.detail(user_id=current_user.id, document_id=document.id)
        return FileUploadResponse(**file_read.model_dump(), file=file_read, document=document_read)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("", response_model=list[FileRead])
def list_files(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return FileService(db).list(current_user.id)


@router.get("/{file_id}", response_model=FileRead)
def get_file(file_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return FileService(db).get(user_id=current_user.id, file_id=file_id)


@router.delete("/{file_id}")
def delete_file(file_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    FileService(db).delete(user_id=current_user.id, file_id=file_id)
    return {"ok": True}
