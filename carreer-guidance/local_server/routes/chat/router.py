import json
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from src.handlers.base_handler import RequestContext
from src.handlers.chat_handler import (
    ChatbotProtocol,
    StubChatbot,
    handle_chat,
    handle_chat_stream,
)
from src.request_body.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])


def get_chatbot() -> ChatbotProtocol:
    """Provide chatbot dependency for route handlers."""

    return StubChatbot()


def get_request_context(request: Request, payload: ChatRequest) -> RequestContext:
    """Build request context from middleware state and payload."""

    return RequestContext(trace_id=request.state.trace_id, user_id=str(payload.user_id))


@router.post(
    "", response_model=ChatResponse, summary="Chat", description="Handle chat request"
)
async def chat_endpoint(
    payload: ChatRequest,
    request: Request,
    chatbot: ChatbotProtocol = Depends(get_chatbot),
) -> ChatResponse:
    context = get_request_context(request, payload)
    return await handle_chat(request=payload, context=context, chatbot=chatbot)


@router.post(
    "/stream",
    summary="Stream chat",
    description="Stream chat response token-by-token via SSE",
)
async def chat_stream_endpoint(
    payload: ChatRequest,
    request: Request,
    chatbot: ChatbotProtocol = Depends(get_chatbot),
) -> StreamingResponse:
    context = get_request_context(request, payload)

    async def event_stream():
        async for token in handle_chat_stream(
            request=payload, context=context, chatbot=chatbot
        ):
            yield f"data: {json.dumps({'token': token, 'trace_id': context.trace_id})}\\n\\n"

        yield "event: done\\ndata: {}\\n\\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
