import json
import logging
import os
import time
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse

from src.database.models import User
from src.handlers.sync_doc_handler import SyncDataHandler
from src.services.auth_service.dependencies import get_current_user, require_roles
from src.utils.api_response import BadRequest, InternalServerError, Ok, TooManyRequests

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


RequestContext = dict[str, str]

router = APIRouter(prefix="/api/sync-documents", tags=["sync-documents"])

_BASE_DIR = Path(__file__).resolve().parents[3]
DOWNLOAD_STORAGE_DIR = Path(
    os.getenv(
        "DOWNLOAD_STORAGE_DIR",
        str(_BASE_DIR / "src" / "database" / "file_downloaded"),
    )
)

_sync_doc_role_guard = require_roles("admin", "employee")


def _to_json_response(payload: dict) -> JSONResponse:
    status_code = int(payload.get("statusCode", 200))
    headers = payload.get("headers", {"Content-Type": "application/json"})
    body_raw = payload.get("body", "{}")
    try:
        body = json.loads(body_raw) if isinstance(body_raw, str) else body_raw
    except Exception:
        body = {"raw": str(body_raw)}
    return JSONResponse(status_code=status_code, content=body, headers=headers)


async def _save_uploaded_files(
    files: list[UploadFile],
    user_id: str,
) -> list[str]:
    """Save uploaded files to disk and return file paths."""
    upload_dir = DOWNLOAD_STORAGE_DIR / user_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_paths: list[str] = []
    for file in files:
        if not file.filename:
            raise ValueError("File name is required")

        file_path = str(upload_dir / file.filename)
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        file_paths.append(file_path)
        logger.info(
            "sync upload file saved: user_id=%s file_name=%s size_bytes=%d",
            user_id,
            str(file.filename),
            len(content),
        )
    return file_paths


@router.post(
    "/upload",
    summary="Upload and process documents",
    description="Upload files, save to server, and start processing",
    response_model=None,
)
async def upload_documents_endpoint(
    request: Request,
    files: list[UploadFile] = File(...),
    industry_type: str | None = Form(default=None),
    current_user: User = Depends(_sync_doc_role_guard),
) -> JSONResponse:
    try:
        user_uuid = current_user.id

        if not files:
            return _to_json_response(BadRequest("No files uploaded").get_response())

        logger.info(
            "sync upload request received: user_id=%s files=%d industry_type=%s",
            str(user_uuid),
            len(files),
            str(industry_type or ""),
        )

        file_paths = await _save_uploaded_files(files, str(user_uuid))

        client_host = request.client.host if request and request.client else "unknown"
        execution_id = f"{int(time.time())}_{client_host}"
        logger.info("sync upload execution id generated: execution_id=%s", execution_id)

        context: RequestContext = {
            "execution_id": execution_id,
            "user_id": str(user_uuid),
        }

        handler = SyncDataHandler(execution_id=execution_id)
        response = handler.process_uploaded_files(
            file_paths=file_paths,
            user_id=user_uuid,
            context=context,
            industry_type=industry_type,
        )
        logger.info(
            "sync upload completed: execution_id=%s user_id=%s job_id=%s status=%s processed=%d failed=%d",
            execution_id,
            str(user_uuid),
            response.job_id,
            response.status,
            response.processed,
            response.failed,
        )
        return _to_json_response(Ok(response.model_dump()).get_response())
    except ValueError as exc:
        message = str(exc)
        if "HTTP 429" in message or "quota" in message.lower():
            return _to_json_response(TooManyRequests(message).get_response())
        return _to_json_response(BadRequest(message).get_response())
    except Exception as exc:
        return _to_json_response(
            InternalServerError(f"Failed to process upload: {str(exc)}").get_response()
        )


@router.post(
    "/upload-gemini",
    summary="Upload and process documents with Gemini OCR",
    description="Upload files, save to server, and start Gemini OCR processing",
    response_model=None,
)
async def upload_documents_gemini_endpoint(
    request: Request,
    files: list[UploadFile] = File(...),
    industry_type: str | None = Form(default=None),
    current_user: User = Depends(_sync_doc_role_guard),
) -> JSONResponse:
    try:
        user_uuid = current_user.id

        if not files:
            return _to_json_response(BadRequest("No files uploaded").get_response())

        logger.info(
            "sync upload (gemini) request received: user_id=%s files=%d industry_type=%s",
            str(user_uuid),
            len(files),
            str(industry_type or ""),
        )

        file_paths = await _save_uploaded_files(files, str(user_uuid))

        client_host = request.client.host if request and request.client else "unknown"
        execution_id = f"{int(time.time())}_{client_host}"
        logger.info(
            "sync upload (gemini) execution id generated: execution_id=%s",
            execution_id,
        )

        context: RequestContext = {
            "execution_id": execution_id,
            "user_id": str(user_uuid),
        }

        handler = SyncDataHandler(execution_id=execution_id)
        response = handler.process_uploaded_files_gemini(
            file_paths=file_paths,
            user_id=user_uuid,
            context=context,
            industry_type=industry_type,
        )
        logger.info(
            "sync upload (gemini) completed: execution_id=%s user_id=%s job_id=%s status=%s processed=%d failed=%d",
            execution_id,
            str(user_uuid),
            response.job_id,
            response.status,
            response.processed,
            response.failed,
        )
        return _to_json_response(Ok(response.model_dump()).get_response())
    except ValueError as exc:
        message = str(exc)
        if "HTTP 429" in message or "quota" in message.lower():
            return _to_json_response(TooManyRequests(message).get_response())
        return _to_json_response(BadRequest(message).get_response())
    except Exception as exc:
        return _to_json_response(
            InternalServerError(
                f"Failed to process upload (gemini): {str(exc)}"
            ).get_response()
        )


@router.get(
    "/status/{ingestion_job_id}",
    summary="Get sync status",
    description="Get current synchronization status by ingestion job id",
    response_model=None,
)
async def get_sync_status_endpoint(
    request: Request,
    ingestion_job_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    try:
        if not ingestion_job_id.strip():
            return _to_json_response(
                BadRequest("ingestion_job_id is required").get_response()
            )

        execution_id_from_state = getattr(request.state, "execution_id", None)
        execution_id = (
            str(execution_id_from_state)
            if execution_id_from_state
            else str(int(time.time()))
        )
        context: RequestContext = {
            "execution_id": execution_id,
            "user_id": str(current_user.id),
        }

        handler = SyncDataHandler(execution_id=execution_id)
        response = handler.get_sync_status(
            ingestion_job_id=ingestion_job_id,
            context=context,
        )
        payload = response.model_dump()
        payload["ingestion_job_id"] = payload.pop("job_id", ingestion_job_id)
        return _to_json_response(Ok(payload).get_response())
    except ValueError as exc:
        return _to_json_response(BadRequest(str(exc)).get_response())
    except Exception as exc:
        return _to_json_response(
            InternalServerError(f"Failed to get sync status: {str(exc)}").get_response()
        )
