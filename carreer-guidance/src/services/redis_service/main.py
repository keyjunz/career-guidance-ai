"""Redis queue service for async chat dispatch."""


import json
from typing import Any

from src.config.settings import get_settings


class RedisQueueService:
    """Enqueue async chat payloads into Redis list."""

    def __init__(self, execution_id: str, queue_name: str = "chat:requests") -> None:
        self.execution_id = execution_id
        self.queue_name = queue_name

    async def enqueue(self, payload: dict[str, Any]) -> None:
        try:
            import redis.asyncio as redis  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "redis package is required for async chat queue"
            ) from exc

        redis_url = get_settings().redis.redis_url
        client = redis.from_url(redis_url, decode_responses=True)
        try:
            await client.rpush(self.queue_name, json.dumps(payload))
        finally:
            await client.aclose()

    async def dequeue(self, timeout: int = 1) -> dict[str, Any] | None:
        try:
            import redis.asyncio as redis  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "redis package is required for async chat queue"
            ) from exc

        redis_url = get_settings().redis.redis_url
        client = redis.from_url(redis_url, decode_responses=True)
        try:
            item = await client.blpop(self.queue_name, timeout=timeout)
            if item is None:
                return None

            _, payload = item
            return json.loads(payload)
        finally:
            await client.aclose()
