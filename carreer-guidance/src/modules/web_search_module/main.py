from typing import Any

from src.services.web_search_service import WebSearchService


class WebSearchModuleImpl:
    def __init__(
        self,
        *,
        execution_id: str,
        web_search_service: WebSearchService | None = None,
    ) -> None:
        self.execution_id = execution_id
        self.web_search_service = web_search_service or WebSearchService(
            execution_id=execution_id
        )

    def query(self, question: str, *, max_results: int = 5) -> dict[str, Any]:
        return self.web_search_service.search(query=question, max_results=max_results)
