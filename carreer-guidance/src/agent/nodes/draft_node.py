from typing import Any

from src.agent.state.agent_state import AgentRuntimeState


def _collect_sources(state: AgentRuntimeState) -> list[dict[str, Any]]:
    rag_sources = list(state.tool_results.get("rag", {}).get("sources") or [])
    web_sources = list(state.tool_results.get("web", {}).get("sources") or [])
    merged = rag_sources + web_sources

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source in merged:
        if not isinstance(source, dict):
            continue
        key = str(
            source.get("url") or source.get("source") or source.get("title") or ""
        ).strip()
        if not key:
            key = f"source-{len(deduped) + 1}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(source)
    return deduped


def _pick_first_image_url(images: list[Any]) -> str | None:
    for image in images:
        if isinstance(image, dict):
            url = str(image.get("url") or "").strip()
        else:
            url = str(image or "").strip()
        if url:
            return url
    return None


def _collect_images(state: AgentRuntimeState) -> list[str]:
    urls: list[str] = []

    rag_payload = state.tool_results.get("rag", {})
    rag_url = _pick_first_image_url(list(rag_payload.get("images") or []))
    if rag_url:
        urls.append(rag_url)

    web_payload = state.tool_results.get("web", {})
    web_url = _pick_first_image_url(list(web_payload.get("images") or []))
    if web_url and web_url not in urls:
        urls.append(web_url)

    return urls[:2]


def _build_source_lines(sources: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for source in sources[:5]:
        url = str(source.get("url") or source.get("source") or "").strip()
        if not url:
            continue
        title = str(source.get("title") or "").strip()
        if title:
            lines.append(f"- {title}: {url}")
        else:
            lines.append(f"- {url}")
    return "\n".join(lines)


def compose_draft_answer(
    state: AgentRuntimeState,
    *,
    max_web_snippets: int = 3,
) -> str:
    if state.plan == "direct_answer":
        direct_answer = str(
            state.tool_results.get("direct", {}).get("answer") or ""
        ).strip()
        state.draft_answer = direct_answer
        state.answer = direct_answer
        state.sources = []
        state.image_urls = []
        return state.draft_answer

    rag_payload = state.tool_results.get("rag", {})
    web_payload = state.tool_results.get("web", {})

    sections: list[str] = []

    rag_answer = str(rag_payload.get("answer") or "").strip()
    if rag_payload.get("success") and rag_answer:
        sections.append(rag_answer)

    web_answer = str(web_payload.get("answer") or "").strip()
    if web_payload.get("success") and web_answer:
        sections.append(f"Web summary:\n{web_answer}")

    web_snippets = [
        str(item).strip()
        for item in list(web_payload.get("snippets") or [])
        if str(item).strip()
    ]
    if web_payload.get("success") and web_snippets:
        snippet_lines = "\n".join(
            f"- {snippet}" for snippet in web_snippets[:max_web_snippets]
        )
        sections.append(f"Web findings:\n{snippet_lines}")

    if not sections:
        errors: list[str] = []
        rag_error = str(rag_payload.get("error") or "").strip()
        web_error = str(web_payload.get("error") or "").strip()
        if rag_error:
            errors.append(f"RAG error: {rag_error}")
        if web_error:
            errors.append(f"Web error: {web_error}")

        fallback = "Khong tim thay du lieu phu hop de tra loi cau hoi nay."
        if errors:
            fallback = f"{fallback}\n\nChi tiet:\n- " + "\n- ".join(errors)
        sections.append(fallback)

    state.sources = _collect_sources(state)
    state.image_urls = _collect_images(state)

    source_lines = _build_source_lines(state.sources)
    if source_lines:
        sections.append(f"Sources:\n{source_lines}")

    state.draft_answer = "\n\n".join(
        section.strip() for section in sections if section.strip()
    )
    state.answer = state.draft_answer
    return state.draft_answer
