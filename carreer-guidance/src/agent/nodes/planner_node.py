from src.agent.state.agent_state import AgentRuntimeState

DIRECT_ANSWER_HINTS = (
    "xin chao",
    "hello",
    "hi",
    "thanks",
    "cam on",
)

WEB_HINTS = (
    "latest",
    "news",
    "update",
    "today",
    "trend",
    "nguon",
    "source",
    "link",
    "website",
    "web",
    "tham khao",
)

RAG_HINTS = (
    "noi bo",
    "tai lieu",
    "knowledge base",
    "career guidance",
    "ho so",
    "cv",
    "resume",
    "lo trinh",
)

COMBINED_HINTS = (
    "ket hop",
    "doi chieu",
    "so sanh",
    "compare",
    "tong hop",
    "both",
)

IMAGE_HINTS = (
    "image",
    "anh",
    "hinh",
    "photo",
    "infographic",
)


def _contains_any(text: str, hints: tuple[str, ...]) -> bool:
    return any(hint in text for hint in hints)


def choose_plan(state: AgentRuntimeState) -> str:
    question = state.question.strip().lower()

    if question in DIRECT_ANSWER_HINTS:
        state.plan = "direct_answer"
        return state.plan

    wants_web = _contains_any(question, WEB_HINTS)
    wants_rag = _contains_any(question, RAG_HINTS)
    wants_combined = _contains_any(question, COMBINED_HINTS)
    wants_image = _contains_any(question, IMAGE_HINTS)

    if wants_combined or (wants_web and wants_rag):
        state.plan = "rag_web_parallel"
    elif wants_web:
        state.plan = "web_only"
    else:
        state.plan = "rag_only"

    if wants_image and state.plan == "rag_only":
        state.plan = "rag_web_parallel"

    return state.plan
