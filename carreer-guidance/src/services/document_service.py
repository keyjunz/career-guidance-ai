"""Document service for archive preparation and chunking."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from src.services.gemini.ocr_service import OCRDocumentResult


@dataclass(slots=True)
class PreparedDocument:
    source_url: str
    file_path: str
    document_name: str
    document_type: str


class DocumentService:
    """Service for document preparation and chunking."""

    def prepare_documents(
        self,
        file_urls: list[str],
        download_dir: str | None,
    ) -> list[PreparedDocument]:
        base_dir = (download_dir or "downloads").rstrip("/\\")
        prepared: list[PreparedDocument] = []

        for url in file_urls:
            parsed = urlparse(url)
            filename = parsed.path.rsplit("/", 1)[-1] or "document.bin"
            extension = (
                filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
            )
            prepared.append(
                PreparedDocument(
                    source_url=url,
                    file_path=f"{base_dir}/{filename}",
                    document_name=filename,
                    document_type=extension,
                )
            )
        return prepared

    def chunk_documents(
        self, ocr_results: list[OCRDocumentResult]
    ) -> list[dict[str, str]]:
        chunks: list[dict[str, str]] = []
        for result in ocr_results:
            if not result.success:
                continue
            text = result.text.strip()
            if not text:
                continue
            chunks.append(
                {
                    "source_url": result.source_url,
                    "file_path": result.file_path,
                    "chunk_text": text,
                }
            )
        return chunks
