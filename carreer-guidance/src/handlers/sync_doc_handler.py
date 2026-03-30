"""Sync-document handler that orchestrates ingestion module calls."""


import logging
from typing import Any

from src.modules.sync_doc_module.main import SyncDocumentModuleImpl
from src.request_body.sync_doc import SyncDocumentsRequest, SyncDocumentsResponse

RequestContext = dict[str, Any]

logger = logging.getLogger(__name__)


class SyncDataHandler:
    """Handler for sync-data operations with strict body parsing."""

    def __init__(
        self,
        execution_id: str,
    ) -> None:
        self.execution_id = execution_id
        self.sync_document_module = SyncDocumentModuleImpl(
            execution_id=self.execution_id
        )

    def handle_sync_data(
        self,
        body: SyncDocumentsRequest | str | dict,
        context: RequestContext,
    ) -> SyncDocumentsResponse:
        logger.info(
            "Start sync handle: execution_id=%s, trace_id=%s",
            self.execution_id,
            context.get("trace_id"),
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
                    raise ValueError("Invalid request body format.")
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"Invalid request body format: {exc}") from exc

        try:
            return self.sync_document_module.sync_documents(request, context)
        except Exception as exc:
            logger.error(
                "Error during document syncing process: execution_id=%s error=%s",
                self.execution_id,
                exc,
            )
            if isinstance(exc, ValueError):
                raise
            raise RuntimeError("Internal server error") from exc

    def handle_get_sync_data_status(
        self,
        params: dict[str, str],
    ) -> SyncDocumentsResponse:
        ingestion_job_id = params.get("ingestion_job_id")
        if not ingestion_job_id:
            raise ValueError("ingestion_job_id is required")

        try:
            context: RequestContext = {"trace_id": self.execution_id}
            return self.sync_document_module.get_status_sync_doc(
                ingestion_job_id=ingestion_job_id,
                context=context,
            )
        except ValueError:
            raise
        except Exception as exc:
            logger.error(
                "Error getting sync status: execution_id=%s error=%s",
                self.execution_id,
                exc,
            )
            raise RuntimeError("Internal server error") from exc
