"""LLM service — API-based text generation (Groq / Gemini).

Wraps LLM API clients. Reusable across modules (RAG, Agent, etc.).
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ─── Config ─────────────────────────────────────────────────────
MAX_ANSWER_WORDS = 500

RAG_PROMPT_TEMPLATE = """You are an expert AI/Computer Science assistant. Answer the question using ONLY the provided context. If the context doesn't contain enough information, say so honestly. Keep your answer concise (under 500 words), accurate, and well-structured.

### Context:
{context}

### Question:
{question}

### Answer:"""

RAG_PROMPT_TEMPLATE_VI = """Bạn là trợ lý chuyên gia AI/Khoa học Máy tính. Trả lời câu hỏi CHỈ dựa trên ngữ cảnh được cung cấp. Nếu ngữ cảnh không chứa đủ thông tin, hãy nói rõ điều đó. Giữ câu trả lời ngắn gọn (dưới 500 từ), chính xác và có cấu trúc rõ ràng.

### Ngữ cảnh:
{context}

### Câu hỏi:
{question}

### Trả lời:"""

API_LLM_MODELS = {
    "groq-llama3-70b": {
        "provider": "groq",
        "name": "llama-3.3-70b-versatile",
        "api_key_env": "GROQ_API_KEY",
        "max_tokens": 1024,
        "temperature": 0.3,
    },
    "groq-llama3-8b": {
        "provider": "groq",
        "name": "llama-3.1-8b-instant",
        "api_key_env": "GROQ_API_KEY",
        "max_tokens": 1024,
        "temperature": 0.3,
    },
    "gemini-flash": {
        "provider": "gemini",
        "name": "gemini-2.0-flash",
        "api_key_env": "GEMINI_API_KEY",
        "max_tokens": 1024,
        "temperature": 0.3,
    },
}

DEFAULT_API_LLM = "groq-llama3-70b"


class LLMService:
    """LLM service using API (Groq / Gemini). No GPU needed."""

    def __init__(self, model_key: str | None = None):
        self.model_key = model_key or DEFAULT_API_LLM
        self.model_config = API_LLM_MODELS[self.model_key]
        self.provider = self.model_config["provider"]
        self.model_name = self.model_config["name"]
        self.max_tokens = self.model_config["max_tokens"]
        self.temperature = self.model_config["temperature"]

        self.client: Any = None
        self._loaded = False

        self.api_key = os.getenv(self.model_config["api_key_env"], "")
        if not self.api_key:
            logger.warning(
                "%s not set! Set it in .env or environment.",
                self.model_config["api_key_env"],
            )

    def load(self) -> None:
        """Initialize API client."""
        if self._loaded:
            return

        if self.provider == "groq":
            from groq import Groq
            self.client = Groq(api_key=self.api_key)
            logger.info("Groq client ready — model: %s", self.model_name)

        elif self.provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model_name)
            logger.info("Gemini client ready — model: %s", self.model_name)

        self._loaded = True

    def generate(
        self,
        question: str,
        context: str,
        language: str = "en",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict:
        """Generate RAG answer via API."""
        if not self._loaded:
            self.load()

        template = RAG_PROMPT_TEMPLATE_VI if language == "vi" else RAG_PROMPT_TEMPLATE
        prompt = template.format(context=context, question=question)

        max_tok = max_tokens or self.max_tokens
        temp = temperature or self.temperature

        start = time.perf_counter()
        max_retries = 3
        retry_delay = 1.5
        answer = ""
        tokens_gen = 0

        for attempt in range(max_retries):
            try:
                if self.provider == "groq":
                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=max_tok,
                        temperature=temp,
                    )
                    answer = response.choices[0].message.content
                    tokens_gen = (
                        response.usage.completion_tokens
                        if response.usage
                        else len(answer.split())
                    )
                elif self.provider == "gemini":
                    response = self.client.generate_content(
                        prompt,
                        generation_config={
                            "max_output_tokens": max_tok,
                            "temperature": temp,
                        },
                    )
                    answer = response.text
                    tokens_gen = len(answer.split())
                break
            except Exception as e:
                logger.warning("API call failed (%d/%d): %s", attempt + 1, max_retries, e)
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    answer = f"[API Error] Failed after {max_retries} retries: {e}"
                    tokens_gen = 0

        latency = (time.perf_counter() - start) * 1000
        words = answer.split()
        if len(words) > MAX_ANSWER_WORDS:
            answer = " ".join(words[:MAX_ANSWER_WORDS]) + "..."

        return {
            "answer": answer.strip(),
            "latency_ms": latency,
            "tokens_generated": tokens_gen,
            "tokens_per_second": tokens_gen / (latency / 1000) if latency > 0 else 0,
            "provider": self.provider,
            "model": self.model_name,
        }

    def translate_query(self, query: str, language: str = "en") -> str:
        """Translate Vietnamese query to English for better retrieval."""
        if language != "vi":
            return query
        if not self._loaded:
            self.load()

        prompt = (
            "Translate the following Vietnamese question to American English accurately. "
            "Return ONLY the English translation, without any quotes, explanations, "
            "or Markdown formatting.\n\n"
            f"Vietnamese: {query}\nEnglish:"
        )
        start = time.perf_counter()
        try:
            if self.provider == "groq":
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=60,
                    temperature=0.1,
                )
                eng_query = response.choices[0].message.content
            elif self.provider == "gemini":
                response = self.client.generate_content(
                    prompt,
                    generation_config={"max_output_tokens": 60, "temperature": 0.1},
                )
                eng_query = response.text
            else:
                return query

            eng_query = eng_query.strip(" '\"\n`")
            elapsed = (time.perf_counter() - start) * 1000
            logger.info("Translated VI→EN: '%s' → '%s' (%.0fms)", query, eng_query, elapsed)
            return eng_query
        except Exception as e:
            logger.warning("Translation failed: %s. Using original.", e)
            return query

    def unload(self) -> None:
        self.client = None
        self._loaded = False
