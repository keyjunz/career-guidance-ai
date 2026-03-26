"""Contracts for sync document module."""

from __future__ import annotations

from typing import Protocol

from src.handlers.base_handler import RequestContext
from src.request_body.sync_doc import SyncDocumentsRequest, SyncDocumentsResponse


class SyncDocumentModule(Protocol):
    """Sync module contract."""

    def sync_documents(
        self,
        request: SyncDocumentsRequest,
        context: RequestContext,
    ) -> SyncDocumentsResponse: ...

    def get_status_sync_doc(
        self,
        ingestion_job_id: str,
        context: RequestContext,
    ) -> SyncDocumentsResponse: ...
