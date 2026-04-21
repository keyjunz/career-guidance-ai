import json
from typing import Any

from src.config.settings_models import get_settings


class RedisQueueService:
    """Enqueue async chat payloads into Redis list."""

    def __init__(self, execution_id: str, queue_name: str = "chat:requests") -> None:
        self.execution_id = execution_id
        self.queue_name = queue_name

    def _redis_client(self):
        try:
            import redis.asyncio as redis  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "redis package is required for async chat queue"
            ) from exc

        cfg = get_settings().redis
        redis_url = cfg.redis_url.strip()
        if not redis_url:
            raise RuntimeError("REDIS_URL is empty")
        if "<PASSWORD>" in redis_url or "YOUR_PASSWORD" in redis_url:
            raise RuntimeError(
                "REDIS_URL contains placeholder password. Please set your real Redis Cloud password."
            )

        client_kwargs: dict[str, Any] = {
            "decode_responses": True,
            "socket_connect_timeout": max(float(cfg.redis_connect_timeout_sec), 1.0),
            "socket_timeout": max(float(cfg.redis_socket_timeout_sec), 1.0),
            "health_check_interval": max(int(cfg.redis_health_check_interval_sec), 0),
            "retry_on_timeout": True,
        }

        if redis_url.startswith("rediss://"):
            ssl_mode = str(cfg.redis_ssl_cert_reqs or "required").strip().lower()
            if ssl_mode not in {"required", "optional", "none"}:
                ssl_mode = "required"
            # redis-py expects ssl_cert_reqs in string mode for from_url(rediss://...)
            client_kwargs["ssl_cert_reqs"] = ssl_mode

        return redis.from_url(redis_url, **client_kwargs)

    def _format_redis_error(self, exc: Exception) -> str:
        message = str(exc)
        redis_url = get_settings().redis.redis_url.strip().lower()
        if "wrong_version_number" in message.lower() and redis_url.startswith(
            "rediss://"
        ):
            return (
                f"{message}. REDIS_URL may be using rediss:// while endpoint expects non-TLS. "
                "Try redis:// for this Redis Cloud database."
            )
        return message

    async def enqueue(self, payload: dict[str, Any]) -> None:
        client = self._redis_client()
        try:
            await client.rpush(self.queue_name, json.dumps(payload))
        except Exception as exc:
            raise RuntimeError(
                f"Failed to enqueue chat payload to Redis: {self._format_redis_error(exc)}"
            ) from exc
        finally:
            await client.aclose()

    async def dequeue(self, timeout: int = 1) -> dict[str, Any] | None:
        client = self._redis_client()
        try:
            item = await client.blpop(self.queue_name, timeout=timeout)
            if item is None:
                return None

            _, payload = item
            return json.loads(payload)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to dequeue chat payload from Redis: {self._format_redis_error(exc)}"
            ) from exc
        finally:
            await client.aclose()
