"""Prompts module."""

from src.prompts.ocr_prompt import OCR_EXTRACT_PROMPT
from src.prompts.rag_prompts import RAG_PROMPT_TEMPLATE, RAG_PROMPT_TEMPLATE_VI
from src.prompts.translation_prompts import build_vi_to_en_translation_prompt
from src.prompts.web_search_prompts import (
    build_web_context_block,
    build_web_summary_question,
)

__all__ = [
    "OCR_EXTRACT_PROMPT",
    "RAG_PROMPT_TEMPLATE",
    "RAG_PROMPT_TEMPLATE_VI",
    "build_vi_to_en_translation_prompt",
    "build_web_summary_question",
    "build_web_context_block",
]
