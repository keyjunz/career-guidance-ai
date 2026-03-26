from fastapi import APIRouter, Depends, Request

from src.handlers.base_handler import DomainError, RequestContext
from src.handlers.sync_doc_handler import (
    SyncDataHandler,
    SyncDocumentModuleProtocol,
    SyncDocumentModuleRuntime,
)
from src.request_body.sync_doc import SyncDocumentsRequest
from src.utils.api_response import BadRequest, InternalServerError, NotFound, Ok

router = APIRouter(prefix="/api/sync-documents", tags=["sync-documents"])


def get_sync_module() -> SyncDocumentModuleProtocol:
    """Provide sync-document module dependency for routes."""

    return SyncDocumentModuleRuntime()


@router.post(
    "",
    summary="Sync documents",
    description="Download files to local and start ingestion job",
)
async def sync_documents_endpoint(
    payload: SyncDocumentsRequest,
    request: Request,
    sync_module: SyncDocumentModuleProtocol = Depends(get_sync_module),
) -> dict:
    try:
        context = RequestContext(
            trace_id=request.state.trace_id, user_id=str(payload.user_id)
        )
        handler = SyncDataHandler(
            execution_id=context.trace_id,
            sync_document_module=sync_module,
        )
        response = handler.handle_sync_data(body=payload, context=context)
        return Ok(response.model_dump()).get_response()
    except ValueError as exc:
        return BadRequest(str(exc)).get_response()
    except DomainError as exc:
        if exc.code == "BAD_REQUEST":
            return BadRequest(exc.message).get_response()
        return InternalServerError(exc.message).get_response()
    except Exception:
        return InternalServerError("Failed to process sync job.").get_response()


@router.get(
    "/{job_id}",
    summary="Get sync status",
    description="Get status of a sync job by job_id",
)
async def get_sync_status(job_id: str) -> dict:
    handler = SyncDataHandler(
        execution_id=f"status-{job_id}",
        sync_document_module=SyncDocumentModuleRuntime(),
    )
    try:
        status = handler.handle_get_sync_data_status(
            params={"ingestion_job_id": job_id},
        )
        return Ok(status.model_dump()).get_response()
    except DomainError as exc:
        if exc.code == "BAD_REQUEST":
            return BadRequest(exc.message).get_response()
        return NotFound(f"job_id '{job_id}' not found").get_response()
    except Exception:
        return InternalServerError("Failed to retrieve sync status.").get_response()
