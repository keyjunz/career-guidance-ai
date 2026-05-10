import json
import logging
import re
import socket
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.config.settings_models import get_settings
from src.prompts.web_search_prompts import (
    build_web_context_block,
    build_web_summary_question,
)
from src.services.llm_service import LLMService

DEFAULT_WEB_SEARCH_ENDPOINT = "https://api.firecrawl.dev/v1/search"
PLACEHOLDER_API_KEYS = {
    "your_firecrawl_api_key",
    "your_web_search_api_key",
    "change-me",
    "changeme",
}
IMAGE_MARKDOWN_PATTERN = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\((?P<url>https?://[^\s)]+)\)",
    flags=re.IGNORECASE,
)
VIETNAMESE_DIACRITIC_PATTERN = re.compile(r"[\u00C0-\u1EF9]")


class WebSearchService:
    def __init__(
        self,
        *,
        execution_id: str,
        endpoint: str | None = None,
        timeout_s: int | None = None,
        llm_service: LLMService | None = None,
    ) -> None:
        self.execution_id = execution_id
        self.endpoint = endpoint
        self.timeout_s = timeout_s
        self.logger = logging.getLogger(f"{__name__}[{execution_id}]")
        self.llm_service = llm_service or LLMService(
            execution_id=execution_id,
            api_key_env_override="GEMINI_AGENT_API_KEY",
        )

    def search(self, *, query: str, max_results: int = 5) -> dict[str, Any]:
        question = query.strip()
        if not question:
            raise ValueError("query is required for web search")

        settings = get_settings()
        api_key = str(settings.web_search.api_key).strip()
        if not api_key or api_key.lower() in PLACEHOLDER_API_KEYS:
            raise ValueError(
                "A valid Firecrawl API key is required. Configure FIRECRAWL_API_KEY "
                "or WEB_SEARCH_API_KEY in the backend .env file."
            )

        endpoint = (
            str(self.endpoint or "").strip()
            or str(settings.web_search.endpoint or "").strip()
            or DEFAULT_WEB_SEARCH_ENDPOINT
        )
        timeout_s = int(self.timeout_s or settings.web_search.timeout_s)
        limit = max(1, min(max_results, 10))

        payload = {
            "query": question,
            "limit": limit,
            "scrapeOptions": {
                "formats": ["markdown"],
                "onlyMainContent": True,
            },
        }

        request = Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "x-api-key": api_key,
            },
            method="POST",
        )

        start = time.perf_counter()
        body = self._fetch_json(request, timeout_s=timeout_s)
        latency_ms = (time.perf_counter() - start) * 1000
        if body.get("success") is False:
            raise RuntimeError(str(body.get("error") or "web search failed"))

        sources, crawl_texts = self._extract_sources(body)
        snippets = [
            str(source.get("snippet") or "").strip()
            for source in sources
            if str(source.get("snippet") or "").strip()
        ]
        images = self._extract_images(body, sources)

        summary = self._summarize_with_llm(question=question, crawl_texts=crawl_texts)
        if not summary and snippets:
            summary = " ".join(snippets[:3])

        return {
            "answer": summary,
            "snippets": snippets,
            "sources": sources,
            "images": images,
            "latency_ms": latency_ms,
        }

    def _fetch_json(self, request: Request, *, timeout_s: int) -> dict[str, Any]:
        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:
                with urlopen(request, timeout=timeout_s) as response:
                    raw = response.read().decode("utf-8")
                    return json.loads(raw)
            except HTTPError as exc:
                details = exc.read().decode("utf-8", errors="ignore")
                self.logger.warning("Web search HTTP error: %s", details)
                if exc.code in {401, 403}:
                    raise RuntimeError(
                        "web search authentication failed. Please verify "
                        "FIRECRAWL_API_KEY or WEB_SEARCH_API_KEY."
                    ) from exc
                raise RuntimeError(f"web search failed with status {exc.code}") from exc
            except (TimeoutError, socket.timeout) as exc:
                self.logger.warning(
                    "Web search timeout (attempt %d/%d): %s",
                    attempt,
                    max_attempts,
                    exc,
                )
                if attempt == max_attempts:
                    raise RuntimeError("web search timeout") from exc
                continue
            except URLError as exc:
                self.logger.warning("Web search network error: %s", exc)
                if attempt == max_attempts:
                    raise RuntimeError("web search network error") from exc
                continue
            except json.JSONDecodeError as exc:
                self.logger.warning("Web search returned invalid JSON")
                raise RuntimeError("web search returned invalid response") from exc

        raise RuntimeError("web search failed")

    def _extract_sources(
        self,
        payload: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[str]]:
        results = self._result_items(payload)
        if not results:
            return [], []

        normalized: list[dict[str, Any]] = []
        crawl_texts: list[str] = []
        for item in results:
            url = str(item.get("url") or "").strip()
            if not url:
                continue
            title = self._resolve_title(item, default=url)
            text_content = self._resolve_text_content(item)
            snippet = self._build_snippet(text_content)
            if text_content:
                crawl_texts.append(text_content)
            normalized.append(
                {
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                    "score": float(item.get("score") or 0.0),
                }
            )
        return normalized, crawl_texts

    def _extract_images(
        self,
        payload: dict[str, Any],
        sources: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        source_urls: set[str] = {
            str(source.get("url") or "").strip() for source in sources
        }

        unique_urls: set[str] = set()
        normalized: list[dict[str, Any]] = []

        top_level_images = payload.get("images")
        if isinstance(top_level_images, list):
            first_source_url = (
                str(sources[0].get("url") or "").strip() if sources else ""
            )
            for image_url in top_level_images:
                resolved_url = str(image_url or "").strip()
                if (
                    not resolved_url
                    or resolved_url in unique_urls
                    or resolved_url in source_urls
                ):
                    continue
                unique_urls.add(resolved_url)
                normalized.append(
                    {
                        "url": resolved_url,
                        "source_url": first_source_url,
                        "alt": "web image",
                    }
                )

        for item in self._result_items(payload):
            item_source_url = str(item.get("url") or "").strip()
            for image in self._extract_item_images(item):
                image_url = str(image.get("url") or "").strip()
                if (
                    not image_url
                    or image_url in unique_urls
                    or image_url in source_urls
                ):
                    continue
                unique_urls.add(image_url)
                normalized.append(
                    {
                        "url": image_url,
                        "source_url": item_source_url,
                        "alt": str(image.get("alt") or "web image").strip()
                        or "web image",
                    }
                )

        return normalized

    def _result_items(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        for key in ("data", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return []

    def _resolve_title(self, item: dict[str, Any], *, default: str) -> str:
        title = str(item.get("title") or "").strip()
        if title:
            return title

        metadata = item.get("metadata")
        if isinstance(metadata, dict):
            for key in ("title", "ogTitle"):
                candidate = str(metadata.get(key) or "").strip()
                if candidate:
                    return candidate

        return default

    def _resolve_text_content(self, item: dict[str, Any]) -> str:
        for key in ("markdown", "content", "description", "snippet", "text"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        metadata = item.get("metadata")
        if isinstance(metadata, dict):
            for key in ("description", "ogDescription"):
                candidate = metadata.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()

        return ""

    def _build_snippet(self, text: str, *, max_chars: int = 400) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= max_chars:
            return normalized
        return f"{normalized[:max_chars].rstrip()}..."

    def _extract_item_images(self, item: dict[str, Any]) -> list[dict[str, str]]:
        metadata = (
            item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        )
        markdown = str(item.get("markdown") or "")

        candidates: list[dict[str, str]] = []
        for key in ("ogImage", "image", "thumbnail", "twitter:image"):
            url = str(metadata.get(key) or "").strip()
            if url:
                candidates.append({"url": url, "alt": "web image"})

        metadata_images = metadata.get("images")
        if isinstance(metadata_images, list):
            for image_url in metadata_images:
                url = str(image_url or "").strip()
                if url:
                    candidates.append({"url": url, "alt": "web image"})
        elif isinstance(metadata_images, str) and metadata_images.strip():
            candidates.append({"url": metadata_images.strip(), "alt": "web image"})

        for match in IMAGE_MARKDOWN_PATTERN.finditer(markdown):
            url = str(match.group("url") or "").strip()
            if not url:
                continue
            alt = str(match.group("alt") or "").strip() or "web image"
            candidates.append({"url": url, "alt": alt})

        deduped: list[dict[str, str]] = []
        seen: set[str] = set()
        for image in candidates:
            image_url = str(image.get("url") or "").strip()
            if not image_url or image_url in seen:
                continue
            seen.add(image_url)
            deduped.append(image)
        return deduped

    def _summarize_with_llm(self, *, question: str, crawl_texts: list[str]) -> str:
        if not crawl_texts:
            return ""

        summary_language = self._resolve_summary_language(question)

        selected_contexts: list[str] = []
        current_chars = 0
        max_chars = 7500

        for raw_text in crawl_texts:
            cleaned = " ".join(str(raw_text or "").split())
            if not cleaned:
                continue

            piece = cleaned[:1500]
            if current_chars + len(piece) > max_chars:
                break
            selected_contexts.append(piece)
            current_chars += len(piece)

        if not selected_contexts:
            return ""

        context = "\n\n".join(
            build_web_context_block(
                index=index + 1,
                content=chunk,
                language=summary_language,
            )
            for index, chunk in enumerate(selected_contexts)
        )
        summary_question = build_web_summary_question(
            question,
            language=summary_language,
        )

        try:
            result = self.llm_service.generate(
                question=summary_question,
                context=context,
                language=summary_language,
                max_tokens=500,
                temperature=0.2,
            )
            answer = str(result.get("answer") or "").strip()
            if answer and not answer.startswith("[API Error]"):
                return answer
        except Exception as exc:
            self.logger.warning("Web summary generation failed: %s", exc)

        return ""

    def _resolve_summary_language(self, question: str) -> str:
        if VIETNAMESE_DIACRITIC_PATTERN.search(str(question or "")):
            return "vi"
        return "en"
