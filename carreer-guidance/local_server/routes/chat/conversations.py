from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from src.database.models import User
from src.services.auth_service.dependencies import get_current_user
from src.services.database_service.conversation_db import (
    ConversationAccessError,
    ConversationNotFoundError,
)
from src.services.database_service.main import DatabaseChatService

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ConversationSummary(BaseModel):
    id: str
    title: str
    started_at: str | None = None
    preview: str = ""


class ConversationMessage(BaseModel):
    id: str
    role: str
    text: str
    timestamp: str | None = None
    image_urls: list[str] = Field(default_factory=list)


class UpdateConversationTitleRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


def _chat_db(request) -> DatabaseChatService:
    return DatabaseChatService(execution_id=request.state.execution_id)


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(
    request: Request,
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    service = _chat_db(request)
    rows = service.list_user_conversations(
        current_user.id,
        limit=limit,
        offset=offset,
    )
    return [ConversationSummary(**row) for row in rows]


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[ConversationMessage],
)
def list_conversation_messages(
    conversation_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
):
    service = _chat_db(request)
    try:
        rows = service.get_conversation_messages(
            current_user.id,
            conversation_id,
            page=page,
            page_size=page_size,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ConversationAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    return [ConversationMessage(**row) for row in rows]


@router.patch("/conversations/{conversation_id}")
def update_conversation_title(
    conversation_id: UUID,
    body: UpdateConversationTitleRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    service = _chat_db(request)
    try:
        service.update_conversation_title(
            current_user.id,
            conversation_id,
            body.title,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ConversationAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return {"ok": True}


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    service = _chat_db(request)
    try:
        service.delete_conversation(current_user.id, conversation_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ConversationAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    return {"ok": True}
