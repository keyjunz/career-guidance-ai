import logging
from typing import Any
from uuid import UUID

from src.modules.sync_doc_module.main import SyncDocumentModuleImpl
from src.request_body.sync_doc import SyncDocumentsRequest, SyncDocumentsResponse

RequestContext = dict[str, Any]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SyncDataHandler:
    def __init__(
        self,
        execution_id: str,
    ) -> None:
        self.execution_id = execution_id
        self.sync_document_module = SyncDocumentModuleImpl(
            execution_id=self.execution_id
        )

    def process_uploaded_files(
        self,
        file_paths: list[str],
        user_id: UUID,
        context: RequestContext,
        industry_type: str | None = None,
    ) -> SyncDocumentsResponse:
        """Process uploaded files by converting to SyncDocumentsRequest."""
        logger.info(
            "Start processing uploaded files: execution_id=%s, context_execution_id=%s, files=%d",
            self.execution_id,
            context.get("execution_id"),
            len(file_paths),
        )
        try:
            # Create request from file paths
            request = SyncDocumentsRequest(
                user_id=user_id,
                file_urls=file_paths,
                download_dir=None,
                industry_type=industry_type,
            )

            # Process using sync_documents
            return self.sync_document_module.sync_documents(
                request=request,
                context=context,
            )
        except ValueError:
            raise
        except Exception as exc:
            logger.error(
                "Error processing uploaded files: execution_id=%s error=%s",
                self.execution_id,
                exc,
            )
            if isinstance(exc, ValueError):
                raise
            raise RuntimeError("Internal server error") from exc

    def get_sync_status(
        self,
        ingestion_job_id: str,
        context: RequestContext,
    ) -> SyncDocumentsResponse:
        """Fetch current sync status for a specific ingestion job."""
        logger.info(
            "Get sync status: execution_id=%s, context_execution_id=%s, job_id=%s",
            self.execution_id,
            context.get("execution_id"),
            ingestion_job_id,
        )
        try:
            return self.sync_document_module.get_status_sync_doc(
                ingestion_job_id=ingestion_job_id,
                context=context,
            )
        except ValueError:
            raise
        except Exception as exc:
            logger.error(
                "Error getting sync status: execution_id=%s, job_id=%s, error=%s",
                self.execution_id,
                ingestion_job_id,
                exc,
            )
            if isinstance(exc, ValueError):
                raise
            raise RuntimeError("Internal server error") from exc
