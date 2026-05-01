from typing import Any

from src.modules.web_search_module import WebSearchModuleImpl


class WebTool:
    def __init__(self, *, execution_id: str, user_id: str) -> None:
        if not execution_id.strip():
            raise ValueError("execution_id is required for web tool")
        if not user_id.strip():
            raise ValueError("user_id is required for web tool")

        self.execution_id = execution_id
        self.user_id = user_id
        self.module = WebSearchModuleImpl(execution_id=execution_id)

    def run(self, question: str) -> dict[str, Any]:
        if not question.strip():
            raise ValueError("question is required for web tool")

        result = self.module.query(question, max_results=5)
        return {
            "answer": str(result.get("answer") or "").strip(),
            "snippets": list(result.get("snippets") or []),
            "sources": list(result.get("sources") or []),
            "images": list(result.get("images") or []),
            "latency_ms": float(result.get("latency_ms") or 0.0),
        }
