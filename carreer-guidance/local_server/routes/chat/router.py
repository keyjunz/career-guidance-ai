import json
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from src.handlers.base_handler import DomainError, RequestContext
from src.handlers.chat_handler import (
    AgentChatbot,
    ChatbotProtocol,
    handle_chat,
    handle_chat_stream,
)
from src.request_body.chat import ChatRequest, ChatResponse
from src.utils.api_response import BadRequest, InternalServerError, Ok

router = APIRouter(prefix="/api/chat", tags=["chat"])


def get_chatbot() -> ChatbotProtocol:
    """Provide chatbot dependency for route handlers."""

    return AgentChatbot()


def get_request_context(request: Request, payload: ChatRequest) -> RequestContext:
    """Build request context from middleware state and payload."""

    return RequestContext(trace_id=request.state.trace_id, user_id=str(payload.user_id))


@router.post("", summary="Chat", description="Handle chat request")
async def chat_endpoint(
    payload: ChatRequest,
    request: Request,
    chatbot: ChatbotProtocol = Depends(get_chatbot),
) -> dict:
    try:
        context = get_request_context(request, payload)
        response: ChatResponse = await handle_chat(
            request=payload, context=context, chatbot=chatbot
        )
        return Ok(response.model_dump()).get_response()
    except DomainError as exc:
        if exc.code == "BAD_REQUEST":
            return BadRequest(exc.message).get_response()
        return InternalServerError(exc.message).get_response()
    except Exception:
        return InternalServerError("Failed to process chat request.").get_response()


@router.post(
    "/stream",
    summary="Stream chat",
    description="Stream chat response token-by-token via SSE",
)
async def chat_stream_endpoint(
    payload: ChatRequest,
    request: Request,
    chatbot: ChatbotProtocol = Depends(get_chatbot),
) -> StreamingResponse | dict:
    try:
        context = get_request_context(request, payload)

        async def event_stream():
            try:
                async for token in handle_chat_stream(
                    request=payload, context=context, chatbot=chatbot
                ):
                    yield f"data: {json.dumps({'token': token, 'trace_id': context.trace_id})}\\n\\n"

                yield "event: done\\ndata: {}\\n\\n"
            except DomainError as exc:
                error_response = (
                    BadRequest(exc.message).get_response()
                    if exc.code == "BAD_REQUEST"
                    else InternalServerError(exc.message).get_response()
                )
                yield f"event: error\\ndata: {json.dumps(error_response)}\\n\\n"
            except Exception:
                error_response = InternalServerError(
                    "Failed to process chat stream."
                ).get_response()
                yield f"event: error\\ndata: {json.dumps(error_response)}\\n\\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")
    except Exception:
        return InternalServerError("Failed to initialize chat stream.").get_response()
