"""Gemini service adapters."""

from src.services.gemini.ocr_service import GeminiOCRService, OCRDocumentResult

__all__ = [
    "GeminiOCRService",
    "OCRDocumentResult",
]
