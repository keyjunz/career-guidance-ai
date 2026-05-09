import base64
import json
import logging
import mimetypes
import os
from pathlib import Path
from urllib import error, parse, request

from src.config.settings_models import get_settings
from src.prompts.ocr_prompt import OCR_EXTRACT_PROMPT

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class GeminiOCRService:
    """Extract plain text from documents using Gemini generateContent API."""

    def __init__(self, execution_id: str, timeout_seconds: int = 120) -> None:
        self.execution_id = execution_id
        self.timeout_seconds = timeout_seconds
        settings = get_settings()
        self.api_key = (
            os.getenv("GEMINI_OCR_API_KEY", "").strip()
            or str(settings.llm.gemini_api_key or "").strip()
            or os.getenv("GEMINI_API_KEY", "").strip()
        )
        self.model_name = settings.llm.gemini_model_name
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def extract_text_batch(
        self,
        documents: list[dict[str, str]],
    ) -> list[dict[str, str | bool | None]]:
        """Extract text from a list of documents.

        Expected input item keys: `source_url`, `file_path`.
        """

        results: list[dict[str, str | bool | None]] = []
        for item in documents:
            source_url = item.get("source_url", "")
            file_path = item.get("file_path", "")
            try:
                text = self._extract_single_document(
                    file_path=file_path,
                )
                results.append(
                    {
                        "source_url": source_url,
                        "file_path": file_path,
                        "text": text,
                        "success": True,
                        "error": None,
                    }
                )
            except Exception as exc:
                logger.error(
                    "Gemini OCR failed: execution_id=%s source_url=%s error=%s",
                    self.execution_id,
                    source_url,
                    exc,
                )
                results.append(
                    {
                        "source_url": source_url,
                        "file_path": file_path,
                        "text": "",
                        "success": False,
                        "error": str(exc),
                    }
                )
        return results

    def _extract_single_document(self, file_path: str) -> str:
        file_bytes = Path(file_path).read_bytes()
        encoded = base64.b64encode(file_bytes).decode("utf-8")
        mime_type = self._guess_mime_type(file_path)

        body = {
            "contents": [
                {
                    "parts": [
                        {"text": OCR_EXTRACT_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": encoded,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 8192,
            },
        }

        response_payload = self._post_generate_content(body)
        text = self._parse_response_text(response_payload)
        if not text.strip():
            raise ValueError("Gemini OCR returned empty text")
        return text

    def _post_generate_content(self, body: dict) -> dict:
        endpoint = (
            f"{self.base_url}/models/{parse.quote(self.model_name, safe='')}:generateContent"
            f"?key={parse.quote(self.api_key, safe='')}"
        )
        payload = json.dumps(body).encode("utf-8")
        req = request.Request(
            endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise ValueError(
                f"Gemini API HTTP {exc.code} for execution_id={self.execution_id}: {detail}"
            ) from exc
        except error.URLError as exc:
            raise ValueError(
                f"Gemini API connection error for execution_id={self.execution_id}: {exc.reason}"
            ) from exc

    def _parse_response_text(self, payload: dict) -> str:
        candidates = payload.get("candidates", [])
        if not candidates:
            raise ValueError("Gemini API returned no candidates")

        parts = candidates[0].get("content", {}).get("parts", [])
        texts = [part.get("text", "") for part in parts if isinstance(part, dict)]
        return "\n".join([item for item in texts if item]).strip()

    def _guess_mime_type(self, file_path: str) -> str:
        guessed, _ = mimetypes.guess_type(file_path)
        if guessed:
            return guessed

        suffix = Path(file_path).suffix.lower()
        if suffix == ".pdf":
            return "application/pdf"
        if suffix in {".jpg", ".jpeg"}:
            return "image/jpeg"
        if suffix == ".png":
            return "image/png"
        return "application/octet-stream"
