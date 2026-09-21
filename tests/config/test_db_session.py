# tests/config/db/test_session.py

import pytest

from src.config.db import session
from src.config.db.session import close_db, get_db, init_db


class FakeAsyncContextManager:
    def __init__(self, value=None, error=None):
        self.value = value
        self.error = error
        self.entered = False
        self.exited = False

    async def __aenter__(self):
        self.entered = True
        if self.error:
            raise self.error
        return self.value

    async def __aexit__(self, exc_type, exc, tb):
        self.exited = True


class FakeConn:
    def __init__(self, error=None):
        self.error = error
        self.run_sync_called = False
        self.run_sync_arg = None

    async def run_sync(self, fn):
        self.run_sync_called = True
        self.run_sync_arg = fn
        if self.error:
            raise self.error


class FakeBeginContextManager:
    def __init__(self, conn=None, error=None):
        self.conn = conn or FakeConn()
        self.error = error
        self.entered = False
        self.exited = False

    async def __aenter__(self):
        self.entered = True
        if self.error:
            raise self.error
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        self.exited = True


class FakeEngine:
    def __init__(self, conn=None, begin_error=None, dispose_error=None):
        self.conn = conn or FakeConn()
        self.begin_error = begin_error
        self.dispose_error = dispose_error
        self.begin_cm = None
        self.dispose_called = False

    def begin(self):
        self.begin_cm = FakeBeginContextManager(
            conn=self.conn,
            error=self.begin_error,
        )
        return self.begin_cm

    async def dispose(self):
        self.dispose_called = True
        if self.dispose_error:
            raise self.dispose_error


class FakeSession:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


class FakeSessionContextManager:
    def __init__(self, session_obj):
        self.session_obj = session_obj
        self.entered = False
        self.exited = False

    async def __aenter__(self):
        self.entered = True
        return self.session_obj

    async def __aexit__(self, exc_type, exc, tb):
        self.exited = True
        await self.session_obj.close()


@pytest.mark.asyncio
async def test_init_db_runs_create_all(monkeypatch):
    fake_conn = FakeConn()
    fake_engine = FakeEngine(conn=fake_conn)

    monkeypatch.setattr(session, "engine", fake_engine)

    await init_db()

    assert fake_engine.begin_cm is not None
    assert fake_engine.begin_cm.entered is True
    assert fake_engine.begin_cm.exited is True
    assert fake_conn.run_sync_called is True


@pytest.mark.asyncio
async def test_init_db_logs_and_reraises_when_create_all_fails(monkeypatch):
    error = RuntimeError("create_all failed")
    fake_conn = FakeConn(error=error)
    fake_engine = FakeEngine(conn=fake_conn)
    error_messages = []

    monkeypatch.setattr(session, "engine", fake_engine)
    monkeypatch.setattr(session.logger, "error", lambda message: error_messages.append(message))

    with pytest.raises(RuntimeError, match="create_all failed"):
        await init_db()

    assert fake_engine.begin_cm is not None
    assert fake_engine.begin_cm.entered is True
    assert fake_engine.begin_cm.exited is True
    assert fake_conn.run_sync_called is True
    assert len(error_messages) == 1
    assert "Database connection failed with DATABASE_URL_ASYNC" in error_messages[0]


@pytest.mark.asyncio
async def test_init_db_logs_and_reraises_when_engine_begin_fails(monkeypatch):
    error = RuntimeError("engine begin failed")
    fake_engine = FakeEngine(begin_error=error)
    error_messages = []

    monkeypatch.setattr(session, "engine", fake_engine)
    monkeypatch.setattr(session.logger, "error", lambda message: error_messages.append(message))

    with pytest.raises(RuntimeError, match="engine begin failed"):
        await init_db()

    assert fake_engine.begin_cm is not None
    assert fake_engine.begin_cm.entered is True
    assert len(error_messages) == 1
    assert "Database connection failed with DATABASE_URL_ASYNC" in error_messages[0]


@pytest.mark.asyncio
async def test_close_db_disposes_engine(monkeypatch):
    fake_engine = FakeEngine()
    monkeypatch.setattr(session, "engine", fake_engine)

    await close_db()

    assert fake_engine.dispose_called is True


@pytest.mark.asyncio
async def test_close_db_reraises_when_dispose_fails(monkeypatch):
    fake_engine = FakeEngine(dispose_error=RuntimeError("dispose failed"))
    monkeypatch.setattr(session, "engine", fake_engine)

    with pytest.raises(RuntimeError, match="dispose failed"):
        await close_db()

    assert fake_engine.dispose_called is True


@pytest.mark.asyncio
async def test_get_db_yields_session_from_session_local(monkeypatch):
    fake_session = FakeSession()
    fake_cm = FakeSessionContextManager(fake_session)
    monkeypatch.setattr(session, "AsyncSessionLocal", lambda: fake_cm)

    generator = get_db()
    yielded = await anext(generator)

    assert yielded is fake_session
    assert fake_cm.entered is True
    assert fake_session.closed is False

    with pytest.raises(StopAsyncIteration):
        await anext(generator)

    assert fake_cm.exited is True
    assert fake_session.closed is True


@pytest.mark.asyncio
async def test_get_db_closes_session_when_generator_is_closed_early(monkeypatch):
    fake_session = FakeSession()
    fake_cm = FakeSessionContextManager(fake_session)
    monkeypatch.setattr(session, "AsyncSessionLocal", lambda: fake_cm)

    generator = get_db()
    yielded = await anext(generator)

    assert yielded is fake_session
    assert fake_session.closed is False

    await generator.aclose()

    assert fake_cm.exited is True
    assert fake_session.closed is True


@pytest.mark.asyncio
async def test_get_db_propagates_session_factory_enter_error(monkeypatch):
    error = RuntimeError("session open failed")
    monkeypatch.setattr(
        session,
        "AsyncSessionLocal",
        lambda: FakeAsyncContextManager(error=error),
    )

    generator = get_db()

    with pytest.raises(RuntimeError, match="session open failed"):
        await anext(generator)
