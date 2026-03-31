from typing import Any

from src.services.redis_service.main import RedisQueueService


class DispatcherService:
    """Dispatch background jobs through Redis queue."""

    def __init__(self, execution_id: str) -> None:
        self.execution_id = execution_id
        self.redis_queue = RedisQueueService(execution_id=execution_id)

    async def dispatch_chat_request(self, payload: dict[str, Any]) -> None:
        await self.redis_queue.enqueue(payload)
