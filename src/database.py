from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import config


class Database:
    def __init__(self):
        self.engine = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None
        self.logger = None

    async def connect(self):
        from src.logging_config import create_logger

        self.logger = create_logger("database", __name__)
        try:
            self.engine = create_async_engine(
                config.database_url,
                pool_size=config.db_max_pool_size,
                max_overflow=5,
                pool_pre_ping=True,
                pool_timeout=config.DB_POOL_TIMEOUT,
            )
            self.session_factory = async_sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )
            self.logger.info("Connected to PostgreSQL (Supabase)")
        except Exception as e:
            self.logger.exception(f"Failed to connect to the database: {str(e)}")
            raise

    async def close(self):
        if self.engine:
            await self.engine.dispose()
            if self.logger:
                self.logger.info("Database connection closed.")

    async def ping(self) -> bool:
        if not self.engine:
            return False
        async with self.engine.connect() as conn:
            await conn.exec_driver_sql("SELECT 1")
        return True


database_instance = Database()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if database_instance.session_factory is None:
        await database_instance.connect()
    async with database_instance.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
