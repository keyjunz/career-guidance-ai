from typing import Any

from src.agent.state.agent_state import AgentRuntimeState

FRIENDLY_TOOL_ERROR_EN = (
    "I could not access the required data source right now. "
    "Please try again later or switch to another chat mode."
)
FRIENDLY_TOOL_ERROR_VI = (
    "Hiện hệ thống chưa truy cập được nguồn dữ liệu phù hợp. "
    "Vui lòng thử lại sau hoặc chuyển sang chế độ chat khác."
)


def _looks_vietnamese(text: str) -> bool:
    normalized = str(text or "").lower()
    vi_markers = (
        "ă",
        "â",
        "đ",
        "ê",
        "ô",
        "ơ",
        "ư",
        "chào",
        "chao",
        "xin chao",
        "cảm ơn",
        "cam on",
        "nghề nghiệp",
        "tư vấn",
    )
    return any(marker in normalized for marker in vi_markers)


def _is_insufficient_answer(text: str) -> bool:
    normalized = str(text or "").strip().lower()
    if not normalized:
        return True
    weak_signals = (
        "provided context does not contain",
        "cannot answer your question",
        "no relevant data found",
        "context is insufficient",
        "i don't have enough information",
        "thieu thong tin",
        "thiếu thông tin",
        "khong tim thay",
        "không tìm thấy",
        "khong co thong tin",
        "không có thông tin",
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
    rag_payload = state.tool_results.get("rag", {})
    rag_url = _pick_first_image_url(list(rag_payload.get("images") or []))
    if rag_url:
        return [rag_url]

    web_payload = state.tool_results.get("web", {})
    web_url = _pick_first_image_url(list(web_payload.get("images") or []))
    if web_url:
        return [web_url]

    return []


def _collect_images_for_answer(
    state: AgentRuntimeState,
    answer_source: str,
) -> list[str]:
    if answer_source == "web":
        web_payload = state.tool_results.get("web", {})
        web_url = _pick_first_image_url(list(web_payload.get("images") or []))
        return [web_url] if web_url else []
    if answer_source == "rag":
        rag_payload = state.tool_results.get("rag", {})
        rag_url = _pick_first_image_url(list(rag_payload.get("images") or []))
        return [rag_url] if rag_url else []
    return []


def _dedupe_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source in sources:
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


def _compose_multi_intent_answer(state: AgentRuntimeState) -> str:
    sections: list[dict[str, Any]] = []
    all_sources: list[dict[str, Any]] = []
    all_images: list[str] = []

    for idx, sub in enumerate(state.sub_queries, 1):
        iid = str(sub.get("intent_id") or "").strip()
        bundle = state.tool_results_by_intent.get(iid) or {}
        title = str(sub.get("section_title") or f"Ý {idx}").strip()
        sub_q = str(sub.get("query") or "").strip()
        answer = str(bundle.get("answer") or "").strip()
        sources = list(bundle.get("sources") or [])
        all_sources.extend(sources)
        for img in list(bundle.get("images") or []):
            u = str(img).strip()
            if u and u not in all_images:
                all_images.append(u)

        sections.append(
            {
                "intent_id": iid,
                "intent_title": title,
                "query": sub_q,
                "answer": answer,
                "sources": sources,
            }
        )

    state.answer_sections = sections
    parts: list[str] = []
    for i, sec in enumerate(sections, 1):
        parts.append(f"## {i}. {sec['intent_title']}\n")
        parts.append(f"**Câu hỏi:** {sec['query']}\n")
        if sec["answer"]:
            parts.append(f"{sec['answer']}\n")
        else:
            parts.append(
                "_Không có phản hồi từ công cụ cho ý này._\n"
                if _looks_vietnamese(state.question)
                else "_No tool response for this part._\n"
            )
    merged = "\n".join(parts).strip()
    state.sources = _dedupe_sources(all_sources)
    state.image_urls = all_images[:3]
    state.draft_answer = merged
    state.answer = merged
    return merged


def compose_draft_answer(
    state: AgentRuntimeState,
) -> str:
    if state.plan == "multi_intent":
        return _compose_multi_intent_answer(state)

    if state.plan == "direct_answer":
        direct_answer = str(
            state.tool_results.get("direct", {}).get("answer") or ""
        ).strip()
        state.draft_answer = direct_answer
        state.answer = direct_answer
        state.sources = []
        state.image_urls = []
        state.answer_sections = []
        return state.draft_answer

    rag_payload = state.tool_results.get("rag", {})
    web_payload = state.tool_results.get("web", {})

    rag_answer = str(rag_payload.get("answer") or "").strip()
    web_answer = str(web_payload.get("answer") or "").strip()
    rag_sources = list(rag_payload.get("sources") or [])
    web_sources = list(web_payload.get("sources") or [])
    rag_ok = bool(rag_payload.get("success")) and not _is_insufficient_answer(
        rag_answer
    )
    web_ok = bool(web_payload.get("success")) and not _is_insufficient_answer(
        web_answer
    )
    rag_weak = (not rag_sources) and bool(web_sources)

    final_answer = ""
    answer_source = ""
    if rag_ok and web_ok:
        # Prefer web answer when rag is weak/insufficient; otherwise prefer rag.
        if _is_insufficient_answer(rag_answer) or rag_weak:
            final_answer = web_answer
            answer_source = "web"
        else:
            final_answer = rag_answer
            answer_source = "rag"
    elif rag_ok:
        final_answer = rag_answer
        answer_source = "rag"
    elif web_ok:
        final_answer = web_answer
        answer_source = "web"

    if not final_answer:
        if bool(rag_payload.get("success")) and rag_answer:
            final_answer = rag_answer
            answer_source = "rag"

    if not final_answer:
        errors: list[str] = []
        rag_error = str(rag_payload.get("error") or "").strip()
        web_error = str(web_payload.get("error") or "").strip()
        if rag_error:
            errors.append(f"RAG error: {rag_error}")
        if web_error:
            errors.append(f"Web error: {web_error}")

        if errors:
            state.has_tool_errors = True
            state.cacheable = False
            fallback = (
                FRIENDLY_TOOL_ERROR_VI
                if _looks_vietnamese(state.question)
                else FRIENDLY_TOOL_ERROR_EN
            )
        else:
            state.cacheable = False
            fallback = (
                "Không tìm thấy dữ liệu phù hợp để trả lời câu hỏi này."
                if _looks_vietnamese(state.question)
                else "No relevant data found to answer this question."
            )
        final_answer = fallback

    state.sources = _collect_sources(state)
    state.image_urls = (
        _collect_images_for_answer(state, answer_source)
        if answer_source
        else _collect_images(state)
    )

    state.draft_answer = final_answer.strip()
    state.answer = state.draft_answer
    return state.draft_answer
