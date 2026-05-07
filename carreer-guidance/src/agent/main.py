import asyncio
import logging
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Any
from uuid import uuid4

from src.agent.edges.pipeline import run_pipeline
from src.agent.state.agent_state import AgentRuntimeState
from src.agent.state.user_store_registry import UserStoreRegistry
from src.request_body.chat_request_body import ChatRequest, ChatResponse, ContentItem

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _resolve_execution_id(context: dict[str, Any] | None) -> str:
    ctx = context or {}
    return str(ctx.get("execution_id") or ctx.get("x_execution_id") or uuid4())


def _build_state(
    request: ChatRequest, context: dict[str, Any] | None
) -> AgentRuntimeState:
    user_id = str(request.user_id)
    execution_id = _resolve_execution_id(context)
    conversation_id = uuid4()

    question = request.question.strip()
    if not question:
        raise ValueError("question is required for RAG chat")

    state = AgentRuntimeState(
        user_id=user_id,
        execution_id=execution_id,
        conversation_id=conversation_id,
        question=question,
    )
    logger.info(
        "[agent-main] state built execution_id=%s user_id=%s conversation_id=%s question_len=%d",
        state.execution_id,
        state.user_id,
        state.conversation_id,
        len(state.question),
    )
    return state


def _to_chat_response(state: AgentRuntimeState) -> ChatResponse:
    content: list[ContentItem] = []
    answer_text = state.answer.strip()
    if answer_text:
        content.append(ContentItem(type="text", text=answer_text))

    for image_url in state.image_urls:
        try:
            content.append(ContentItem(type="image", image_url=image_url))
        except Exception:
            continue

    if not content:
        content.append(
            ContentItem(type="text", text="Khong tim thay cau tra loi phu hop.")
        )

    response_type = "text"
    has_text = any(item.type == "text" for item in content)
    has_image = any(item.type == "image" for item in content)
    if has_image and has_text:
        response_type = "mixed"
    elif has_image:
        response_type = "image"

    return ChatResponse(
        type=response_type,
        content=content,
        conversation_id=state.conversation_id,
        execution_id=state.execution_id,
        statuses=state.status_history,
        sources=state.sources,
        cached=state.cache_hit,
    )


def invoke(request: ChatRequest, context: dict[str, Any] | None = None) -> ChatResponse:
    started_at = perf_counter()
    state = _build_state(request, context)
    logger.info(
        "[agent-main] invoke started execution_id=%s user_id=%s",
        state.execution_id,
        state.user_id,
    )
    store = UserStoreRegistry.get_store(state.user_id)
    try:
        final_state = run_pipeline(state, store)
    except Exception:
        logger.exception(
            "[agent-main] invoke failed execution_id=%s user_id=%s",
            state.execution_id,
            state.user_id,
        )
        raise

    response = _to_chat_response(final_state)
    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info(
        "[agent-main] invoke finished execution_id=%s cache_hit=%s statuses=%d answer_len=%d elapsed_ms=%.2f",
        state.execution_id,
        state.cache_hit,
        len(state.status_history),
        len(state.answer),
        elapsed_ms,
    )
    return response


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
) -> AsyncIterator[dict[str, Any]]:
    started_at = perf_counter()
    state = _build_state(request, context)
    logger.info(
        "[agent-main] invoke_stream started execution_id=%s user_id=%s",
        state.execution_id,
        state.user_id,
    )
    store = UserStoreRegistry.get_store(state.user_id)

    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def status_callback(status: str) -> None:
        logger.info(
            "[agent-main] stream status execution_id=%s status=%s",
            state.execution_id,
            status,
        )
        loop.call_soon_threadsafe(
            queue.put_nowait,
            {
                "type": "status",
                "status": status,
            },
        )

    def worker() -> None:
        try:
            logger.info(
                "[agent-main] stream worker started execution_id=%s",
                state.execution_id,
            )
            final_state = run_pipeline(state, store, status_callback=status_callback)
            logger.info(
                "[agent-main] stream worker finished execution_id=%s answer_len=%d",
                state.execution_id,
                len(final_state.answer),
            )
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {
                    "type": "done",
                    "state": final_state,
                },
            )
        except Exception as exc:  # pragma: no cover
            logger.exception(
                "[agent-main] stream worker failed execution_id=%s",
                state.execution_id,
            )
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
            yield {"type": "status", "status": str(payload.get("status") or "")}
            continue

        if payload_type == "error":
            logger.error(
                "[agent-main] stream payload error execution_id=%s error=%s",
                state.execution_id,
                payload.get("error") or "streaming failed",
            )
            await background_task
            raise RuntimeError(str(payload.get("error") or "streaming failed"))

        if payload_type == "done":
            final_state = payload.get("state")
            if not isinstance(final_state, AgentRuntimeState):
                await background_task
                raise RuntimeError("invalid final state in stream pipeline")

            for token in _iter_answer_tokens(final_state.answer):
                yield {"type": "token", "token": token}

            final_payload = _to_chat_response(final_state).model_dump(mode="json")
            yield {
                "type": "final_payload",
                "payload": final_payload,
            }
            yield {
                "type": "done",
                "execution_id": final_state.execution_id,
            }

            logger.info(
                "[agent-main] stream done execution_id=%s answer_len=%d token_count=%d",
                state.execution_id,
                len(final_state.answer),
                len(_iter_answer_tokens(final_state.answer)),
            )

            break

    await background_task
    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info(
        "[agent-main] invoke_stream finished execution_id=%s cache_hit=%s elapsed_ms=%.2f",
        state.execution_id,
        state.cache_hit,
        elapsed_ms,
    )
