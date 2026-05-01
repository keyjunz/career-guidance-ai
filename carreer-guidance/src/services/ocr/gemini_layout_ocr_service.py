import json
import logging
import os
from pathlib import Path
from typing import Any
import hashlib

import fitz
from PIL import Image
import google.generativeai as genai

from src.prompts.ocr_prompt import GEMINI_LAYOUT_OCR_PROMPT

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TEXT_LABELS = {"text"}
IMAGE_LABELS = {"image"}


class GeminiLayoutOCRService:
    """Extract layout-aware blocks using Gemini Vision (text + image)."""

    def __init__(
        self,
        execution_id: str,
        model_name: str | None = None,
        api_key: str | None = None,
        image_storage_dir: str | None = None,
        pdf_zoom: float | None = None,
        max_pages: int | None = None,
        timeout_s: int | None = None,
    ) -> None:
        self.execution_id = execution_id
        self.model_name = model_name or os.getenv("GEMINI_MODEL_NAME", "").strip()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
        self.pdf_zoom = pdf_zoom or float(os.getenv("PDF_RENDER_ZOOM", "1.5"))
        self.max_pages = max_pages or int(os.getenv("GEMINI_OCR_MAX_PAGES", "0"))
        self.timeout_s = timeout_s or int(os.getenv("GEMINI_OCR_TIMEOUT", "120"))
        self.image_storage_dir = self._resolve_image_dir(image_storage_dir)

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required for Gemini OCR")
        if not self.model_name:
            raise ValueError("GEMINI_MODEL_NAME is required for Gemini OCR")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

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
                    "Gemini layout OCR failed: execution_id=%s source_url=%s error=%s",
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

        text_parts: list[str] = []
        for page in pages:
            for block in page.get("blocks", []):
                if block.get("type") in TEXT_LABELS and block.get("text"):
                    text_parts.append(str(block.get("text")))

        return {
            "doc_id": doc_id,
            "text": "\n".join(text_parts).strip(),
            "pages": pages,
        }

    def _extract_from_pdf(self, path: Path, doc_id: str) -> list[dict[str, Any]]:
        pages: list[dict[str, Any]] = []
        with fitz.open(path) as doc:
            page_count = doc.page_count
            if self.max_pages > 0:
                page_count = min(page_count, self.max_pages)
            for page_index in range(page_count):
                page = doc.load_page(page_index)
                matrix = fitz.Matrix(self.pdf_zoom, self.pdf_zoom)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                pages.append(self._extract_from_image(image, page_index + 1, doc_id))
        return pages

    def _extract_from_image(
        self,
        image: Image.Image,
        page_number: int,
        doc_id: str,
    ) -> dict[str, Any]:
        layout_blocks = self._extract_layout_blocks(image)
        blocks: list[dict[str, Any]] = []
        image_index = 0

        block_index = 0
        for item in layout_blocks:
            label = str(item.get("type") or "").strip().lower() or "text"
            if label not in TEXT_LABELS and label not in IMAGE_LABELS:
                label = "text"

            bbox = item.get("bbox") or item.get("box") or item.get("points")
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

            if label in TEXT_LABELS:
                text = str(item.get("text") or "").strip()
                if not text:
                    continue
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

    def _extract_layout_blocks(self, image: Image.Image) -> list[dict[str, Any]]:
        prompt = (
            f"{GEMINI_LAYOUT_OCR_PROMPT}\n\nIMAGE_SIZE: {image.width}x{image.height}"
        )
        response_text = self._call_gemini(prompt, image)
        payload = self._parse_json_payload(response_text)
        if isinstance(payload, dict):
            blocks = payload.get("blocks")
            if isinstance(blocks, list):
                return [
                    self._normalize_block(item)
                    for item in blocks
                    if isinstance(item, dict)
                ]
        if isinstance(payload, list):
            return [
                self._normalize_block(item)
                for item in payload
                if isinstance(item, dict)
            ]
        return []

    def _call_gemini(self, prompt: str, image: Image.Image) -> str:
        try:
            response = self.model.generate_content(
                [prompt, image],
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 2048,
                },
                request_options={"timeout": self.timeout_s},
            )
            return str(response.text or "").strip()
        except Exception as exc:
            raise RuntimeError(f"Gemini OCR request failed: {exc}") from exc

    def _normalize_block(self, item: dict[str, Any]) -> dict[str, Any]:
        label = (
            str(
                item.get("type")
                or item.get("label")
                or item.get("kind")
                or item.get("category")
                or "text"
            )
            .strip()
            .lower()
        )
        if label in {"figure", "photo", "diagram", "chart", "table", "image"}:
            label = "image"
        elif label != "image":
            label = "text"

        return {
            "type": label,
            "bbox": item.get("bbox")
            or item.get("box")
            or item.get("bounding_box")
            or item.get("points"),
            "text": item.get("text") or item.get("content") or "",
            "score": item.get("score") or item.get("confidence") or 0.0,
        }

    def _parse_json_payload(self, raw_text: str) -> Any:
        text = str(raw_text or "").strip()
        if not text:
            return {}

        if text.startswith("```"):
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1].strip()

        for start_char, end_char in (("{", "}"), ("[", "]")):
            start = text.find(start_char)
            end = text.rfind(end_char)
            if start != -1 and end != -1 and end > start:
                snippet = text[start : end + 1]
                try:
                    return json.loads(snippet)
                except json.JSONDecodeError:
                    continue

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

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
