import contextvars
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config.db.models import metadata
from src.config.loggers import Logger
from src.config.settings import VectorDBBackend, settings
from src.utils.vectordb.factory import VectorDBProviderFactory

logger = Logger(__name__)

engine = create_async_engine(settings.DATABASE_URL_ASYNC, echo=True, pool_pre_ping=True)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ==========================================
# 2. الـ Engine الخاص بالـ Celery Workers
# ==========================================
# بيستخدم NullPool عشان يمنع تداخل الـ Processes والـ Forks
celery_engine = create_async_engine(settings.DATABASE_URL_ASYNC, poolclass=NullPool, echo=True, pool_pre_ping=True)

CeleryAsyncSessionLocal = sessionmaker(
    bind=celery_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# VectorDB Configurations
VECTORDB_CLIENT_MAP = {
    VectorDBBackend.QDRANT.value: Path("src/assets/db/qdrant"),
    VectorDBBackend.PGVECTOR.value: AsyncSessionLocal,
}
vectordb_client = VectorDBProviderFactory(settings.VECTOR_DB_BACKEND).create(
    {
        "db_client": VECTORDB_CLIENT_MAP[settings.VECTOR_DB_BACKEND],
        "distance_method": settings.VECTOR_DB_DISTANCE_METHOD,
        "default_vector_size": settings.VECTOR_DB_DEFAULT_SIZE,
        "index_threshold": settings.VECTOR_DB_INDEX_THRESHOLD,
    }
)


async def init_db():
    """
    Initialize database and create tables if needed.
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(metadata.create_all)

        logger.info("Database connected and tables created successfully.")
        return AsyncSessionLocal
    except Exception as e:
        logger.error(
            f"Database connection failed with DATABASE_URL_ASYNC: " f"{settings.DATABASE_URL_ASYNC}, Error: {e}"
        )
        raise


async def init_vectordb():
    """
    Initialize vectordb client and connect to it.
    """
    try:
        # connect to vectordb
        await vectordb_client.connect()
        logger.info("VectorDB client initialized and connected successfully.")
        return vectordb_client
    except Exception as e:
        logger.error(
            f"VectorDB client initialization failed with DATABASE_URL_ASYNC: "
            f"{settings.DATABASE_URL_ASYNC}, Error: {e}"
        )
        raise


async def close_db():
    """
    Dispose the database engine.
    """
    await engine.dispose()


async def close_vectordb():
    try:
        await vectordb_client.disconnect()
        logger.info("VectorDB client disconnected successfully.")
    except Exception as e:
        logger.error(
            f"VectorDB client disconnection failed with DATABASE_URL_ASYNC: "
            f"{settings.DATABASE_URL_ASYNC}, Error: {e}"
        )
        raise


db_session_context: contextvars.ContextVar[AsyncSession] = contextvars.ContextVar("db_session_context")


async def get_db():
    async with AsyncSessionLocal() as session:
        token = None
        try:
            token = db_session_context.set(session)
            yield session
        finally:
            if token:
                try:
                    db_session_context.reset(token)
                except ValueError:
                    # تجاهل خطأ اختلاف الـ Context أثناء الـ Shutdown أو الـ Cleanup في Celery
                    pass
            try:
                await session.close()
            except Exception as e:
                logger.error(f"Error closing session: {e}")


DBSession = Annotated[AsyncSession, Depends(get_db)]
