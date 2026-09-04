from src.database import Database
from src.health.constants import DatabaseStatus, HealthStatus
from src.health.schemas import HealthCheckResponse
from src.logging_config import create_logger
from src.redis_client import RedisClient

logger = create_logger("health_service", __name__)


class HealthService:
    def __init__(self, db: Database, redis: RedisClient):
        self.db = db
        self.redis = redis

    async def check_health(self) -> HealthCheckResponse:
        database_status = DatabaseStatus.UNKNOWN
        redis_status = DatabaseStatus.UNKNOWN
        overall_status = HealthStatus.OK
        detail_messages = []

        try:
            if await self.db.ping():
                database_status = DatabaseStatus.CONNECTED
            else:
                database_status = DatabaseStatus.DISCONNECTED
                overall_status = HealthStatus.ERROR
        except Exception as e:
            logger.error(f"Health check failed (DB Connection): {e}")
            database_status = DatabaseStatus.ERROR
            overall_status = HealthStatus.ERROR
            detail_messages.append(f"Database: {str(e)}")

        try:
            if await self.redis.ping():
                redis_status = DatabaseStatus.CONNECTED
            else:
                redis_status = DatabaseStatus.DISCONNECTED
                overall_status = HealthStatus.ERROR
        except Exception as e:
            logger.error(f"Health check failed (Redis Connection): {e}")
            redis_status = DatabaseStatus.ERROR
            overall_status = HealthStatus.ERROR
            detail_messages.append(f"Redis: {str(e)}")

        detail = "; ".join(detail_messages) if detail_messages else None
        return HealthCheckResponse(
            status=overall_status,
            database=database_status,
            redis=redis_status,
            detail=detail,
        )
