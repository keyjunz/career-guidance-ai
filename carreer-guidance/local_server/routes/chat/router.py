import asyncio
import json

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from src.database.models import User
from src.handlers.chat_handler import ChatHandler
from src.request_body.chat_request_body import ChatRequest
from src.services.auth_service.dependencies import get_current_user
from src.utils.api_response import BadRequest, InternalServerError, Ok

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _to_json_response(payload: dict) -> JSONResponse:
    status_code = int(payload.get("statusCode", 200))
    headers = payload.get("headers", {"Content-Type": "application/json"})
    body_raw = payload.get("body", "{}")
    try:
        body = json.loads(body_raw) if isinstance(body_raw, str) else body_raw
    except Exception:
        body = {"raw": str(body_raw)}
    return JSONResponse(status_code=status_code, content=body, headers=headers)


@router.post("", summary="Chat", description="Handle chat request")
async def chat_endpoint(
    payload: ChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    invocation_type: str = Query(default="sync", pattern="^(sync|async)$"),
) -> JSONResponse:
    try:
        handler = ChatHandler(
            execution_id=request.state.execution_id,
            user_id=current_user.id,
        )
        response_payload = await handler.execute(
            payload, invocation_type=invocation_type
        )
        return _to_json_response(Ok(response_payload).get_response())
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"error": str(exc)})
    except ValueError as exc:
        return _to_json_response(BadRequest(str(exc)).get_response())
    except Exception:
        return _to_json_response(
            InternalServerError("Failed to process chat request.").get_response()
        )


@router.post(
    "/stream",
    summary="Stream chat",
    description="Stream chat response token-by-token via SSE",
    response_model=None,
)
async def chat_stream_endpoint(
    payload: ChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse | JSONResponse:
    try:
        handler = ChatHandler(
            execution_id=request.state.execution_id,
            user_id=current_user.id,
        )

        async def event_stream():
            agen = handler.stream_tokens(payload)
            try:
                next_task = None
                while True:
                    if next_task is None:
                        next_task = asyncio.create_task(agen.__anext__())

                    # Wait up to 1 second for the next item
                    done, _ = await asyncio.wait(
                        [next_task],
                        timeout=1.0,
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    if await request.is_disconnected():
                        next_task.cancel()
                        await agen.aclose()
                        break

                    if next_task in done:
                        try:
                            stream_event = next_task.result()
                        except StopAsyncIteration:
                            break
                        except asyncio.CancelledError:
                            break
                        
                        next_task = None # reset for next iteration

                        event_type = str(stream_event.get("type") or "")
                        if event_type == "status":
                            status_text = str(stream_event.get("status") or "")
                            yield f"event: status\ndata: {json.dumps({'status': status_text, 'execution_id': request.state.execution_id})}\n\n"
                        elif event_type == "token":
                            token = str(stream_event.get("token") or "")
                            yield f"event: token\ndata: {json.dumps({'token': token, 'execution_id': request.state.execution_id})}\n\n"
                        elif event_type == "final_payload":
                            payload_data = stream_event.get("payload")
                            if isinstance(payload_data, dict):
                                yield f"event: final_payload\ndata: {json.dumps(payload_data)}\n\n"
                        elif event_type == "done":
                            execution_id = str(
                                stream_event.get("execution_id")
                                or request.state.execution_id
                            )
                            yield f"event: done\ndata: {json.dumps({'execution_id': execution_id})}\n\n"

            except asyncio.CancelledError:
                pass
            except ValueError as exc:
                error_response = BadRequest(str(exc)).get_response()
                yield f"event: error\ndata: {json.dumps(error_response)}\n\n"
            except Exception:
                error_response = InternalServerError(
                    "Failed to process chat stream."
                ).get_response()
                yield f"event: error\ndata: {json.dumps(error_response)}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")
    except Exception:
        return _to_json_response(
            InternalServerError("Failed to initialize chat stream.").get_response()
        )
