"""Document preparation and chunking service."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from urllib import parse, request

logger = logging.getLogger(__name__)


class DocumentService:
    """Download source files and transform OCR text into chunks."""

    def __init__(
        self,
        execution_id: str,
        chunk_size: int = 1500,
        overlap: int = 200,
    ) -> None:
        self.execution_id = execution_id
        self.chunk_size = max(chunk_size, 200)
        self.overlap = max(min(overlap, self.chunk_size // 2), 0)

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
        chunks: list[dict] = []
        for result in ocr_results:
            if not bool(result.get("success")):
                continue
            text = str(result.get("text") or "").strip()
            if not text:
                continue

            parts = self._split_text(text)
            for idx, part in enumerate(parts):
                file_path = str(result.get("file_path") or "")
                chunks.append(
                    {
                        "chunk_id": f"{Path(file_path).stem}:{idx}",
                        "document_id": Path(file_path).name,
                        "text": part,
                        "metadata": {
                            "execution_id": self.execution_id,
                            "source_url": str(result.get("source_url") or ""),
                            "file_path": file_path,
                            "chunk_index": idx,
                        },
                    }
                )

        return chunks

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
        req = request.Request(url, method="GET")
        try:
            with request.urlopen(req, timeout=120) as resp:
                destination.write_bytes(resp.read())
        except Exception as exc:
            logger.error(
                "Download file failed: execution_id=%s url=%s error=%s",
                self.execution_id,
                url,
                exc,
            )
            raise ValueError(f"Failed to download file: {url}") from exc

    def _split_text(self, text: str) -> list[str]:
        compact = "\n".join(line.rstrip() for line in text.splitlines()).strip()
        if len(compact) <= self.chunk_size:
            return [compact]

        chunks: list[str] = []
        start = 0
        text_length = len(compact)
        while start < text_length:
            end = min(start + self.chunk_size, text_length)
            chunks.append(compact[start:end])
            if end == text_length:
                break
            start = max(end - self.overlap, start + 1)

        return chunks
