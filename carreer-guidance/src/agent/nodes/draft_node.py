from typing import Any

from src.agent.state.agent_state import AgentRuntimeState


def _is_insufficient_answer(text: str) -> bool:
    normalized = str(text or "").strip().lower()
    if not normalized:
        return True
    weak_signals = (
        "provided context does not contain",
        "cannot answer your question",
        "khong tim thay",
        "không tìm thấy",
        "khong co thong tin",
        "không có thông tin",
        "context is insufficient",
    )
    return any(signal in normalized for signal in weak_signals)


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


def compose_draft_answer(
    state: AgentRuntimeState,
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

    rag_answer = str(rag_payload.get("answer") or "").strip()
    web_answer = str(web_payload.get("answer") or "").strip()
    rag_ok = bool(rag_payload.get("success")) and not _is_insufficient_answer(rag_answer)
    web_ok = bool(web_payload.get("success")) and not _is_insufficient_answer(web_answer)

    final_answer = ""
    if rag_ok and web_ok:
        # Prefer web answer when rag is weak/insufficient; otherwise prefer rag.
        final_answer = web_answer if _is_insufficient_answer(rag_answer) else rag_answer
    elif rag_ok:
        final_answer = rag_answer
    elif web_ok:
        final_answer = web_answer

    if not final_answer:
        if bool(rag_payload.get("success")) and rag_answer:
            final_answer = rag_answer

    if not final_answer:
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
        final_answer = fallback

    state.sources = _collect_sources(state)
    state.image_urls = _collect_images(state)

    state.draft_answer = final_answer.strip()
    state.answer = state.draft_answer
    return state.draft_answer
