import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from src.modules.chat_module.main import ChatModuleImpl
from src.request_body.chat_request_body import ChatRequest

RequestContext = dict[str, Any]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ChatHandler:
    def __init__(
        self,
        execution_id: str,
        user_id: UUID,
    ) -> None:
        self.execution_id = execution_id
        self.user_id = user_id

    def _build_context(self) -> RequestContext:
        return {
            "execution_id": self.execution_id,
            "user_id": str(self.user_id),
        }

    def _build_module(self) -> ChatModuleImpl:
        return ChatModuleImpl(
            execution_id=self.execution_id,
            user_id=str(self.user_id),
        )

    def _inject_user_id(self, request: ChatRequest) -> ChatRequest:
        """Inject authenticated user_id into the request."""
        request.user_id = self.user_id
        return request

    async def execute(
        self,
        request: ChatRequest,
        invocation_type: str = "sync",
    ) -> dict[str, Any]:
        mode = (invocation_type or "sync").strip().lower()
        if mode not in {"sync", "async"}:
            raise ValueError("invocation_type must be either 'sync' or 'async'")

        request = self._inject_user_id(request)

        if mode == "async":
            return await self.invoke_async_chat_handler(request)

        return await self.invoke_sync_chat_handler(request)

    async def invoke_async_chat_handler(self, request: ChatRequest) -> dict[str, Any]:
        module = self._build_module()
        context = self._build_context()
        return await module.invoke_async_chat(request, context=context)

    async def invoke_sync_chat_handler(self, request: ChatRequest) -> dict[str, Any]:
        module = self._build_module()
        context = self._build_context()
        response = await asyncio.to_thread(module.invoke_sync_chat, request, context)
        return response.model_dump(mode="json")

    async def stream_tokens(self, request: ChatRequest) -> AsyncIterator[dict[str, Any]]:
        request = self._inject_user_id(request)
        module = self._build_module()
        context = self._build_context()
        async for event in module.stream_tokens(request, context=context):
            yield event
