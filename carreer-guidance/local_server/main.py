import json
import logging
import os
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from local_server.routes.chat.router import router as chat_router
from local_server.routes.sync_doc.router import router as sync_doc_router
from src.utils.common import ErrorResponse

APP_NAME = "career-guidance-ai"
APP_VERSION = "0.1.0"
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
SWAGGER_DIR = ASSETS_DIR / "swagger"
SWAGGER_HTML_PATH = SWAGGER_DIR / "index.html"
SWAGGER_JSON_PATH = SWAGGER_DIR / "openapi.json"
IMAGE_DIR_SETTING = os.getenv("IMAGE_STORAGE_DIR", "database/images")
IMAGE_DIR = (
    Path(IMAGE_DIR_SETTING)
    if Path(IMAGE_DIR_SETTING).is_absolute()
    else (BASE_DIR / IMAGE_DIR_SETTING)
)


def configure_app_logging() -> None:
    """Configure app-wide logging so module logs appear in uvicorn terminal."""
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    root_logger = logging.getLogger()

    if uvicorn_error_logger.handlers:
        root_logger.handlers = uvicorn_error_logger.handlers
        root_logger.setLevel(level)
    elif not root_logger.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )
    else:
        root_logger.setLevel(level)

    logging.getLogger("src").setLevel(level)
    logging.getLogger("local_server").setLevel(level)


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    configure_app_logging()

    app = FastAPI(
        title="Career Guidance AI Local Server",
        version=APP_VERSION,
        description="Local API server for career guidance chat and document sync.",
        docs_url=None,
        redoc_url=None,
    )

    app.include_router(chat_router)
    app.include_router(sync_doc_router)

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    SWAGGER_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")
    app.mount("/images", StaticFiles(directory=str(IMAGE_DIR)), name="images")

    def custom_openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        openapi_schema["openapi"] = "3.0.3"

        body_schema_name = (
            "Body_upload_documents_endpoint_api_sync_documents_upload_post"
        )
        upload_schema = (
            openapi_schema.get("components", {})
            .get("schemas", {})
            .get(body_schema_name, {})
        )
        file_items = upload_schema.get("properties", {}).get("files", {}).get("items")
        if isinstance(file_items, dict) and file_items.get("contentMediaType"):
            file_items.pop("contentMediaType", None)
            file_items["type"] = "string"
            file_items["format"] = "binary"

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

    @app.get("/docs", include_in_schema=False)
    async def custom_docs() -> FileResponse:
        return FileResponse(SWAGGER_HTML_PATH)

    @app.on_event("startup")
    async def export_openapi_to_assets() -> None:
        SWAGGER_JSON_PATH.write_text(
            json.dumps(app.openapi(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_execution_id(request: Request, call_next):
        execution_id = request.headers.get("x-execution-id", str(uuid4()))
        request.state.execution_id = execution_id
        response = await call_next(request)
        response.headers["x-execution-id"] = execution_id
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
            execution_id=getattr(request.state, "execution_id", None),
        )
        return JSONResponse(status_code=422, content=payload.model_dump())

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        payload = ErrorResponse(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
            details={"exception_type": exc.__class__.__name__},
            execution_id=getattr(request.state, "execution_id", None),
        )
        return JSONResponse(status_code=500, content=payload.model_dump())

    @app.get("/health", tags=["health"], summary="Healthcheck")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok", "service": APP_NAME}

    return app


app = create_app()
