"""Chat handler that orchestrates chat module calls."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol
from uuid import uuid4

from src.handlers.base_handler import RequestContext, map_exception_to_domain_error
from src.request_body.chat import ChatRequest, ChatResponse, ContentItem


class ChatbotProtocol(Protocol):
    """Protocol for chatbot module dependency."""

    async def invoke(
        self, request: ChatRequest, context: RequestContext
    ) -> ChatResponse: ...

    async def invoke_stream(
        self, request: ChatRequest, context: RequestContext
    ) -> AsyncIterator[str]: ...


class StubChatbot:
    """Fallback chatbot implementation to keep local server runnable."""

    async def invoke(
        self, request: ChatRequest, context: RequestContext
    ) -> ChatResponse:
        conversation_id = request.conversation_id or uuid4()
        text = (request.message or "").strip() or "Da nhan hinh anh tu nguoi dung."
        return ChatResponse(
            type="text",
            content=[ContentItem(type="text", text=f"[stub] {text}")],
            conversation_id=conversation_id,
            trace_id=context.trace_id,
        )

    async def invoke_stream(
        self, request: ChatRequest, context: RequestContext
    ) -> AsyncIterator[str]:
        content = (request.message or "").strip() or "Da nhan request stream"
        for token in ["[stub] ", content]:
            yield token


async def handle_chat(
    request: ChatRequest,
    context: RequestContext,
    chatbot: ChatbotProtocol,
) -> ChatResponse:
    """Handle non-streaming chat request and map failures to DomainError."""

    try:
        return await chatbot.invoke(request=request, context=context)
    except Exception as exc:  # pragma: no cover - defensive mapping
        raise map_exception_to_domain_error(exc) from exc


async def handle_chat_stream(
    request: ChatRequest,
    context: RequestContext,
    chatbot: ChatbotProtocol,
) -> AsyncIterator[str]:
    """Handle streaming chat request as async token iterator."""

    try:
        async for token in chatbot.invoke_stream(request=request, context=context):
            yield token
    except Exception as exc:  # pragma: no cover - defensive mapping
        raise map_exception_to_domain_error(exc) from exc
