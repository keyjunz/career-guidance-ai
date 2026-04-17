import json
from threading import Lock
from typing import Any
from uuid import UUID

from src.agent.state.store_helpers import STORE_ROOT, normalize_question, utc_now


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
        self._data["updated_at"] = utc_now()
        self.path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

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

    def save_answer(
        self,
        execution_id: str,
        conversation_id: UUID,
        question: str,
        answer: str,
        *,
        sources: list[dict[str, Any]] | None = None,
        cache_hit: bool = False,
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
            self._data.setdefault("qa_cache", {})[normalized] = {
                "question": resolved_question,
                "answer": answer,
                "sources": sources or [],
                "conversation_id": str(conversation_id),
                "updated_at": utc_now(),
            }

            self._data.setdefault("history", []).append(
                {
                    "execution_id": execution_id,
                    "conversation_id": str(conversation_id),
                    "question": resolved_question,
                    "answer": answer,
                    "sources": sources or [],
                    "cache_hit": cache_hit,
                    "timestamp": utc_now(),
                }
            )
            self._save()
