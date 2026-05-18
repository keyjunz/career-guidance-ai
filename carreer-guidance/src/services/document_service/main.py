import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any
from urllib import parse, request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TEXT_LABELS = {
    "paragraph_title",
    "text",
    "number",
    "abstract",
    "content",
    "reference",
    "doc_title",
    "footnote",
    "header",
    "algorithm",
    "footer",
    "aside_text",
    "reference_content",
}
IMAGE_LABELS = {"image", "chart", "table"}


class DocumentService:
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

            pages = result.get("pages")
            if isinstance(pages, list) and pages:
                chunks.extend(self._chunk_layout_pages(result))
                continue

            text = str(result.get("text") or "").strip()
            if not text:
                continue

            file_path = str(result.get("file_path") or "")
            doc_id = str(result.get("doc_id") or Path(file_path).name)
            pages = self._split_text_by_pages(text)
            total_chunks_for_file = 0

            for page_number, page_text in enumerate(pages, start=1):
                chunk_list = self._semantic_split_text(page_text)
                for idx, part in enumerate(chunk_list):
                    chunks.append(
                        {
                            "chunk_id": f"{doc_id}:p{page_number}:{idx}",
                            "document_id": Path(file_path).name,
                            "text": part,
                            "metadata": {
                                "execution_id": self.execution_id,
                                "source_url": str(result.get("source_url") or ""),
                                "file_path": file_path,
                                "source": file_path,
                                "title": Path(file_path).name,
                                "industry_type": str(result.get("industry_type") or ""),
                                "page_number": page_number,
                                "chunk_index": idx,
                                "doc_id": doc_id,
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

    def _chunk_layout_pages(self, result: dict[str, Any]) -> list[dict]:
        chunks: list[dict] = []
        file_path = str(result.get("file_path") or "")
        source_url = str(result.get("source_url") or "")
        industry_type = str(result.get("industry_type") or "")
        doc_id = str(result.get("doc_id") or Path(file_path).stem)

        pages = result.get("pages") or []
        text_blocks = self._collect_text_blocks(pages)
        image_blocks = self._collect_image_blocks(pages)
        image_links = self._link_images_to_text(image_blocks, text_blocks)

        current_blocks: list[dict[str, Any]] = []
        current_text_parts: list[str] = []
        current_length = 0
        chunk_index = 0
        overlap_chars = max(0, int(self.chunk_overlap or 0))

        def _build_overlap_blocks(
            blocks: list[dict[str, Any]],
        ) -> list[dict[str, Any]]:
            if not blocks or overlap_chars <= 0:
                return []
            overlap: list[dict[str, Any]] = []
            char_count = 0
            for block in reversed(blocks):
                text = str(block.get("text") or "").strip()
                if not text:
                    continue
                overlap.insert(0, block)
                char_count += len(text) + 1
                if char_count >= overlap_chars:
                    break
            return overlap

        for block in text_blocks:
            text = str(block.get("text") or "").strip()
            if not text:
                continue

            projected = current_length + len(text) + (1 if current_text_parts else 0)
            if current_text_parts and projected > self.max_chunk_size:
                chunk = self._build_layout_chunk(
                    doc_id=doc_id,
                    file_path=file_path,
                    source_url=source_url,
                    industry_type=industry_type,
                    chunk_index=chunk_index,
                    text_blocks=current_blocks,
                    image_links=image_links,
                )
                chunks.append(chunk)
                chunk_index += 1
                overlap_blocks = _build_overlap_blocks(current_blocks)
                current_blocks = overlap_blocks
                current_text_parts = [
                    str(block.get("text") or "").strip()
                    for block in current_blocks
                    if str(block.get("text") or "").strip()
                ]
                current_length = sum(len(s) for s in current_text_parts) + max(
                    len(current_text_parts) - 1, 0
                )
                if current_length > self.max_chunk_size:
                    current_blocks = []
                    current_text_parts = []
                    current_length = 0

            current_blocks.append(block)
            current_text_parts.append(text)
            current_length += len(text) + (1 if current_text_parts else 0)

        if current_blocks:
            chunk = self._build_layout_chunk(
                doc_id=doc_id,
                file_path=file_path,
                source_url=source_url,
                industry_type=industry_type,
                chunk_index=chunk_index,
                text_blocks=current_blocks,
                image_links=image_links,
            )
            chunks.append(chunk)

        logger.info(
            "layout chunking done: execution_id=%s file_path=%s pages=%d chunks=%d",
            self.execution_id,
            file_path,
            len(pages),
            len(chunks),
        )
        return chunks

    def _build_layout_chunk(
        self,
        *,
        doc_id: str,
        file_path: str,
        source_url: str,
        industry_type: str,
        chunk_index: int,
        text_blocks: list[dict[str, Any]],
        image_links: dict[str, dict[str, Any]],
    ) -> dict:
        page_number = int(text_blocks[0].get("page_number") or 1)
        chunk_text = "\n".join(
            str(block.get("text") or "").strip() for block in text_blocks
        ).strip()

        linked_images = self._collect_linked_images(text_blocks, image_links)
        image_paths = []
        image_ids = []
        image_bboxes = []

        for image in linked_images:
            image_id = str(image.get("image_id") or "")
            image_path = str(image.get("image_path") or "")
            if not image_path:
                continue
            image_paths.append(image_path)
            if image_id:
                image_ids.append(image_id)
            image_bboxes.append(image.get("bbox"))

        metadata: dict[str, Any] = {
            "execution_id": self.execution_id,
            "source_url": source_url,
            "file_path": file_path,
            "source": file_path,
            "title": Path(file_path).name,
            "industry_type": industry_type,
            "page_number": page_number,
            "chunk_index": chunk_index,
            "doc_id": doc_id,
            "has_image": bool(image_paths),
        }

        if image_paths:
            metadata.update(
                {
                    "image_paths": image_paths,
                    "image_ids": image_ids,
                    "image_bboxes": image_bboxes,
                }
            )

        return {
            "chunk_id": f"{doc_id}:p{page_number}:{chunk_index}",
            "document_id": Path(file_path).name,
            "text": chunk_text,
            "metadata": metadata,
        }

    def _collect_text_blocks(self, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        for page in pages:
            for block in page.get("blocks", []):
                if str(block.get("type") or "") in TEXT_LABELS:
                    blocks.append(block)
        blocks.sort(
            key=lambda b: (
                b.get("page_number", 0),
                (b.get("bbox") or [0, 0, 0, 0])[1],
                (b.get("bbox") or [0, 0, 0, 0])[0],
            )
        )
        return blocks

    def _collect_image_blocks(
        self, pages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        for page in pages:
            for block in page.get("blocks", []):
                if str(block.get("type") or "") in IMAGE_LABELS:
                    blocks.append(block)
        return blocks

    def _link_images_to_text(
        self,
        image_blocks: list[dict[str, Any]],
        text_blocks: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        links: dict[str, dict[str, Any]] = {}
        for image in image_blocks:
            image_id = str(image.get("image_id") or "")
            if not image_id:
                continue
            best = self._nearest_block(image, text_blocks)
            if best is None:
                continue
            links[image_id] = {
                "image_id": image_id,
                "image_path": image.get("image_path"),
                "bbox": image.get("bbox"),
                "linked_text": best.get("text"),
                "linked_block_id": best.get("block_id"),
            }
        return links

    def _collect_linked_images(
        self,
        text_blocks: list[dict[str, Any]],
        image_links: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        linked: list[dict[str, Any]] = []
        block_ids = {block.get("block_id") for block in text_blocks}
        for image in image_links.values():
            if image.get("linked_block_id") in block_ids:
                linked.append(image)
        return linked

    def _nearest_block(
        self,
        image_block: dict[str, Any],
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        if not candidates:
            return None
        image_bbox = image_block.get("bbox") or [0, 0, 0, 0]
        best = None
        best_distance = None
        for block in candidates:
            if block.get("page_number") != image_block.get("page_number"):
                continue
            distance = self._bbox_distance(
                image_bbox, block.get("bbox") or [0, 0, 0, 0]
            )
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best = block
        return best

    def _bbox_distance(self, bbox_a: list[int], bbox_b: list[int]) -> float:
        ax = (bbox_a[0] + bbox_a[2]) / 2
        ay = (bbox_a[1] + bbox_a[3]) / 2
        bx = (bbox_b[0] + bbox_b[2]) / 2
        by = (bbox_b[1] + bbox_b[3]) / 2
        return abs(ax - bx) + abs(ay - by)

    def count_pages(self, text: str, file_path: str | None = None) -> int:
        """Count pages, preferring direct PDF file analysis when possible."""
        file_pages = self._count_pages_from_pdf_file(file_path)
        if file_pages > 0:
            return file_pages
        return len(self._split_text_by_pages(text))

    def _count_pages_from_pdf_file(self, file_path: str | None) -> int:
        """Best-effort PDF page count without external dependencies."""
        if not file_path:
            return 0

        path = Path(file_path)
        if path.suffix.lower() != ".pdf" or not path.exists():
            return 0

        try:
            data = path.read_bytes()
            if not data.startswith(b"%PDF"):
                return 0

            # Common PDFs expose one '/Type /Page' per page object.
            page_objects = re.findall(rb"/Type\s*/Page(?!s)", data)
            if page_objects:
                return len(page_objects)

            # Fallback: page tree can carry '/Count N'.
            counts = [int(m) for m in re.findall(rb"/Count\s+(\d+)", data)]
            if counts:
                return max(counts)
        except Exception as exc:
            logger.warning(
                "count pages from pdf failed: execution_id=%s file_path=%s error=%s",
                self.execution_id,
                file_path,
                exc,
            )

        return 0

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
            overlap_chars = max(0, int(self.chunk_overlap or 0))

            def _build_overlap(prev_chunk: list[str]) -> list[str]:
                if not prev_chunk or overlap_chars <= 0:
                    return []
                overlap: list[str] = []
                char_count = 0
                for sentence in reversed(prev_chunk):
                    overlap.insert(0, sentence)
                    char_count += len(sentence) + 1
                    if char_count >= overlap_chars:
                        break
                return overlap

            for sentence in sentences:
                sentence_length = len(sentence)

                # If adding this sentence exceeds max size, finalize current chunk
                if current_length + sentence_length > self.max_chunk_size:
                    if current_chunk:
                        chunks.append(" ".join(current_chunk))
                        overlap = _build_overlap(current_chunk)
                        current_chunk = overlap + [sentence]
                        current_length = sum(len(s) for s in current_chunk) + max(
                            len(current_chunk) - 1, 0
                        )
                        if current_length > self.max_chunk_size:
                            current_chunk = [sentence[: self.max_chunk_size]]
                            current_length = len(current_chunk[0])
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
