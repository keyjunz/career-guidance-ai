from fastapi import APIRouter, Depends, HTTPException, Request

from src.handlers.base_handler import RequestContext
from src.handlers.sync_doc_handler import (
    SyncDocumentModuleProtocol,
    StubSyncDocumentModule,
    handle_sync_documents,
)
from src.request_body.sync_doc import SyncDocumentsRequest, SyncDocumentsResponse

router = APIRouter(prefix="/api/sync-documents", tags=["sync-documents"])

_SYNC_JOB_STATUS: dict[str, SyncDocumentsResponse] = {}


def get_sync_module() -> SyncDocumentModuleProtocol:
    """Provide sync-document module dependency for routes."""

    return StubSyncDocumentModule()


@router.post(
    "",
    response_model=SyncDocumentsResponse,
    summary="Sync documents",
    description="Download files to local and start ingestion job",
)
async def sync_documents_endpoint(
    payload: SyncDocumentsRequest,
    request: Request,
    sync_module: SyncDocumentModuleProtocol = Depends(get_sync_module),
) -> SyncDocumentsResponse:
    context = RequestContext(
        trace_id=request.state.trace_id, user_id=str(payload.user_id)
    )
    response = await handle_sync_documents(
        request=payload, context=context, sync_module=sync_module
    )
    _SYNC_JOB_STATUS[response.job_id] = response
    return response


@router.get(
    "/{job_id}",
    response_model=SyncDocumentsResponse,
    summary="Get sync status",
    description="Get status of a sync job by job_id",
)
async def get_sync_status(job_id: str) -> SyncDocumentsResponse:
    result = _SYNC_JOB_STATUS.get(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"job_id '{job_id}' not found")
    return result
