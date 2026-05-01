import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from src.modules.chat_module.main import ChatModuleImpl
from src.request_body.chat_request_body import ChatRequest

RequestContext = dict[str, Any]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ChatHandler:
    def __init__(
        self,
        execution_id: str,
    ) -> None:
        self.execution_id = execution_id

    def _build_context(self, request: ChatRequest) -> RequestContext:
        return {
            "execution_id": self.execution_id,
            "user_id": str(request.user_id),
        }

    def _build_module(self, request: ChatRequest) -> ChatModuleImpl:
        return ChatModuleImpl(
            execution_id=self.execution_id,
            user_id=str(request.user_id),
        )

    async def execute(
        self,
        request: ChatRequest,
        invocation_type: str = "sync",
    ) -> dict[str, Any]:
        mode = (invocation_type or "sync").strip().lower()
        if mode not in {"sync", "async"}:
            raise ValueError("invocation_type must be either 'sync' or 'async'")

        if mode == "async":
            return await self.invoke_async_chat_handler(request)

        return await self.invoke_sync_chat_handler(request)

    async def invoke_async_chat_handler(self, request: ChatRequest) -> dict[str, Any]:
        module = self._build_module(request)
        context = self._build_context(request)
        return await module.invoke_async_chat(request, context=context)

    async def invoke_sync_chat_handler(self, request: ChatRequest) -> dict[str, Any]:
        module = self._build_module(request)
        context = self._build_context(request)
        response = await asyncio.to_thread(module.invoke_sync_chat, request, context)
        return response.model_dump(mode="json")

    async def stream_tokens(self, request: ChatRequest) -> AsyncIterator[str]:
        module = self._build_module(request)
        context = self._build_context(request)
        async for token in module.stream_tokens(request, context=context):
            yield token
