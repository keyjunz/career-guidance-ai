"""LLM service — API-based text generation (Groq / Gemini)."""

import logging
import os
import time
from typing import Any, Dict, Optional

from src.config.settings_models import get_settings
from src.prompts.rag_prompts import RAG_PROMPT_TEMPLATE, RAG_PROMPT_TEMPLATE_VI
from src.prompts.translation_prompts import build_vi_to_en_translation_prompt

MAX_ANSWER_WORDS = 500

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
        "api_key_env": "GEMINI_AGENT_API_KEY",
        "max_tokens": 1024,
        "temperature": 0.3,
    },
}
DEFAULT_API_LLM = "groq-llama3-70b"


class LLMService:
    """LLM service using API (Groq / Gemini). No GPU needed."""

    def __init__(
        self,
        *,
        execution_id: str,
        model_key: str | None = None,
        api_key_env_override: str | None = None,
    ):
        self.execution_id = execution_id
        self.logger = logging.getLogger(f"{__name__}[{execution_id}]")
        self.api_key_env_override = api_key_env_override

        requested_model_key = (
            model_key or os.getenv("LLM_MODEL_KEY") or DEFAULT_API_LLM
        ).strip()
        if requested_model_key not in API_LLM_MODELS:
            self.logger.warning(
                "Unknown LLM_MODEL_KEY='%s'. Falling back to '%s'.",
                requested_model_key,
                DEFAULT_API_LLM,
            )
            requested_model_key = DEFAULT_API_LLM

        self._apply_model_config(requested_model_key)

        self.client: Any = None
        self._loaded = False

        self.api_key = self._resolve_api_key_for_model(self.model_key)
        if not self.api_key:
            fallback_model = self._fallback_model_key(self.model_key)
            if fallback_model:
                self.logger.warning(
                    "%s not set. Falling back from '%s' to '%s'.",
                    self.model_config["api_key_env"],
                    self.model_key,
                    fallback_model,
                )
                self._apply_model_config(fallback_model)
                self.api_key = self._resolve_api_key_for_model(self.model_key)

        if not self.api_key:
            self.logger.warning(
                "%s not set! Set it in .env or environment.",
                self.model_config["api_key_env"],
            )

    def _apply_model_config(self, model_key: str) -> None:
        self.model_key = model_key
        self.model_config = API_LLM_MODELS[self.model_key]
        self.provider = self.model_config["provider"]
        self.model_name = self.model_config["name"]
        self.max_tokens = self.model_config["max_tokens"]
        self.temperature = self.model_config["temperature"]

        if self.provider == "gemini":
            gemini_model_name = os.getenv("GEMINI_MODEL_NAME", "").strip()
            if not gemini_model_name:
                try:
                    gemini_model_name = str(
                        get_settings().llm.gemini_model_name
                    ).strip()
                except Exception:
                    gemini_model_name = ""
            if gemini_model_name:
                self.model_name = gemini_model_name

    def _resolve_api_key_for_model(self, model_key: str) -> str:
        model_config = API_LLM_MODELS[model_key]
        if model_config["provider"] == "gemini":
            if self.api_key_env_override:
                override_key = os.getenv(self.api_key_env_override, "").strip()
                if override_key:
                    return override_key

            key = os.getenv(model_config["api_key_env"], "").strip()
            if key:
                return key
            try:
                settings_key = str(get_settings().llm.gemini_api_key).strip()
                if settings_key:
                    return settings_key
            except Exception:
                return ""

            fallback_key = os.getenv("GEMINI_API_KEY", "").strip()
            if fallback_key:
                return fallback_key

        key = os.getenv(model_config["api_key_env"], "").strip()
        if key:
            return key

        return ""

    def _fallback_model_key(self, current_model_key: str) -> str | None:
        if current_model_key != "gemini-flash" and self._resolve_api_key_for_model(
            "gemini-flash"
        ):
            return "gemini-flash"

        if current_model_key != "groq-llama3-70b" and self._resolve_api_key_for_model(
            "groq-llama3-70b"
        ):
            return "groq-llama3-70b"

        return None

    def load(self) -> None:
        if self._loaded:
            return
        if self.provider == "groq":
            from groq import Groq

            self.client = Groq(api_key=self.api_key)
            self.logger.info("Groq client ready — model: %s", self.model_name)
        elif self.provider == "gemini":
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model_name)
            self.logger.info("Gemini client ready — model: %s", self.model_name)
        self._loaded = True

    def generate(
        self,
        question: str,
        context: str,
        language: str = "en",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict:
        if not self._loaded:
            self.load()
        template = RAG_PROMPT_TEMPLATE_VI if language == "vi" else RAG_PROMPT_TEMPLATE
        prompt = template.format(context=context, question=question)
        max_tok = max_tokens or self.max_tokens
        temp = temperature or self.temperature
        start = time.perf_counter()
        max_retries, retry_delay, answer, tokens_gen = 3, 1.5, "", 0
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
                self.logger.warning(
                    "API call failed (%d/%d): %s", attempt + 1, max_retries, e
                )
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

    def generate_raw(
        self,
        prompt: str,
        *,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict:
        if not self._loaded:
            self.load()
        max_tok = max_tokens or self.max_tokens
        temp = temperature or self.temperature
        start = time.perf_counter()
        max_retries, retry_delay, answer, tokens_gen = 3, 1.5, "", 0
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
                self.logger.warning(
                    "API call failed (%d/%d): %s", attempt + 1, max_retries, e
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    answer = f"[API Error] Failed after {max_retries} retries: {e}"
                    tokens_gen = 0
        latency = (time.perf_counter() - start) * 1000
        return {
            "answer": str(answer or "").strip(),
            "latency_ms": latency,
            "tokens_generated": tokens_gen,
            "tokens_per_second": tokens_gen / (latency / 1000) if latency > 0 else 0,
            "provider": self.provider,
            "model": self.model_name,
        }

    def translate_query(self, query: str, language: str = "en") -> str:
        if language != "vi":
            return query
        if not self._loaded:
            self.load()
        prompt = build_vi_to_en_translation_prompt(query)
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
            self.logger.info(
                "Translated VI→EN: '%s' → '%s' (%.0fms)", query, eng_query, elapsed
            )
            return eng_query
        except Exception as e:
            self.logger.warning("Translation failed: %s. Using original.", e)
            return query

    def unload(self) -> None:
        self.client = None
        self._loaded = False
