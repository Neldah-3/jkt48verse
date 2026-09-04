import time
from typing import Optional

from src.config import config


class _MemoryStore:
    """Tiny async key-value store with TTL — dev fallback ketika REDIS_URL=memory://.

    Hanya untuk development (satu proses). Produksi wajib Redis sungguhan.
    """

    def __init__(self) -> None:
        self._data: dict[str, tuple[str, Optional[float]]] = {}

    def _alive(self, key: str) -> Optional[str]:
        item = self._data.get(key)
        if item is None:
            return None
        value, expires_at = item
        if expires_at is not None and expires_at <= time.monotonic():
            self._data.pop(key, None)
            return None
        return value

    async def ping(self) -> bool:
        return True

    async def get(self, key: str) -> Optional[str]:
        return self._alive(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        expires_at = time.monotonic() + ex if ex else None
        self._data[key] = (value, expires_at)

    async def setex(self, key: str, seconds: int, value: str) -> None:
        await self.set(key, value, ex=seconds)

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self._data.pop(key, None)

    async def incr(self, key: str) -> int:
        value = int(self._alive(key) or 0) + 1
        self._data[key] = (str(value), None)
        return value

    async def expire(self, key: str, seconds: int) -> None:
        item = self._data.get(key)
        if item is not None:
            self._data[key] = (item[0], time.monotonic() + seconds)

    async def ttl(self, key: str) -> int:
        item = self._data.get(key)
        if item is None:
            return -2
        _, expires_at = item
        if expires_at is None:
            return -1
        return max(0, int(expires_at - time.monotonic()))

    async def aclose(self) -> None:  # pragma: no cover
        self._data.clear()


class RedisClient:
    def __init__(self):
        self.client = None
        self.logger = None
        self._memory = config.redis_url.startswith("memory://")

    async def connect(self):
        from src.logging_config import create_logger

        self.logger = create_logger("redis", __name__)
        if self._memory:
            self.client = _MemoryStore()
            self.logger.warning(
                "REDIS_URL=memory:// — memakai cache in-process (khusus development). "
                "Produksi wajib Redis sungguhan (mis. Upstash)."
            )
            return
        try:
            from redis.asyncio import Redis

            self.client = Redis.from_url(
                config.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            await self.client.ping()
            self.logger.info("Connected to Redis")
        except Exception as e:
            self.logger.exception(f"Failed to connect to Redis: {str(e)}")
            raise

    async def close(self):
        if self.client:
            await self.client.aclose()
            if self.logger:
                self.logger.info("Redis connection closed.")

    async def ping(self) -> bool:
        if not self.client:
            return False
        return bool(await self.client.ping())

    async def get(self, key: str) -> Optional[str]:
        if not self.client:
            return None
        return await self.client.get(key)

    async def set(self, key: str, value: str, ttl: int | None = None):
        if not self.client:
            return
        if ttl:
            await self.client.set(key, value, ex=ttl)
        else:
            await self.client.set(key, value)

    async def delete(self, key: str):
        if not self.client:
            return
        await self.client.delete(key)


redis_instance = RedisClient()
