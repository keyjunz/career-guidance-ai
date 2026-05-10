import hashlib
import logging
import os
import shutil
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from src.config.database import session_scope
from src.database.models import Document, Role, User
from src.repositories.document_repository import DocumentRepository
from src.repositories.user_repository import UserRepository
from src.request_body.auth_request_body import UserResponse
from src.services.auth_service.dependencies import require_roles
from src.services.auth_service.password import hash_password
from src.services.vector_db_service.main import VectorDBService

logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).resolve().parents[3]
_IMAGE_DIR_SETTING = os.getenv("IMAGE_STORAGE_DIR", "database/images")
_IMAGE_DIR = (
    Path(_IMAGE_DIR_SETTING)
    if Path(_IMAGE_DIR_SETTING).is_absolute()
    else (_BASE_DIR / _IMAGE_DIR_SETTING)
)
_DOWNLOAD_DIR = Path(
    os.getenv(
        "DOWNLOAD_STORAGE_DIR",
        str(_BASE_DIR / "src" / "database" / "file_downloaded"),
    )
)

router = APIRouter(prefix="/api/admin", tags=["admin"])

_admin_guard = require_roles("admin")


def _user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        user_name=user.user_name,
        email=user.email,
        phone=user.phone,
        is_active=user.is_active,
        role=user.role.role,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get(
    "/users",
    summary="List all users",
    response_model=list[UserResponse],
)
def list_users(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: User = Depends(_admin_guard),
):
    with session_scope() as session:
        repo = UserRepository(session)
        users = repo.get_many(limit=limit, offset=offset)
        for u in users:
            _ = u.role.role
        session.expunge_all()
    return [_user_to_response(u) for u in users]


@router.get(
    "/users/{user_id}",
    summary="Get user detail",
    response_model=UserResponse,
)
def get_user(
    user_id: UUID,
    _admin: User = Depends(_admin_guard),
):
    with session_scope() as session:
        repo = UserRepository(session)
        user = repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        _ = user.role.role
        session.expunge(user)
    return _user_to_response(user)


@router.put(
    "/users/{user_id}",
    summary="Update user (role, is_active, etc.)",
    response_model=UserResponse,
)
def update_user(
    user_id: UUID,
    payload: dict,
    _admin: User = Depends(_admin_guard),
):
    allowed_fields = {"user_name", "email", "phone", "is_active", "role_id", "password"}
    update_data = {k: v for k, v in payload.items() if k in allowed_fields}

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No valid fields to update. Allowed: {', '.join(sorted(allowed_fields))}",
        )

    if "password" in update_data:
        update_data["password"] = hash_password(str(update_data["password"]))

    if "role_id" in update_data:
        try:
            update_data["role_id"] = UUID(str(update_data["role_id"]))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role_id format",
            )

    with session_scope() as session:
        repo = UserRepository(session)
        user = repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        user = repo.update(user, update_data)
        _ = user.role.role
        session.expunge(user)

    logger.info("Admin updated user: id=%s fields=%s", user_id, list(update_data.keys()))
    return _user_to_response(user)


@router.delete(
    "/users/{user_id}",
    summary="Delete user",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user(
    user_id: UUID,
    _admin: User = Depends(_admin_guard),
):
    with session_scope() as session:
        repo = UserRepository(session)
        deleted = repo.delete_by_id(user_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

    logger.info("Admin deleted user: id=%s", user_id)
    return None


# ---------------------------------------------------------------------------
# Document management endpoints
# ---------------------------------------------------------------------------

class DocumentResponse(BaseModel):
    id: UUID
    user_id: UUID
    document_name: str
    document_type: str
    ingestion_job_id: str | None
    status: str
    created_at: str
    updated_at: str
    image_urls: list[str]


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


def _build_doc_id_from_path(file_path: str) -> str:
    """Replicate the OCR service's doc_id generation from a file path."""
    p = Path(file_path)
    digest = hashlib.md5(str(p).encode("utf-8")).hexdigest()[:8]
    return f"{p.stem}-{digest}"


def _collect_image_urls(doc: Document) -> list[str]:
    """Scan IMAGE_STORAGE_DIR for images belonging to this document."""
    file_path = (doc.content or "").strip()
    if not file_path:
        return []

    doc_id = _build_doc_id_from_path(file_path)
    doc_image_dir = _IMAGE_DIR / doc_id
    if not doc_image_dir.is_dir():
        return []

    urls: list[str] = []
    for img_file in sorted(doc_image_dir.rglob("*")):
        if img_file.is_file() and img_file.suffix.lower() in {
            ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp",
        }:
            rel = img_file.relative_to(_IMAGE_DIR)
            urls.append(f"/images/{rel.as_posix()}")
    return urls


def _doc_to_response(doc: Document) -> DocumentResponse:
    return DocumentResponse(
        id=doc.id,
        user_id=doc.user_id,
        document_name=doc.document_name,
        document_type=doc.document_type,
        ingestion_job_id=doc.ingestion_job_id,
        status=doc.status,
        created_at=doc.created_at.isoformat() if doc.created_at else "",
        updated_at=doc.updated_at.isoformat() if doc.updated_at else "",
        image_urls=_collect_image_urls(doc),
    )


@router.get(
    "/documents",
    summary="List all synced documents",
    response_model=DocumentListResponse,
)
def list_documents(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: User = Depends(_admin_guard),
):
    with session_scope() as session:
        repo = DocumentRepository(session)
        docs = repo.get_all_paginated(limit=limit, offset=offset)
        total = repo.count_all()
        session.expunge_all()
    return DocumentListResponse(
        documents=[_doc_to_response(d) for d in docs],
        total=total,
    )


@router.get(
    "/documents/{document_id}",
    summary="Get document detail with images",
    response_model=DocumentResponse,
)
def get_document(
    document_id: UUID,
    _admin: User = Depends(_admin_guard),
):
    with session_scope() as session:
        repo = DocumentRepository(session)
        doc = repo.get_by_id(document_id)
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )
        session.expunge(doc)
    return _doc_to_response(doc)


@router.delete(
    "/documents/{document_id}",
    summary="Delete document (DB + ChromaDB + disk)",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document(
    document_id: UUID,
    _admin: User = Depends(_admin_guard),
):
    with session_scope() as session:
        repo = DocumentRepository(session)
        doc = repo.get_by_id(document_id)
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )
        file_path = (doc.content or "").strip()
        ingestion_job_id = doc.ingestion_job_id
        session.expunge(doc)

    # 1. Delete from ChromaDB
    if ingestion_job_id:
        try:
            vector_service = VectorDBService(execution_id="admin-delete")
            vector_service.delete_by_ingestion_job(ingestion_job_id)
        except Exception as exc:
            logger.warning(
                "ChromaDB delete failed for document=%s job=%s: %s",
                document_id, ingestion_job_id, exc,
            )

    # 2. Delete extracted images from disk
    if file_path:
        doc_id = _build_doc_id_from_path(file_path)
        doc_image_dir = _IMAGE_DIR / doc_id
        if doc_image_dir.is_dir():
            shutil.rmtree(doc_image_dir, ignore_errors=True)
            logger.info("Removed image dir: %s", doc_image_dir)

    # 3. Delete uploaded source file from disk
    source_path = Path(file_path) if file_path else None
    if source_path and source_path.is_file():
        try:
            source_path.unlink()
            logger.info("Removed source file: %s", source_path)
        except OSError as exc:
            logger.warning("Failed to remove source file: %s: %s", source_path, exc)

    # 4. Delete from Postgres
    with session_scope() as session:
        repo = DocumentRepository(session)
        deleted = repo.delete_by_id(document_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

    logger.info("Admin deleted document: id=%s", document_id)
    return None
