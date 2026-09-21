# tests/conftest.py

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from server import create_app
from src.config.db.session import get_db
from src.config.settings import get_settings, settings
from src.config.storage import BucketS3Storage
from tests.db import test_engine


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_test_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    connection = await test_engine.connect()
    outer_transaction = await connection.begin()

    session = AsyncSession(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    nested_transaction = await connection.begin_nested()

    @event.listens_for(session.sync_session, "after_transaction_end")
    def restart_savepoint(sess, transaction):
        nonlocal nested_transaction

        if connection.closed:
            return

        if outer_transaction.is_active and not nested_transaction.is_active:
            nested_transaction = connection.sync_connection.begin_nested()

    try:
        yield session
    finally:
        event.remove(session.sync_session, "after_transaction_end", restart_savepoint)
        await session.close()

        if outer_transaction.is_active:
            await outer_transaction.rollback()

        await connection.close()


@pytest_asyncio.fixture
async def app(db_session: AsyncSession):
    application = create_app()

    async def override_get_db():
        yield db_session

    application.dependency_overrides[get_db] = override_get_db

    async with LifespanManager(application):
        yield application

    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


async def auth_as(app, permission_func, user):
    async def override_current_user():
        return user

    app.dependency_overrides[permission_func] = override_current_user


def clear_auth(app, permission_func):
    app.dependency_overrides.pop(permission_func, None)


@asynccontextmanager
async def authenticated(app, permission_func, user):
    await auth_as(app, permission_func, user)
    try:
        yield
    finally:
        clear_auth(app, permission_func)


@pytest.fixture
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def storage():
    storage_instance = BucketS3Storage()
    storage_instance.AWS_S3_BUCKET_NAME = "test-bucket"
    storage_instance.AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=3600"}
    storage_instance.AWS_DEFAULT_ACL = "public-read"
    storage_instance.default_content_type = "application/octet-stream"
    return storage_instance


@pytest.fixture
def patched_settings(monkeypatch):
    monkeypatch.setattr(settings, "ENV", "test")
    monkeypatch.setattr(settings, "POSTGRES_USER", "postgres")
    monkeypatch.setattr(settings, "POSTGRES_PASSWORD", "secret")
    monkeypatch.setattr(settings, "POSTGRES_DB", "minirag")
    monkeypatch.setattr(settings, "POSTGRES_HOST", "localhost")
    monkeypatch.setattr(settings, "POSTGRES_PORT", 5432)
    monkeypatch.setattr(settings, "REDIS_URL", "redis://localhost:6379/0")

    monkeypatch.setattr(settings, "AWS_ACCESS_KEY_ID", "r2-access")
    monkeypatch.setattr(settings, "AWS_SECRET_ACCESS_KEY", "r2-secret")
    monkeypatch.setattr(settings, "AWS_S3_BUCKET_NAME", "bucket-name")
    monkeypatch.setattr(settings, "AWS_S3_ENDPOINT_URL", "https://r2.example.com")

    monkeypatch.setattr(settings, "GRAFANA_USER", "grafana-user")
    monkeypatch.setattr(settings, "GRAFANA_PASS", "grafana-pass")
    monkeypatch.setattr(settings, "GRAFANA_CLOUD_USER", None)
    monkeypatch.setattr(settings, "GRAFANA_CLOUD_TOKEN", None)

    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "unit-test-secret")
    monkeypatch.setattr(settings, "JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(settings, "ACCESS_TOKEN_TIME_OUT", 15)
    monkeypatch.setattr(settings, "REFRESH_TOKEN_TIME_OUT", 7)
    monkeypatch.setattr(settings, "JWT_COOKIE_NAME", "access_token")
    monkeypatch.setattr(settings, "JWT_REFRESH_COOKIE_NAME", "refresh_token")
    monkeypatch.setattr(settings, "COOKIE_SECURE", False)
    monkeypatch.setattr(settings, "COOKIE_SAMESITE", "lax")
    monkeypatch.setattr(settings, "COOKIE_DOMAIN", None)

    return settings
