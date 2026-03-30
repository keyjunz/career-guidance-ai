import logging
from typing import Any, Awaitable, Callable

from src.services.redis_service.main import RedisQueueService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ChatWorkerService:
    """Consume async chat requests and process them sequentially."""

    def __init__(self, execution_id: str, queue_name: str = "chat:requests") -> None:
        self.execution_id = execution_id
        self.redis_queue = RedisQueueService(
            execution_id=execution_id,
            queue_name=queue_name,
        )

    async def run_once(
        self,
        processor: Callable[[dict[str, Any]], Awaitable[Any] | Any],
    ) -> bool:
        payload = await self.redis_queue.dequeue(timeout=1)
        if payload is None:
            return False

        try:
            result = processor(payload)
            if hasattr(result, "__await__"):
                await result
            return True
        except Exception as exc:  # pragma: no cover
            logger.exception("Worker failed to process chat payload: %s", exc)
            return False

    async def run_forever(
        self,
        processor: Callable[[dict[str, Any]], Awaitable[Any] | Any],
    ) -> None:
        while True:
            await self.run_once(processor)
