import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from src.agent import main as agent_main
from src.request_body.chat_request_body import ChatRequest, ChatResponse
from src.services.cost_tracking.token_usage import get_token_usage_snapshot
from src.services.database_service.main import DatabaseChatService
from src.services.dispatcher_service.main import DispatcherService

RequestContext = dict[str, Any]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ChatModuleImpl:
    def __init__(
        self,
        execution_id: str,
        user_id: str | None = None,
        dispatcher_service: DispatcherService | None = None,
        chat_db_service: DatabaseChatService | None = None,
    ) -> None:
        self.execution_id = execution_id
        self.user_id = str(user_id).strip() if user_id else None
        self.dispatcher_service = dispatcher_service or DispatcherService(
            execution_id=execution_id
        )
        self.chat_db_service = chat_db_service or DatabaseChatService(
            execution_id=execution_id
        )

    def _build_context(
        self, request: ChatRequest, context: RequestContext
    ) -> RequestContext:
        resolved_context = dict(context)
        resolved_context["execution_id"] = self.execution_id
        resolved_context.setdefault("user_id", str(request.user_id))
        return resolved_context

    async def invoke_async_chat(
        self,
        request: ChatRequest,
        context: RequestContext,
    ) -> dict[str, Any]:
        resolved_context = self._build_context(request, context)
        request_payload = request.model_dump(mode="json")
        payload = {
            "target_function_name": "invoke_sync_chat_handler",
            "execution_id": self.execution_id,
            **request_payload,
            "context": resolved_context,
        }

        await self.dispatcher_service.dispatch_chat_request(payload)

        return {
            "status": "queued",
            "message": "Chat request has been queued.",
            "execution_id": self.execution_id,
        }

    def invoke_sync_chat(
        self,
        request: ChatRequest,
        context: RequestContext,
    ) -> ChatResponse:
        resolved_context = self._build_context(request, context)
        response = agent_main.invoke(request, context=resolved_context)
        self._persist_chat_turn(
            request=request,
            answer=self._extract_answer_text(response),
            conversation_id=response.conversation_id,
            context=resolved_context,
        )
        return response

    async def stream_tokens(
        self,
        request: ChatRequest,
        context: RequestContext,
    ) -> AsyncIterator[dict[str, Any]]:
        resolved_context = self._build_context(request, context)
        answer_chunks: list[str] = []
        conversation_id = None
        usage = None
        async for event in agent_main.invoke_stream(request, context=resolved_context):
            if event.get("type") == "token":
                answer_chunks.append(str(event.get("token") or ""))
            elif event.get("type") == "final_payload":
                payload = event.get("payload")
                if isinstance(payload, dict):
                    conversation_id = payload.get("conversation_id")
            elif event.get("type") == "usage":
                usage = event.get("usage")
                continue
            yield event

        answer_text = "".join(answer_chunks).strip()
        if answer_text:
            await asyncio.to_thread(
                self._persist_chat_turn,
                request=request,
                answer=answer_text,
                conversation_id=conversation_id,
                context=resolved_context,
                usage=usage,
            )

    @staticmethod
    def _coerce_uuid(value: Any) -> UUID | None:
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        if isinstance(value, str):
            try:
                return UUID(value)
            except ValueError:
                return None
        return None

    def _extract_answer_text(self, response: ChatResponse) -> str:
        text_parts: list[str] = []
        for item in response.content:
            if item.type == "text" and item.text:
                text_parts.append(item.text)
        return "\n".join(text_parts).strip()

    def _persist_chat_turn(
        self,
        *,
        request: ChatRequest,
        answer: str,
        conversation_id: Any,
        context: RequestContext,
        usage: Any | None = None,
    ) -> None:
        if not answer.strip():
            return

        try:
            session_id = str(context.get("execution_id") or self.execution_id).strip()
            usage = usage or get_token_usage_snapshot()
            resolved_conversation_id = self._coerce_uuid(conversation_id)
            if resolved_conversation_id is None:
                resolved_conversation_id = request.conversation_id
            self.chat_db_service.save_chat_turn(
                user_id=request.user_id,
                question=request.question,
                answer=answer,
                conversation_id=resolved_conversation_id,
                session_id=session_id,
                usage=usage,
            )
        except Exception as exc:
            logger.warning(
                "Failed to persist chat turn to DB: execution_id=%s user_id=%s error=%s",
                self.execution_id,
                str(request.user_id),
                exc,
            )
