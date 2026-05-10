import hashlib
import logging
import os
from pathlib import Path
from typing import Any

import fitz
import numpy as np
from PIL import Image
from paddleocr import PPStructure, PaddleOCR

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
CAPTION_LABELS = {"figure_title"}
IMAGE_LABELS = {"image", "chart", "table"}


class PaddleOCRService:
    """Extract layout-aware text using PP-DocLayout + PP-OCRv5 rec."""

    def __init__(
        self,
        execution_id: str,
        layout_model_dir: str | None = None,
        rec_model_dir: str | None = None,
        image_storage_dir: str | None = None,
        pdf_zoom: float | None = None,
        pdf_render_dpi: int | None = None,
        layout_score_threshold: float | None = None,
        use_gpu: bool | None = None,
    ) -> None:
        self.execution_id = execution_id
        self.pdf_zoom = pdf_zoom or float(os.getenv("PDF_RENDER_ZOOM", "1.5"))
        self.pdf_render_dpi = pdf_render_dpi or int(os.getenv("PDF_RENDER_DPI", "200"))
        self.layout_score_threshold = layout_score_threshold or float(
            os.getenv("LAYOUT_SCORE_THRESHOLD", "0.5")
        )
        self.use_gpu = bool(
            str(os.getenv("PADDLE_USE_GPU", "false")).strip().lower() == "true"
        )
        if use_gpu is not None:
            self.use_gpu = use_gpu

        self.layout_model_dir = Path(
            layout_model_dir
            or os.getenv("PADDLE_LAYOUT_MODEL_DIR")
            or self._default_layout_model_dir()
        ).expanduser()
        self.rec_model_dir = Path(
            rec_model_dir
            or os.getenv("PADDLE_REC_MODEL_DIR")
            or self._default_rec_model_dir()
        ).expanduser()
        self.image_storage_dir = self._resolve_image_dir(image_storage_dir)

        if not self.layout_model_dir.exists():
            raise FileNotFoundError(
                f"Layout model dir not found: {self.layout_model_dir}"
            )
        if not self.rec_model_dir.exists():
            raise FileNotFoundError(f"Rec model dir not found: {self.rec_model_dir}")

        self.layout_engine = PPStructure(
            layout=True,
            show_log=False,
            layout_score_threshold=self.layout_score_threshold,
            layout_model_dir=str(self.layout_model_dir),
        )
        self.rec_engine = PaddleOCR(
            det=False,
            rec=True,
            cls=False,
            use_angle_cls=False,
            show_log=False,
            use_gpu=self.use_gpu,
            rec_model_dir=str(self.rec_model_dir),
        )

    def extract_text_batch(
        self,
        documents: list[dict[str, str]],
    ) -> list[dict[str, str | bool | None | list[dict[str, Any]]]]:
        results: list[dict[str, str | bool | None | list[dict[str, Any]]]] = []
        for item in documents:
            source_url = item.get("source_url", "")
            file_path = item.get("file_path", "")
            try:
                payload = self._extract_single_document(file_path=file_path)
                payload.update(
                    {
                        "source_url": source_url,
                        "file_path": file_path,
                        "success": True,
                        "error": None,
                    }
                )
                results.append(payload)
            except Exception as exc:
                logger.error(
                    "Paddle OCR failed: execution_id=%s source_url=%s error=%s",
                    self.execution_id,
                    source_url,
                    exc,
                )
                results.append(
                    {
                        "source_url": source_url,
                        "file_path": file_path,
                        "text": "",
                        "pages": [],
                        "success": False,
                        "error": str(exc),
                    }
                )
        return results

    def _extract_single_document(self, file_path: str) -> dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        doc_id = self._build_doc_id(path)
        if path.suffix.lower() == ".pdf":
            pages = self._extract_from_pdf(path, doc_id)
        else:
            image = Image.open(path).convert("RGB")
            pages = [self._extract_from_image(image, 1, doc_id)]

        text_parts = []
        for page in pages:
            for block in page.get("blocks", []):
                if block.get("type") in TEXT_LABELS and block.get("text"):
                    text_parts.append(str(block.get("text")))
                if block.get("type") in CAPTION_LABELS and block.get("text"):
                    text_parts.append(str(block.get("text")))

        return {
            "doc_id": doc_id,
            "text": "\n".join(text_parts).strip(),
            "pages": pages,
        }

    def _extract_from_pdf(self, path: Path, doc_id: str) -> list[dict[str, Any]]:
        pages: list[dict[str, Any]] = []
        with fitz.open(path) as doc:
            for page_index in range(doc.page_count):
                page = doc.load_page(page_index)
                page_number = page_index + 1
                image_blocks = self._extract_image_objects(
                    page=page,
                    doc=doc,
                    doc_id=doc_id,
                    page_number=page_number,
                )
                text = page.get_text("text").strip()

                # Rule-based fast path only when PDF has extractable text.
                # If page is image-only (scanned), fall back to layout+OCR.
                if image_blocks and text:
                    text_block = self._build_text_block(page, page_number, text)
                    blocks = image_blocks
                    if text_block:
                        blocks.append(text_block)
                    pages.append(
                        {
                            "page_number": page_number,
                            "width": float(page.rect.width),
                            "height": float(page.rect.height),
                            "blocks": blocks,
                        }
                    )
                    continue

                image = self._render_page_image(page)
                pages.append(self._extract_from_image(image, page_number, doc_id))
        return pages

    def _render_page_image(self, page: fitz.Page) -> Image.Image:
        scale = max(self.pdf_render_dpi / 72.0, 0.1)
        matrix = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    def _build_text_block(
        self, page: fitz.Page, page_number: int, text: str
    ) -> dict[str, Any] | None:
        if not text:
            return None

        rect = page.rect
        return {
            "block_id": f"p{page_number}-b000",
            "type": "text",
            "bbox": [
                int(rect.x0),
                int(rect.y0),
                int(rect.x1),
                int(rect.y1),
            ],
            "score": 1.0,
            "page_number": page_number,
            "text": text,
        }

    def _extract_image_objects(
        self,
        *,
        page: fitz.Page,
        doc: fitz.Document,
        doc_id: str,
        page_number: int,
    ) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        image_infos = page.get_image_info(xrefs=True) or []
        bbox_by_xref: dict[int, list[int]] = {}
        for info in image_infos:
            xref = int(info.get("xref") or 0)
            bbox = info.get("bbox")
            if xref and bbox and len(bbox) == 4:
                bbox_by_xref[xref] = [int(b) for b in bbox]

        image_index = 0
        for img in page.get_images(full=True):
            if not img:
                continue
            xref = int(img[0])
            extracted = doc.extract_image(xref)
            if not extracted:
                continue
            image_bytes = extracted.get("image")
            ext = str(extracted.get("ext") or "png").lower()
            if not image_bytes:
                continue

            image_index += 1
            image_path = self._save_raw_image(
                image_bytes=image_bytes,
                extension=ext,
                doc_id=doc_id,
                page_number=page_number,
                image_index=image_index,
            )

            block = {
                "block_id": f"p{page_number}-img{image_index:03d}",
                "type": "image",
                "bbox": bbox_by_xref.get(xref) or [0, 0, 0, 0],
                "score": 1.0,
                "page_number": page_number,
                "image_path": image_path,
                "image_id": f"{doc_id}-p{page_number}-img{image_index:03d}",
            }
            blocks.append(block)

        return blocks

    def _save_raw_image(
        self,
        *,
        image_bytes: bytes,
        extension: str,
        doc_id: str,
        page_number: int,
        image_index: int,
    ) -> str:
        target_dir = self.image_storage_dir / doc_id / f"p{page_number}"
        target_dir.mkdir(parents=True, exist_ok=True)
        safe_ext = extension if extension.isalnum() else "png"
        image_name = f"img{image_index:03d}.{safe_ext}"
        image_path = target_dir / image_name
        image_path.write_bytes(image_bytes)
        return str(image_path)

    def _extract_from_image(
        self,
        image: Image.Image,
        page_number: int,
        doc_id: str,
    ) -> dict[str, Any]:
        layout_results = self.layout_engine(np.array(image))
        blocks: list[dict[str, Any]] = []
        image_index = 0

        block_index = 0
        for item in layout_results or []:
            label = str(item.get("type") or item.get("label") or "").strip()
            bbox = item.get("bbox") or item.get("box") or item.get("points")
            if not label or not bbox:
                continue

            normalized_bbox = self._normalize_bbox(bbox, image.width, image.height)
            if not normalized_bbox:
                continue

            block_index += 1
            block: dict[str, Any] = {
                "block_id": f"p{page_number}-b{block_index:03d}",
                "type": label,
                "bbox": normalized_bbox,
                "score": float(item.get("score") or 0.0),
                "page_number": page_number,
            }

            if label in TEXT_LABELS or label in CAPTION_LABELS:
                crop = image.crop(tuple(normalized_bbox))
                text = self._recognize_text(crop)
                block["text"] = text
            elif label in IMAGE_LABELS:
                crop = image.crop(tuple(normalized_bbox))
                image_index += 1
                image_path = self._save_image(crop, doc_id, page_number, image_index)
                block["image_path"] = image_path
                block["image_id"] = f"{doc_id}-p{page_number}-img{image_index:03d}"

            blocks.append(block)

        return {
            "page_number": page_number,
            "width": image.width,
            "height": image.height,
            "blocks": blocks,
        }

    def _recognize_text(self, image: Image.Image) -> str:
        img = np.array(image)
        result = self.rec_engine.ocr(img, det=False, rec=True, cls=False)
        return self._parse_rec_result(result)

    def _parse_rec_result(self, result: Any) -> str:
        if not result:
            return ""

        if isinstance(result, list):
            for item in result:
                if isinstance(item, list) and item:
                    first = item[0]
                    if isinstance(first, (list, tuple)) and first:
                        return str(first[0]).strip()
                    if isinstance(first, str):
                        return first.strip()
                if isinstance(item, (list, tuple)) and item:
                    return str(item[0]).strip()
                if isinstance(item, str):
                    return item.strip()
        return ""

    def _save_image(
        self,
        image: Image.Image,
        doc_id: str,
        page_number: int,
        image_index: int,
    ) -> str:
        target_dir = self.image_storage_dir / doc_id / f"p{page_number}"
        target_dir.mkdir(parents=True, exist_ok=True)
        image_name = f"img{image_index:03d}.png"
        image_path = target_dir / image_name
        image.save(image_path, format="PNG")
        return str(image_path)

    def _normalize_bbox(self, bbox: Any, width: int, height: int) -> list[int] | None:
        if not bbox:
            return None

        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            x1, y1, x2, y2 = bbox
        elif isinstance(bbox, (list, tuple)) and len(bbox) >= 2:
            xs = [point[0] for point in bbox if isinstance(point, (list, tuple))]
            ys = [point[1] for point in bbox if isinstance(point, (list, tuple))]
            if not xs or not ys:
                return None
            x1, x2 = min(xs), max(xs)
            y1, y2 = min(ys), max(ys)
        else:
            return None

        x1 = max(int(x1), 0)
        y1 = max(int(y1), 0)
        x2 = min(int(x2), width)
        y2 = min(int(y2), height)
        if x2 <= x1 or y2 <= y1:
            return None
        return [x1, y1, x2, y2]

    def _build_doc_id(self, path: Path) -> str:
        digest = hashlib.md5(str(path).encode("utf-8")).hexdigest()[:8]
        return f"{path.stem}-{digest}"

    def _resolve_image_dir(self, image_storage_dir: str | None) -> Path:
        if image_storage_dir:
            base = Path(image_storage_dir)
        else:
            base = Path(os.getenv("IMAGE_STORAGE_DIR", "database/images"))

        if base.is_absolute():
            return base

        base_dir = Path(__file__).resolve().parents[3]
        return (base_dir / base).resolve()

    def _default_layout_model_dir(self) -> str:
        base_dir = Path(__file__).resolve().parents[3]
        return str(base_dir / "src" / "model_ml" / "PP-DocLayout_plus-L_infer")

    def _default_rec_model_dir(self) -> str:
        base_dir = Path(__file__).resolve().parents[3]
        return str(base_dir / "src" / "model_ml" / "PP-OCRv5_server_rec_infer")
