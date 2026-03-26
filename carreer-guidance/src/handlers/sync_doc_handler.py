"""Sync-document handler that orchestrates ingestion module calls."""

from __future__ import annotations

import logging
from typing import Protocol

from src.handlers.base_handler import (
    DomainError,
    RequestContext,
    map_exception_to_domain_error,
)
from src.modules.sync_doc_module.main import SyncDocumentModuleImpl
from src.request_body.sync_doc import SyncDocumentsRequest, SyncDocumentsResponse
from src.services.database_service import DatabaseSyncService
from src.services.document_service import DocumentService
from src.services.gemini.ocr_service import GeminiOCRService
from src.services.vector_db_services import VectorDBService

logger = logging.getLogger(__name__)


class SyncDocumentModuleProtocol(Protocol):
    """Protocol for sync document module dependency."""

    def sync_documents(
        self, request: SyncDocumentsRequest, context: RequestContext
    ) -> SyncDocumentsResponse: ...

    def get_status_sync_doc(
        self, ingestion_job_id: str, context: RequestContext
    ) -> SyncDocumentsResponse: ...


class SyncDocumentModuleRuntime:
    """Route-compatible module provider backed by real sync services."""

    def __init__(self) -> None:
        self._impl = SyncDocumentModuleImpl(
            document_service=DocumentService(),
            gemini_ocr_service=GeminiOCRService(),
            database_service=DatabaseSyncService(),
            vector_db_service=VectorDBService(),
        )

    def sync_documents(
        self, request: SyncDocumentsRequest, context: RequestContext
    ) -> SyncDocumentsResponse:
        return self._impl.sync_documents(request=request, context=context)

    def get_status_sync_doc(
        self, ingestion_job_id: str, context: RequestContext
    ) -> SyncDocumentsResponse:
        return self._impl.get_status_sync_doc(
            ingestion_job_id=ingestion_job_id,
            context=context,
        )


class SyncDataHandler:
    """Handler for sync-data operations with strict body parsing."""

    def __init__(
        self,
        execution_id: str,
        sync_document_module: SyncDocumentModuleProtocol,
    ) -> None:
        self.execution_id = execution_id
        self.sync_document_module = sync_document_module

    def handle_sync_data(
        self,
        body: SyncDocumentsRequest | str | dict,
        context: RequestContext,
    ) -> SyncDocumentsResponse:
        logger.info(
            "Start sync handle: execution_id=%s, trace_id=%s",
            self.execution_id,
            context.trace_id,
        )
        try:
            match body:
                case SyncDocumentsRequest():
                    request = body
                case str():
                    request = SyncDocumentsRequest.model_validate_json(body)
                case dict():
                    request = SyncDocumentsRequest.model_validate(body)
                case _:
                    raise DomainError(
                        code="BAD_REQUEST",
                        message="Invalid request body format.",
                    )
        except DomainError:
            raise
        except Exception as exc:
            raise DomainError(
                code="BAD_REQUEST",
                message=f"Invalid request body format: {exc}",
            ) from exc

        try:
            return self.sync_document_module.sync_documents(request, context)
        except Exception as exc:
            logger.error(
                "Error during document syncing process: execution_id=%s error=%s",
                self.execution_id,
                exc,
            )
            raise map_exception_to_domain_error(exc) from exc

    def handle_get_sync_data_status(
        self,
        params: dict[str, str],
    ) -> SyncDocumentsResponse:
        ingestion_job_id = params.get("ingestion_job_id")
        if not ingestion_job_id:
            raise DomainError(
                code="BAD_REQUEST",
                message="ingestion_job_id is required",
            )

        try:
            context = RequestContext(trace_id=self.execution_id)
            return self.sync_document_module.get_status_sync_doc(
                ingestion_job_id=ingestion_job_id,
                context=context,
            )
        except DomainError:
            raise
        except Exception as exc:
            logger.error(
                "Error getting sync status: execution_id=%s error=%s",
                self.execution_id,
                exc,
            )
            raise map_exception_to_domain_error(exc) from exc
