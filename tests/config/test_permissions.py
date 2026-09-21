# tests/config/test_permissions.py

from types import SimpleNamespace

import jwt
import pytest

from src.config import permissions
from src.config.exceptions import ForbiddenException, NotFoundException, UnAuthorizedException
from src.config.permissions import CurrentUser
from src.config.settings import settings


class FakeUserCRUD:
    def __init__(self, db, user_to_return=None):
        self.db = db
        self.user_to_return = user_to_return
        self.get_called_with = None

    async def get(self, condition):
        self.get_called_with = condition
        return self.user_to_return


@pytest.mark.asyncio
async def test_current_user_returns_none_when_not_required():
    dependency = CurrentUser(required=False)
    request = SimpleNamespace(cookies={})
    db = object()

    result = await dependency(request, db)

    assert result is None


@pytest.mark.asyncio
async def test_current_user_raises_when_cookie_missing():
    dependency = CurrentUser(required=True)
    request = SimpleNamespace(cookies={})
    db = object()

    with pytest.raises(UnAuthorizedException, match="Not authenticated"):
        await dependency(request, db)


@pytest.mark.asyncio
async def test_current_user_raises_when_token_expired(monkeypatch):
    dependency = CurrentUser(required=True)
    request = SimpleNamespace(cookies={settings.JWT_COOKIE_NAME: "expired-token"})
    db = object()

    def fake_decode(*args, **kwargs):
        raise jwt.ExpiredSignatureError("expired")

    monkeypatch.setattr(permissions.jwt, "decode", fake_decode)

    with pytest.raises(UnAuthorizedException, match="Token expired"):
        await dependency(request, db)


@pytest.mark.asyncio
async def test_optional_current_user_returns_none_when_token_expired(monkeypatch):
    dependency = CurrentUser(required=False)
    request = SimpleNamespace(cookies={settings.JWT_COOKIE_NAME: "expired-token"})
    db = object()

    def fake_decode(*args, **kwargs):
        raise jwt.ExpiredSignatureError("expired")

    monkeypatch.setattr(permissions.jwt, "decode", fake_decode)

    result = await dependency(request, db)

    assert result is None


@pytest.mark.asyncio
async def test_current_user_raises_when_token_invalid(monkeypatch):
    dependency = CurrentUser(required=True)
    request = SimpleNamespace(cookies={settings.JWT_COOKIE_NAME: "invalid-token"})
    db = object()

    def fake_decode(*args, **kwargs):
        raise jwt.InvalidTokenError("invalid")

    monkeypatch.setattr(permissions.jwt, "decode", fake_decode)

    with pytest.raises(UnAuthorizedException, match="Invalid token"):
        await dependency(request, db)


@pytest.mark.asyncio
async def test_optional_current_user_returns_none_when_token_invalid(monkeypatch):
    dependency = CurrentUser(required=False)
    request = SimpleNamespace(cookies={settings.JWT_COOKIE_NAME: "invalid-token"})
    db = object()

    def fake_decode(*args, **kwargs):
        raise jwt.InvalidTokenError("invalid")

    monkeypatch.setattr(permissions.jwt, "decode", fake_decode)

    result = await dependency(request, db)

    assert result is None


@pytest.mark.asyncio
async def test_current_user_raises_when_user_not_found(monkeypatch):
    dependency = CurrentUser(required=True)
    request = SimpleNamespace(cookies={settings.JWT_COOKIE_NAME: "valid-token"})
    db = object()

    monkeypatch.setattr(
        permissions.jwt,
        "decode",
        lambda *args, **kwargs: {"sub": "user-123"},
    )
    fake_crud = FakeUserCRUD(db=db, user_to_return=None)
    monkeypatch.setattr(permissions, "UserCRUD", lambda db_arg: fake_crud)

    with pytest.raises(NotFoundException, match="User not found"):
        await dependency(request, db)


@pytest.mark.asyncio
async def test_optional_current_user_returns_none_when_user_not_found(monkeypatch):
    dependency = CurrentUser(required=False)
    request = SimpleNamespace(cookies={settings.JWT_COOKIE_NAME: "valid-token"})
    db = object()

    monkeypatch.setattr(
        permissions.jwt,
        "decode",
        lambda *args, **kwargs: {"sub": "user-123"},
    )
    fake_crud = FakeUserCRUD(db=db, user_to_return=None)
    monkeypatch.setattr(permissions, "UserCRUD", lambda db_arg: fake_crud)

    result = await dependency(request, db)

    assert result is None


@pytest.mark.asyncio
async def test_current_user_raises_when_user_is_deactivated(monkeypatch):
    dependency = CurrentUser(required=True)
    request = SimpleNamespace(cookies={settings.JWT_COOKIE_NAME: "valid-token"})
    db = object()
    inactive_user = SimpleNamespace(id="user-123", is_active=False)

    monkeypatch.setattr(
        permissions.jwt,
        "decode",
        lambda *args, **kwargs: {"sub": "user-123"},
    )
    fake_crud = FakeUserCRUD(db=db, user_to_return=inactive_user)
    monkeypatch.setattr(permissions, "UserCRUD", lambda db_arg: fake_crud)

    with pytest.raises(ForbiddenException, match="User is deactivated"):
        await dependency(request, db)


@pytest.mark.asyncio
async def test_optional_current_user_returns_none_when_user_is_deactivated(monkeypatch):
    dependency = CurrentUser(required=False)
    request = SimpleNamespace(cookies={settings.JWT_COOKIE_NAME: "valid-token"})
    db = object()
    inactive_user = SimpleNamespace(id="user-123", is_active=False)

    monkeypatch.setattr(
        permissions.jwt,
        "decode",
        lambda *args, **kwargs: {"sub": "user-123"},
    )
    fake_crud = FakeUserCRUD(db=db, user_to_return=inactive_user)
    monkeypatch.setattr(permissions, "UserCRUD", lambda db_arg: fake_crud)

    result = await dependency(request, db)

    assert result is None


@pytest.mark.asyncio
async def test_current_user_returns_user_when_token_is_valid_and_user_is_active(
    monkeypatch,
):
    dependency = CurrentUser(required=True)
    request = SimpleNamespace(cookies={settings.JWT_COOKIE_NAME: "valid-token"})
    db = object()
    active_user = SimpleNamespace(id="user-123", is_active=True)
    decode_calls = {}

    def fake_decode(token, secret, algorithms, options):
        decode_calls["token"] = token
        decode_calls["secret"] = secret
        decode_calls["algorithms"] = algorithms
        decode_calls["options"] = options
        return {"sub": "user-123"}

    monkeypatch.setattr(permissions.jwt, "decode", fake_decode)
    fake_crud = FakeUserCRUD(db=db, user_to_return=active_user)
    monkeypatch.setattr(permissions, "UserCRUD", lambda db_arg: fake_crud)

    result = await dependency(request, db)

    assert result is active_user
    assert fake_crud.db is db
    assert decode_calls["token"] == "valid-token"
    assert decode_calls["secret"] == settings.JWT_SECRET_KEY
    assert decode_calls["algorithms"] == [settings.JWT_ALGORITHM]
    assert decode_calls["options"] == {"require": ["sub"]}


@pytest.mark.asyncio
async def test_optional_current_user_returns_user_when_token_is_valid_and_user_is_active(
    monkeypatch,
):
    dependency = CurrentUser(required=False)
    request = SimpleNamespace(cookies={settings.JWT_COOKIE_NAME: "valid-token"})
    db = object()
    active_user = SimpleNamespace(id="user-123", is_active=True)

    monkeypatch.setattr(
        permissions.jwt,
        "decode",
        lambda *args, **kwargs: {"sub": "user-123"},
    )
    fake_crud = FakeUserCRUD(db=db, user_to_return=active_user)
    monkeypatch.setattr(permissions, "UserCRUD", lambda db_arg: fake_crud)

    result = await dependency(request, db)

    assert result is active_user


@pytest.mark.asyncio
async def test_current_user_passes_db_to_user_crud(monkeypatch):
    dependency = CurrentUser(required=True)
    request = SimpleNamespace(cookies={settings.JWT_COOKIE_NAME: "valid-token"})
    db = object()
    active_user = SimpleNamespace(id="user-456", is_active=True)

    monkeypatch.setattr(
        permissions.jwt,
        "decode",
        lambda *args, **kwargs: {"sub": "user-456"},
    )

    captured = {}

    def fake_user_crud(db_arg):
        captured["db"] = db_arg
        return FakeUserCRUD(db=db_arg, user_to_return=active_user)

    monkeypatch.setattr(permissions, "UserCRUD", fake_user_crud)

    result = await dependency(request, db)

    assert result is active_user
    assert captured["db"] is db


@pytest.mark.asyncio
async def test_current_user_queries_user_by_decoded_subject(monkeypatch):
    dependency = CurrentUser(required=True)
    request = SimpleNamespace(cookies={settings.JWT_COOKIE_NAME: "valid-token"})
    db = object()
    active_user = SimpleNamespace(id="user-999", is_active=True)

    monkeypatch.setattr(
        permissions.jwt,
        "decode",
        lambda *args, **kwargs: {"sub": "user-999"},
    )
    fake_crud = FakeUserCRUD(db=db, user_to_return=active_user)
    monkeypatch.setattr(permissions, "UserCRUD", lambda db_arg: fake_crud)

    result = await dependency(request, db)

    assert result is active_user
    assert fake_crud.get_called_with is not None


def test_current_user_instance_is_required():
    assert permissions.current_user.required is True


def test_optional_current_user_instance_is_not_required():
    assert permissions.optional_current_user.required is False
