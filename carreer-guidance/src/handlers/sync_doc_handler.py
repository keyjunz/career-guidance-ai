"""Sync-document handler that orchestrates ingestion module calls."""

from __future__ import annotations

from typing import Protocol
from uuid import uuid4

from src.handlers.base_handler import RequestContext, map_exception_to_domain_error
from src.request_body.sync_doc import SyncDocumentsRequest, SyncDocumentsResponse


class SyncDocumentModuleProtocol(Protocol):
    """Protocol for sync document module dependency."""

    async def sync_documents(
        self, request: SyncDocumentsRequest, context: RequestContext
    ) -> SyncDocumentsResponse: ...


class StubSyncDocumentModule:
    """Fallback sync module implementation to keep local server runnable."""

    async def sync_documents(
        self, request: SyncDocumentsRequest, context: RequestContext
    ) -> SyncDocumentsResponse:
        return SyncDocumentsResponse(
            job_id=f"job-{uuid4()}",
            status="pending",
            processed=len(request.file_urls),
            failed=0,
            downloaded=len(request.file_urls),
        )


async def handle_sync_documents(
    request: SyncDocumentsRequest,
    context: RequestContext,
    sync_module: SyncDocumentModuleProtocol,
) -> SyncDocumentsResponse:
    """Handle sync request and map failures to DomainError."""

    try:
        return await sync_module.sync_documents(request=request, context=context)
    except Exception as exc:  # pragma: no cover - defensive mapping
        raise map_exception_to_domain_error(exc) from exc
