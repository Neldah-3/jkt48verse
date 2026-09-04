from typing import Optional

from redis.asyncio import Redis

from src.config import config


class RedisClient:
    def __init__(self):
        self.client: Optional[Redis] = None
        self.logger = None

    async def connect(self):
        from src.logging_config import create_logger

        self.logger = create_logger("redis", __name__)
        try:
            self.client = Redis.from_url(
                config.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            await self.client.ping()
            self.logger.info("Connected to Redis (Upstash)")
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
