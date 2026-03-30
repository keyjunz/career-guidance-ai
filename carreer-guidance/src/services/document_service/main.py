"""Document preparation and semantic chunking service."""


import logging
import os
import re
import tempfile
from pathlib import Path
from urllib import parse, request
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DocumentService:
    """Transform OCR text into semantically coherent chunks using embeddings."""

    def __init__(
        self,
        execution_id: str,
        embedding_service: Any | None = None,
        semantic_chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        similarity_threshold: float | None = None,
        max_chunk_size: int | None = None,
    ) -> None:
        self.execution_id = execution_id
        self.embedding_service = embedding_service

        # Load from environment or use defaults
        self.semantic_chunk_size = semantic_chunk_size or int(
            os.getenv("SEMANTIC_CHUNK_SIZE", "512")
        )
        self.chunk_overlap = chunk_overlap or int(
            os.getenv("SEMANTIC_CHUNK_OVERLAP", "100")
        )
        self.similarity_threshold = similarity_threshold or float(
            os.getenv("SEMANTIC_SIMILARITY_THRESHOLD", "0.5")
        )
        self.max_chunk_size = max_chunk_size or int(os.getenv("MAX_CHUNK_SIZE", "1024"))

    def prepare_documents(
        self,
        file_urls: list[str],
        download_dir: str | None,
    ) -> list[dict[str, str]]:
        target_dir = self._resolve_download_dir(download_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        prepared: list[dict[str, str]] = []
        for index, url in enumerate(file_urls, start=1):
            file_name = self._build_file_name(url=url, index=index)
            local_path = target_dir / file_name
            self._download_file(
                url=url,
                destination=local_path,
            )

            prepared.append(
                {
                    "source_url": url,
                    "file_path": str(local_path),
                    "file_name": local_path.name,
                    "file_extension": local_path.suffix.lower(),
                }
            )

        return prepared

    def chunk_documents(
        self,
        ocr_results: list[dict[str, str | bool | None]],
    ) -> list[dict]:
        """Split documents by page, then semantically chunk each page."""
        chunks: list[dict] = []

        for result in ocr_results:
            if not bool(result.get("success")):
                continue
            text = str(result.get("text") or "").strip()
            if not text:
                continue

            file_path = str(result.get("file_path") or "")
            pages = self._split_text_by_pages(text)
            total_chunks_for_file = 0

            for page_number, page_text in enumerate(pages, start=1):
                chunk_list = self._semantic_split_text(page_text)
                for idx, part in enumerate(chunk_list):
                    chunks.append(
                        {
                            "chunk_id": f"{Path(file_path).stem}:p{page_number}:{idx}",
                            "document_id": Path(file_path).name,
                            "text": part,
                            "metadata": {
                                "execution_id": self.execution_id,
                                "source_url": str(result.get("source_url") or ""),
                                "file_path": file_path,
                                "industry_type": str(result.get("industry_type") or ""),
                                "page_number": page_number,
                                "chunk_index": idx,
                            },
                        }
                    )
                total_chunks_for_file += len(chunk_list)

            logger.info(
                "document chunking done: execution_id=%s file_path=%s pages=%d chunks=%d text_length=%d industry_type=%s",
                self.execution_id,
                file_path,
                len(pages),
                total_chunks_for_file,
                len(text),
                str(result.get("industry_type") or ""),
            )

        return chunks

    def _semantic_split_text(self, text: str) -> list[str]:
        """Split text into semantically coherent chunks using sentence grouping."""
        compact = "\n".join(line.rstrip() for line in text.splitlines()).strip()
        if len(compact) <= self.semantic_chunk_size:
            return [compact]

        try:
            # Split text into sentences as basic units
            sentences = self._split_sentences(compact)
            if not sentences:
                return [compact]

            # Group sentences into chunks with semantic coherence
            chunks: list[str] = []
            current_chunk: list[str] = []
            current_length = 0

            for sentence in sentences:
                sentence_length = len(sentence)

                # If adding this sentence exceeds max size, finalize current chunk
                if current_length + sentence_length > self.max_chunk_size:
                    if current_chunk:
                        chunks.append(" ".join(current_chunk))
                        current_chunk = [sentence]
                        current_length = sentence_length
                    else:
                        # Single sentence exceeds max, split it
                        chunks.append(sentence[: self.max_chunk_size])
                        current_chunk = []
                        current_length = 0
                else:
                    current_chunk.append(sentence)
                    current_length += sentence_length + 1  # +1 for space

            # Add remaining chunk
            if current_chunk:
                chunks.append(" ".join(current_chunk))

            return chunks
        except Exception as exc:
            logger.warning(
                "Semantic splitting failed, returning full text chunk: %s", exc
            )
            return [compact]

    def _split_text_by_pages(self, text: str) -> list[str]:
        """Split OCR text into pages if page separators exist."""
        compact = text.replace("\r\n", "\n").strip()
        if not compact:
            return []

        # Common OCR page delimiters.
        separator_pattern = r"\f|\n\s*[-=]{2,}\s*page\s*\d+\s*[-=]{2,}\s*\n"
        parts = [
            part.strip()
            for part in re.split(separator_pattern, compact, flags=re.IGNORECASE)
            if part.strip()
        ]
        if parts:
            return parts
        return [compact]

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences at period/newline boundaries."""
        # Split by common sentence boundaries
        sentences = re.split(r"(?<=[.!?\n])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _resolve_download_dir(self, download_dir: str | None) -> Path:
        if download_dir:
            return Path(download_dir).expanduser().resolve()

        return Path(tempfile.gettempdir()) / "career_guidance_sync_docs"

    def _build_file_name(self, url: str, index: int) -> str:
        path = parse.urlparse(url).path
        raw_name = Path(path).name
        if raw_name:
            return raw_name
        return f"document_{index}.pdf"

    def _download_file(self, url: str, destination: Path) -> None:
        """Download file from URL to local destination."""
        req = request.Request(url, method="GET")
        try:
            with request.urlopen(req, timeout=120) as resp:
                destination.write_bytes(resp.read())
        except Exception as exc:
            logger.error(
                "Download failed: execution_id=%s url=%s error=%s",
                self.execution_id,
                url,
                exc,
            )
            raise ValueError(f"Failed to download file: {url}") from exc
