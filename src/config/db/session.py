import contextvars
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config.db.models import metadata
from src.config.loggers import Logger
from src.config.settings import settings
from src.utils.vectordb.factory import VectorDBProviderFactory

logger = Logger(__name__)

engine = create_async_engine(settings.DATABASE_URL_ASYNC, echo=True)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

vectordb_client = VectorDBProviderFactory(settings.VECTOR_DB_BACKEND).create(
    {
        "db_client": AsyncSessionLocal,
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
        # 2. وضع الـ session جوه المتغير السياقي
        token = db_session_context.set(session)
        try:
            yield session
        finally:
            # تنظيف المتغير بعد انتهاء الريكويست
            db_session_context.reset(token)


DBSession = Annotated[AsyncSession, Depends(get_db)]
