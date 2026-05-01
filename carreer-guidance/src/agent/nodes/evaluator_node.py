from src.agent.state.agent_state import AgentRuntimeState

PASS_THRESHOLD = 0.65


def evaluate_draft(state: AgentRuntimeState) -> bool:
    notes: list[str] = []
    score = 1.0

    draft = state.draft_answer.strip()
    if len(draft) < 30:
        score -= 0.30
        notes.append("draft answer is too short")

    if state.plan in {"rag_only", "rag_web_parallel"}:
        rag_ok = bool(state.tool_results.get("rag", {}).get("success"))
        if not rag_ok:
            score -= 0.35
            notes.append("rag tool failed")

    if state.plan in {"web_only", "rag_web_parallel"}:
        web_payload = state.tool_results.get("web", {})
        web_ok = bool(web_payload.get("success"))
        if not web_ok:
            score -= 0.35
            notes.append("web tool failed")
        elif not list(web_payload.get("sources") or []):
            score -= 0.15
            notes.append("web tool returned no sources")

    if not state.sources and state.plan != "direct_answer":
        score -= 0.10
        notes.append("no sources attached")

    if state.plan == "rag_web_parallel":
        rag_ok = bool(state.tool_results.get("rag", {}).get("success"))
        web_ok = bool(state.tool_results.get("web", {}).get("success"))
        if not rag_ok and not web_ok:
            score = 0.0
            notes.append("both rag and web failed")

    state.evaluation_score = max(0.0, score)
    state.evaluation_notes = notes

    passed = state.evaluation_score >= PASS_THRESHOLD
    if passed and draft:
        state.answer = draft
    return passed
