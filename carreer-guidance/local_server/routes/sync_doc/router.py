from fastapi import APIRouter, Request

from src.handlers.sync_doc_handler import SyncDataHandler
from src.request_body.sync_doc import SyncDocumentsRequest
from src.utils.api_response import BadRequest, InternalServerError, NotFound, Ok

RequestContext = dict[str, str]

router = APIRouter(prefix="/api/sync-documents", tags=["sync-documents"])


@router.post(
    "",
    summary="Sync documents",
    description="Download files to local and start ingestion job",
)
async def sync_documents_endpoint(
    payload: SyncDocumentsRequest,
    request: Request,
) -> dict:
    try:
        context: RequestContext = {
            "trace_id": request.state.trace_id,
            "user_id": str(payload.user_id),
        }
        handler = SyncDataHandler(
            execution_id=str(context["trace_id"]),
        )
        response = handler.handle_sync_data(body=payload, context=context)
        return Ok(response.model_dump()).get_response()
    except ValueError as exc:
        return BadRequest(str(exc)).get_response()
    except Exception:
        return InternalServerError("Failed to process sync job.").get_response()


@router.get(
    "/{job_id}",
    summary="Get sync status",
    description="Get status of a sync job by job_id",
)
async def get_sync_status(job_id: str) -> dict:
    handler = SyncDataHandler(
        execution_id=job_id,
    )
    try:
        status = handler.handle_get_sync_data_status(
            params={"ingestion_job_id": job_id},
        )
        return Ok(status.model_dump()).get_response()
    except ValueError as exc:
        if "not found" not in str(exc).lower():
            return BadRequest(str(exc)).get_response()
        return NotFound(f"job_id '{job_id}' not found").get_response()
    except Exception:
        return InternalServerError("Failed to retrieve sync status.").get_response()
