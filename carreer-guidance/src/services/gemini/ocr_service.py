"""Gemini OCR service adapters."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class OCRDocumentResult:
    source_url: str
    file_path: str
    text: str
    success: bool
    error_message: str | None = None


class GeminiOCRService:
    """OCR service backed by Gemini.

    This is a service layer adapter. Replace the placeholder logic with
    real Gemini API integration in production.
    """

    def extract_text_batch(
        self, documents: list[dict[str, str]]
    ) -> list[OCRDocumentResult]:
        results: list[OCRDocumentResult] = []
        for doc in documents:
            file_path = doc.get("file_path", "")
            source_url = doc.get("source_url", "")
            # Placeholder output until Gemini API is wired.
            results.append(
                OCRDocumentResult(
                    source_url=source_url,
                    file_path=file_path,
                    text=f"[gemini-ocr-placeholder] extracted from {file_path}",
                    success=True,
                )
            )
        return results
