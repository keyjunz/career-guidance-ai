from fastapi import APIRouter, Request, UploadFile, Form, File
from fastapi.responses import JSONResponse
from uuid import UUID
import os
import time
import logging
import json
from pathlib import Path

from src.handlers.sync_doc_handler import SyncDataHandler
from src.utils.api_response import BadRequest, InternalServerError, Ok, TooManyRequests

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


RequestContext = dict[str, str]

router = APIRouter(prefix="/api/sync-documents", tags=["sync-documents"])

DOWNLOAD_STORAGE_DIR = Path(
    r"C:\Users\Nitro 5\OneDrive\Documents\nckh\kltn\career-guidance-ai\carreer-guidance\src\database\file_downloaded"
)


def _to_json_response(payload: dict) -> JSONResponse:
    status_code = int(payload.get("statusCode", 200))
    headers = payload.get("headers", {"Content-Type": "application/json"})
    body_raw = payload.get("body", "{}")
    try:
        body = json.loads(body_raw) if isinstance(body_raw, str) else body_raw
    except Exception:
        body = {"raw": str(body_raw)}
    return JSONResponse(status_code=status_code, content=body, headers=headers)


@router.post(
    "/upload",
    summary="Upload and process documents",
    description="Upload files, save to server, and start processing",
    response_model=None,
)
async def upload_documents_endpoint(
    request: Request,
    files: list[UploadFile] = File(...),
    user_id: str = Form(...),
    industry_type: str | None = Form(default=None),
) -> JSONResponse:
    try:
        # Validate user_id is a valid UUID
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            return _to_json_response(
                BadRequest(f"Invalid user_id format: {user_id}").get_response()
            )

        if not files:
            return _to_json_response(BadRequest("No files uploaded").get_response())

        logger.info(
            "sync upload request received: user_id=%s files=%d industry_type=%s",
            str(user_uuid),
            len(files),
            str(industry_type or ""),
        )

        # Create directory for storing uploaded files
        upload_dir = DOWNLOAD_STORAGE_DIR / str(user_uuid)
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_paths = []

        # Save uploaded files
        for file in files:
            if not file.filename:
                return _to_json_response(
                    BadRequest("File name is required").get_response()
                )

            file_path = str(upload_dir / file.filename)
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            file_paths.append(file_path)
            logger.info(
                "sync upload file saved: user_id=%s file_name=%s file_path=%s size_bytes=%d",
                str(user_uuid),
                str(file.filename),
                file_path,
                len(content),
            )

        # Generate execution_id from timestamp and client host
        client_host = request.client.host if request and request.client else "unknown"
        execution_id = f"{int(time.time())}_{client_host}"
        logger.info("sync upload execution id generated: execution_id=%s", execution_id)

        # Process files
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


@router.get(
    "/status/{ingestion_job_id}",
    summary="Get sync status",
    description="Get current synchronization status by ingestion job id",
    response_model=None,
)
async def get_sync_status_endpoint(
    request: Request,
    ingestion_job_id: str,
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
