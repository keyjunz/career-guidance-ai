import asyncio
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

from src.agent.edges.pipeline import run_pipeline
from src.agent.state.agent_state import AgentRuntimeState
from src.agent.state.user_store_registry import UserStoreRegistry
from src.request_body.chat_request_body import ChatRequest, ChatResponse, ContentItem


def _resolve_execution_id(context: dict[str, Any] | None) -> str:
    ctx = context or {}
    return str(
        ctx.get("trace_id")
        or ctx.get("execution_id")
        or ctx.get("x_execution_id")
        or uuid4()
    )


def _build_state(
    request: ChatRequest, context: dict[str, Any] | None
) -> AgentRuntimeState:
    user_id = str(request.user_id)
    execution_id = _resolve_execution_id(context)
    conversation_id = uuid4()

    question = request.question.strip()
    if not question:
        raise ValueError("question is required for RAG chat")

    return AgentRuntimeState(
        user_id=user_id,
        execution_id=execution_id,
        conversation_id=conversation_id,
        question=question,
    )


def _to_chat_response(state: AgentRuntimeState) -> ChatResponse:
    return ChatResponse(
        type="text",
        content=[ContentItem(type="text", text=state.answer)],
        conversation_id=state.conversation_id,
        trace_id=state.execution_id,
        statuses=state.status_history,
        cached=state.cache_hit,
    )


def invoke(request: ChatRequest, context: dict[str, Any] | None = None) -> ChatResponse:
    state = _build_state(request, context)
    store = UserStoreRegistry.get_store(state.user_id)
    final_state = run_pipeline(state, store)
    return _to_chat_response(final_state)


def _iter_answer_tokens(answer: str) -> list[str]:
    words = answer.split()
    if not words:
        return []

    tokens: list[str] = []
    for index, word in enumerate(words):
        suffix = " " if index < len(words) - 1 else ""
        tokens.append(f"{word}{suffix}")
    return tokens


async def invoke_stream(
    request: ChatRequest,
    context: dict[str, Any] | None = None,
) -> AsyncIterator[str]:
    state = _build_state(request, context)
    store = UserStoreRegistry.get_store(state.user_id)

    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def status_callback(status: str) -> None:
        loop.call_soon_threadsafe(
            queue.put_nowait,
            {
                "type": "status",
                "value": status,
            },
        )

    def worker() -> None:
        try:
            final_state = run_pipeline(state, store, status_callback=status_callback)
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {
                    "type": "done",
                    "state": final_state,
                },
            )
        except Exception as exc:  # pragma: no cover
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {
                    "type": "error",
                    "error": str(exc),
                },
            )

    background_task = asyncio.create_task(asyncio.to_thread(worker))

    while True:
        payload = await queue.get()
        payload_type = payload.get("type")

        if payload_type == "status":
            yield f"[STATUS] {payload.get('value', '')}"
            continue

        if payload_type == "error":
            await background_task
            raise RuntimeError(str(payload.get("error") or "streaming failed"))

        if payload_type == "done":
            final_state = payload.get("state")
            if not isinstance(final_state, AgentRuntimeState):
                await background_task
                raise RuntimeError("invalid final state in stream pipeline")

            for token in _iter_answer_tokens(final_state.answer):
                yield token

            break

    await background_task
