import json
from threading import Lock
from typing import Any
from uuid import UUID

from src.agent.state.store_helpers import STORE_ROOT, normalize_question, utc_now

MAX_HISTORY_ITEMS = 200
MAX_QA_CACHE_ITEMS = 200
MAX_STATUS_EXECUTIONS = 100
NON_CACHEABLE_ANSWER_MARKERS = (
    "no relevant data found",
    "không tìm thấy dữ liệu phù hợp",
    "i could not access the required data source",
    "hiện hệ thống chưa truy cập được nguồn dữ liệu phù hợp",
    "web search authentication failed",
    "cannot connect to chromadb",
    "quota exceeded",
)


class UserStore:
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.path = STORE_ROOT / f"{user_id}.json"
        self._lock = Lock()
        self._data = self._load()

    def _default_payload(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "pending_by_execution": {},
            "status_by_execution": {},
            "qa_cache": {},
            "history": [],
        }

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            payload = self._default_payload()
            self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
            return payload

        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            payload = self._default_payload()
            self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
            return payload

    def _save(self) -> None:
        self._prune()
        self._data["updated_at"] = utc_now()
        self.path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _prune(self) -> None:
        history = self._data.get("history")
        if isinstance(history, list) and len(history) > MAX_HISTORY_ITEMS:
            self._data["history"] = history[-MAX_HISTORY_ITEMS:]

        status_by_execution = self._data.get("status_by_execution")
        if (
            isinstance(status_by_execution, dict)
            and len(status_by_execution) > MAX_STATUS_EXECUTIONS
        ):
            items = list(status_by_execution.items())[-MAX_STATUS_EXECUTIONS:]
            self._data["status_by_execution"] = dict(items)

        cache = self._data.get("qa_cache")
        if isinstance(cache, dict):
            for key in list(cache.keys()):
                item = cache.get(key)
                answer = ""
                if isinstance(item, dict):
                    answer = str(item.get("answer") or "").lower()
                if not isinstance(item, dict) or any(
                    marker in answer for marker in NON_CACHEABLE_ANSWER_MARKERS
                ):
                    cache.pop(key, None)

            if len(cache) > MAX_QA_CACHE_ITEMS:
                sorted_items = sorted(
                    cache.items(),
                    key=lambda pair: (
                        str(pair[1].get("updated_at", ""))
                        if isinstance(pair[1], dict)
                        else ""
                    ),
                )
                self._data["qa_cache"] = dict(sorted_items[-MAX_QA_CACHE_ITEMS:])

    def append_status(self, execution_id: str, status: str) -> None:
        with self._lock:
            items = self._data.setdefault("status_by_execution", {}).setdefault(
                execution_id,
                [],
            )
            items.append(
                {
                    "status": status,
                    "timestamp": utc_now(),
                }
            )
            self._save()

    def get_status_texts(self, execution_id: str) -> list[str]:
        with self._lock:
            entries = self._data.get("status_by_execution", {}).get(execution_id, [])
            return [str(entry.get("status") or "") for entry in entries]

    def stage_question(
        self,
        execution_id: str,
        conversation_id: UUID,
        question: str,
    ) -> None:
        with self._lock:
            self._data.setdefault("pending_by_execution", {})[execution_id] = {
                "conversation_id": str(conversation_id),
                "question": question,
                "timestamp": utc_now(),
            }
            self._save()

    def get_cached_answer(self, question: str) -> dict[str, Any] | None:
        with self._lock:
            normalized = normalize_question(question)
            cache = self._data.setdefault("qa_cache", {})
            item = cache.get(normalized)
            if not isinstance(item, dict):
                return None
            return item

    def get_recent_history(
        self,
        *,
        conversation_id: str,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        with self._lock:
            history = list(self._data.get("history") or [])
        filtered = [
            item
            for item in history
            if str(item.get("conversation_id") or "") == str(conversation_id)
        ]
        return filtered[-limit:]

    def save_answer(
        self,
        execution_id: str,
        conversation_id: UUID,
        question: str,
        answer: str,
        *,
        sources: list[dict[str, Any]] | None = None,
        image_urls: list[str] | None = None,
        cache_hit: bool = False,
        cacheable: bool = True,
    ) -> None:
        with self._lock:
            pending = self._data.setdefault("pending_by_execution", {}).pop(
                execution_id,
                None,
            )
            resolved_question = (
                str(pending.get("question"))
                if isinstance(pending, dict) and pending.get("question")
                else question
            )

            normalized = normalize_question(resolved_question)
            normalized_answer = str(answer or "").strip().lower()
            should_cache = (
                cacheable
                and bool(normalized_answer)
                and not any(
                    marker in normalized_answer
                    for marker in NON_CACHEABLE_ANSWER_MARKERS
                )
            )
            if should_cache:
                self._data.setdefault("qa_cache", {})[normalized] = {
                    "question": resolved_question,
                    "answer": answer,
                    "sources": sources or [],
                    "image_urls": image_urls or [],
                    "conversation_id": str(conversation_id),
                    "updated_at": utc_now(),
                }
            else:
                self._data.setdefault("qa_cache", {}).pop(normalized, None)

            self._data.setdefault("history", []).append(
                {
                    "execution_id": execution_id,
                    "conversation_id": str(conversation_id),
                    "question": resolved_question,
                    "answer": answer,
                    "sources": sources or [],
                    "image_urls": image_urls or [],
                    "cache_hit": cache_hit,
                    "timestamp": utc_now(),
                }
            )
            self._save()
