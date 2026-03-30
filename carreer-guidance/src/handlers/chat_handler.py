"""Chat handler that orchestrates chat module calls."""


import inspect
import logging
from collections.abc import AsyncIterator
from typing import Any

from src.agent import main as agent_main
from src.request_body.chat import ChatRequest, ChatResponse
from src.services.dispatcher_service.main import DispatcherService
from src.utils.api_response import BadRequest, InternalServerError, NotFound, Ok

RequestContext = dict[str, Any]
logger = logging.getLogger(__name__)


class ChatHandler:
    """Handler for chat endpoint using sync or async invocation mode."""

    def __init__(self, execution_id: str) -> None:
        self.execution_id = execution_id
        self.dispatcher_service = DispatcherService(execution_id=execution_id)

    async def invoke_async_chat_handler(self, request: ChatRequest) -> dict:
        try:
            payload = {
                "target_function_name": "invoke_sync_chat_handler",
                **request.model_dump(mode="json"),
                "execution_id": self.execution_id,
            }
            logger.info("Enqueue async chat request: %s", payload)
            await self.dispatcher_service.dispatch_chat_request(payload)

            response = {
                "message": "Message dispatched successfully",
                "execution_id": self.execution_id,
            }
            return Ok(response).get_response()
        except Exception as exc:
            logger.error("Error in async chat handler: %s", exc)
            return InternalServerError(
                "Failed to dispatch async chat request."
            ).get_response()

    async def invoke_sync_chat_handler(self, request: ChatRequest) -> dict:
        try:
            logger.info("Invoking sync chat handler with message: %s", request.message)
            context: RequestContext = {
                "trace_id": self.execution_id,
                "user_id": str(request.user_id),
            }

            invoke_fn = getattr(agent_main, "invoke", None)
            if invoke_fn is None:
                raise RuntimeError("Chat agent is not configured.")

            result = invoke_fn(request=request, context=context)
            if inspect.isawaitable(result):
                result = await result

            if isinstance(result, ChatResponse):
                payload = result.model_dump()
            elif isinstance(result, dict):
                payload = ChatResponse.model_validate(result).model_dump()
            else:
                raise RuntimeError("Invalid response from chat agent.")

            return Ok(payload).get_response()
        except ValueError as exc:
            logger.error("Value error in sync chat handler: %s", exc)
            return BadRequest(str(exc)).get_response()
        except Exception as exc:
            logger.error("Error in sync chat handler: %s", exc)
            return InternalServerError("Failed to process chat request.").get_response()

    async def execute(
        self,
        request: ChatRequest | str | dict,
        invocation_type: str,
    ) -> dict:
        logger.info("Executing chat handler with invocation type: %s", invocation_type)
        try:
            parsed_request = self._parse_request(request)
        except ValueError as exc:
            logger.error("Value error parsing chat request: %s", exc)
            return BadRequest(f"Invalid request body format: {exc}").get_response()
        except Exception as exc:
            logger.error("Error parsing chat request: %s", exc)
            return InternalServerError("Failed to parse chat request.").get_response()

        match invocation_type:
            case "async":
                return await self.invoke_async_chat_handler(parsed_request)
            case "sync":
                return await self.invoke_sync_chat_handler(parsed_request)
            case _:
                return NotFound("Invocation type not found").get_response()

    async def stream_tokens(
        self,
        request: ChatRequest | str | dict,
    ) -> AsyncIterator[str]:
        parsed_request = self._parse_request(request)
        context: RequestContext = {
            "trace_id": self.execution_id,
            "user_id": str(parsed_request.user_id),
        }

        invoke_stream_fn = getattr(agent_main, "invoke_stream", None)
        if invoke_stream_fn is None:
            raise RuntimeError("Chat stream agent is not configured.")

        stream = invoke_stream_fn(request=parsed_request, context=context)
        if inspect.isawaitable(stream):
            stream = await stream

        async for token in stream:
            yield token

    def _parse_request(self, request: ChatRequest | str | dict) -> ChatRequest:
        match request:
            case ChatRequest():
                return request
            case str():
                return ChatRequest.model_validate_json(request)
            case dict():
                return ChatRequest.model_validate(request)
            case _:
                raise ValueError("Invalid request format for chat handler.")
