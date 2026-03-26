"""FastAPI application entrypoint for local development server."""

from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from local_server.routes.chat.router import router as chat_router
from local_server.routes.sync_doc.router import router as sync_doc_router
from src.handlers.base_handler import DomainError
from src.request_body.common import ErrorResponse

APP_NAME = "career-guidance-ai"
APP_VERSION = "0.1.0"


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title="Career Guidance AI Local Server",
        version=APP_VERSION,
        description="Local API server for career guidance chat and document sync.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_trace_id(request: Request, call_next):
        trace_id = request.headers.get("x-trace-id", str(uuid4()))
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["x-trace-id"] = trace_id
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        payload = ErrorResponse(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": exc.errors()},
            trace_id=getattr(request.state, "trace_id", None),
        )
        return JSONResponse(status_code=422, content=payload.model_dump())

    @app.exception_handler(DomainError)
    async def domain_exception_handler(
        request: Request, exc: DomainError
    ) -> JSONResponse:
        payload = ErrorResponse(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            trace_id=getattr(request.state, "trace_id", None),
        )
        return JSONResponse(status_code=400, content=payload.model_dump())

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        payload = ErrorResponse(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
            details={"exception_type": exc.__class__.__name__},
            trace_id=getattr(request.state, "trace_id", None),
        )
        return JSONResponse(status_code=500, content=payload.model_dump())

    @app.get("/health", tags=["health"], summary="Healthcheck")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok", "service": APP_NAME}

    app.include_router(chat_router)
    app.include_router(sync_doc_router)
    return app


app = create_app()
