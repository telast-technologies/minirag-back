# tests/db.py
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

DATABASE_URL = "sqlite+aiosqlite://"

test_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=StaticPool,
)
