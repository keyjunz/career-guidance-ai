"""Chat handler that orchestrates chat module calls."""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator
from typing import Protocol

from src.agent import main as agent_main
from src.handlers.base_handler import (
    DomainError,
    RequestContext,
    map_exception_to_domain_error,
)
from src.request_body.chat import ChatRequest, ChatResponse


class ChatbotProtocol(Protocol):
    """Protocol for chatbot module dependency."""

    async def invoke(
        self, request: ChatRequest, context: RequestContext
    ) -> ChatResponse: ...

    async def invoke_stream(
        self, request: ChatRequest, context: RequestContext
    ) -> AsyncIterator[str]: ...


class AgentChatbot:
    """Runtime chatbot adapter backed by agent layer."""

    async def invoke(
        self, request: ChatRequest, context: RequestContext
    ) -> ChatResponse:
        invoke_fn = getattr(agent_main, "invoke", None)
        if invoke_fn is None:
            raise DomainError(
                code="NOT_IMPLEMENTED",
                message="Chat agent is not configured.",
            )

        result = invoke_fn(request=request, context=context)
        if inspect.isawaitable(result):
            result = await result

        if isinstance(result, ChatResponse):
            return result
        if isinstance(result, dict):
            return ChatResponse.model_validate(result)

        raise DomainError(
            code="INTERNAL_ERROR",
            message="Invalid response from chat agent.",
        )

    async def invoke_stream(
        self, request: ChatRequest, context: RequestContext
    ) -> AsyncIterator[str]:
        invoke_stream_fn = getattr(agent_main, "invoke_stream", None)
        if invoke_stream_fn is None:
            raise DomainError(
                code="NOT_IMPLEMENTED",
                message="Chat stream agent is not configured.",
            )

        stream = invoke_stream_fn(request=request, context=context)
        if inspect.isawaitable(stream):
            stream = await stream

        async for token in stream:
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
