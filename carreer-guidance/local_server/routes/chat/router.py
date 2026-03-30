import json
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from src.handlers.chat_handler import ChatHandler
from src.request_body.chat import ChatRequest
from src.utils.api_response import BadRequest, InternalServerError

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", summary="Chat", description="Handle chat request")
async def chat_endpoint(
    payload: ChatRequest,
    request: Request,
    invocation_type: str = Query(default="sync", pattern="^(sync|async)$"),
) -> dict:
    try:
        handler = ChatHandler(execution_id=request.state.trace_id)
        return await handler.execute(payload, invocation_type=invocation_type)
    except Exception:
        return InternalServerError("Failed to process chat request.").get_response()


@router.post(
    "/stream",
    summary="Stream chat",
    description="Stream chat response token-by-token via SSE",
    response_model=None,
)
async def chat_stream_endpoint(
    payload: ChatRequest,
    request: Request,
) -> StreamingResponse | dict:
    try:
        handler = ChatHandler(execution_id=request.state.trace_id)

        async def event_stream():
            try:
                async for token in handler.stream_tokens(payload):
                    yield f"data: {json.dumps({'token': token, 'trace_id': request.state.trace_id})}\\n\\n"

                yield "event: done\\ndata: {}\\n\\n"
            except ValueError as exc:
                error_response = BadRequest(str(exc)).get_response()
                yield f"event: error\\ndata: {json.dumps(error_response)}\\n\\n"
            except Exception:
                error_response = InternalServerError(
                    "Failed to process chat stream."
                ).get_response()
                yield f"event: error\\ndata: {json.dumps(error_response)}\\n\\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")
    except Exception:
        return InternalServerError("Failed to initialize chat stream.").get_response()
