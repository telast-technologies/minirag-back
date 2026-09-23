import contextvars

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config.db.models import metadata
from src.config.loggers import Logger
from src.config.settings import settings

logger = Logger(__name__)

engine = create_async_engine(settings.DATABASE_URL_ASYNC, echo=True)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """
    Initialize database and create tables if needed.
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(metadata.create_all)

        logger.info("Database connected and tables created successfully.")
    except Exception as e:
        logger.error(
            f"Database connection failed with DATABASE_URL_ASYNC: " f"{settings.DATABASE_URL_ASYNC}, Error: {e}"
        )
        raise


async def close_db():
    """
    Dispose the database engine.
    """
    await engine.dispose()


db_session_context: contextvars.ContextVar[AsyncSession] = contextvars.ContextVar("db_session_context")
async def get_db():
    async with AsyncSessionLocal() as session:
        # 2. وضع الـ session جوه المتغير السياقي
        token = db_session_context.set(session)
        try:
            yield session
        finally:
            # تنظيف المتغير بعد انتهاء الريكويست
            db_session_context.reset(token)


DBSession = Annotated[AsyncSession, Depends(get_db)]
