"""Conversation and message persistence helpers."""

from __future__ import annotations

from uuid import UUID, uuid4

from src.config.database import session_scope
from src.database.models import Conversation
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.message_repository import MessageRepository
from src.repositories.request_cost_log_repository import RequestCostLogRepository
from src.services.cost_tracking.token_usage import TokenUsageAccumulator


class ConversationAccessError(PermissionError):
    """Raised when a user accesses another user's conversation."""


class ConversationNotFoundError(ValueError):
    """Raised when conversation_id does not exist."""


def _truncate_title(text: str, max_len: int = 80) -> str:
    t = (text or "").strip().replace("\n", " ")
    if len(t) <= max_len:
        return t or "New conversation"
    return f"{t[: max_len - 1].rstrip()}…"


def resolve_conversation_id(
    *,
    user_id: UUID,
    conversation_id: UUID | None,
) -> UUID:
    if conversation_id is None:
        return uuid4()

    with session_scope() as session:
        repo = ConversationRepository(session)
        existing = repo.get_by_id(conversation_id)
        if existing is None:
            return conversation_id
        if existing.user_id != user_id:
            raise ConversationAccessError("Conversation access denied.")
        return existing.id


def save_chat_turn(
    *,
    user_id: UUID,
    question: str,
    answer: str,
    conversation_id: UUID | None,
    session_id: str,
    usage: TokenUsageAccumulator | None = None,
) -> tuple[UUID, UUID]:
    normalized_question = question.strip()
    normalized_answer = answer.strip()
    if not normalized_question:
        raise ValueError("question must not be empty")
    if not normalized_answer:
        raise ValueError("answer must not be empty")

    normalized_session_id = (session_id or uuid4().hex).strip()[:50] or uuid4().hex[:50]

    with session_scope() as session:
        conversation_repo = ConversationRepository(session)
        message_repo = MessageRepository(session)
        cost_repo = RequestCostLogRepository(session)

        conversation = _resolve_conversation_entity(
            conversation_repo=conversation_repo,
            user_id=user_id,
            conversation_id=conversation_id,
            session_id=normalized_session_id,
            first_question=normalized_question,
        )

        cost_log_id = None
        if usage and (usage.input_tokens > 0 or usage.output_tokens > 0):
            cost_row = cost_repo.create(
                {
                    "user_id": user_id,
                    "request_type": usage.primary_request_type(),
                    "model_name": usage.primary_model_name(),
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                }
            )
            cost_log_id = cost_row.id

        message = message_repo.create(
            {
                "conversation_id": conversation.id,
                "user_message": normalized_question,
                "chatbot_response": normalized_answer,
                "user_id": user_id,
                "cost_log_id": cost_log_id,
            }
        )

    return conversation.id, message.id


def _resolve_conversation_entity(
    *,
    conversation_repo: ConversationRepository,
    user_id: UUID,
    conversation_id: UUID | None,
    session_id: str,
    first_question: str,
) -> Conversation:
    if conversation_id is not None:
        existing = conversation_repo.get_by_id(conversation_id)
        if existing is None:
            return conversation_repo.create(
                {
                    "id": conversation_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "title": _truncate_title(first_question),
                }
            )
        if existing.user_id != user_id:
            raise ConversationAccessError("Conversation access denied.")
        if not existing.title:
            existing.title = _truncate_title(first_question)
            conversation_repo.update(existing, {"title": existing.title})
        return existing

    return conversation_repo.create(
        {
            "session_id": session_id,
            "user_id": user_id,
            "title": _truncate_title(first_question),
        }
    )


def list_user_conversations(
    *,
    user_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    with session_scope() as session:
        conversation_repo = ConversationRepository(session)
        message_repo = MessageRepository(session)
        rows = conversation_repo.get_recent_conversations(
            user_id, limit=limit, offset=offset
        )
        out: list[dict] = []
        for conv in rows:
            first_msg = message_repo.get_first_by_conversation(conv.id)
            preview = ""
            if first_msg:
                preview = first_msg.user_message.strip()[:120]
            title = (conv.title or "").strip()
            if not title and first_msg:
                title = _truncate_title(first_msg.user_message)
            if not title:
                title = "New conversation"
            out.append(
                {
                    "id": str(conv.id),
                    "title": title,
                    "started_at": conv.started_at.isoformat()
                    if conv.started_at
                    else None,
                    "preview": preview,
                }
            )
        return out


def get_conversation_messages(
    *,
    user_id: UUID,
    conversation_id: UUID,
    page: int = 1,
    page_size: int = 100,
) -> list[dict]:
    with session_scope() as session:
        conversation_repo = ConversationRepository(session)
        message_repo = MessageRepository(session)
        conv = conversation_repo.get_by_id(conversation_id)
        if conv is None:
            raise ConversationNotFoundError("Conversation not found.")
        if conv.user_id != user_id:
            raise ConversationAccessError("Conversation access denied.")

        messages = message_repo.get_by_conversation_paginated(
            conversation_id, page=page, page_size=page_size
        )
        items: list[dict] = []
        for msg in messages:
            items.append(
                {
                    "id": str(msg.id),
                    "role": "user",
                    "text": msg.user_message,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                }
            )
            items.append(
                {
                    "id": f"{msg.id}_assistant",
                    "role": "assistant",
                    "text": msg.chatbot_response,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                }
            )
        return items


def update_conversation_title(
    *,
    user_id: UUID,
    conversation_id: UUID,
    title: str,
) -> None:
    normalized = title.strip()
    if not normalized:
        raise ValueError("title must not be empty")

    with session_scope() as session:
        conversation_repo = ConversationRepository(session)
        conv = conversation_repo.get_by_id(conversation_id)
        if conv is None:
            raise ConversationNotFoundError("Conversation not found.")
        if conv.user_id != user_id:
            raise ConversationAccessError("Conversation access denied.")
        conversation_repo.update(conv, {"title": normalized[:200]})


def delete_conversation(*, user_id: UUID, conversation_id: UUID) -> None:
    with session_scope() as session:
        conversation_repo = ConversationRepository(session)
        conv = conversation_repo.get_by_id(conversation_id)
        if conv is None:
            raise ConversationNotFoundError("Conversation not found.")
        if conv.user_id != user_id:
            raise ConversationAccessError("Conversation access denied.")
        conversation_repo.delete(conv)
