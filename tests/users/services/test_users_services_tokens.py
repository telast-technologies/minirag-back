# tests/users/services/test_token_manager.py

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from starlette.responses import Response

from src.config.exceptions import UnAuthorizedException
from src.config.settings import settings
from src.users.services.tokens import TokenManager
from tests.factories import UserFactory


@pytest.mark.asyncio
async def test_generate_tokens_returns_access_and_refresh_tokens(patched_settings):
    user = UserFactory.build()
    manager = TokenManager(user)

    tokens = manager.generate_tokens()

    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["access_token_expires"] > datetime.now(timezone.utc)
    assert tokens["refresh_token_expires"] > datetime.now(timezone.utc)

    access_payload = jwt.decode(
        tokens["access_token"],
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    refresh_payload = jwt.decode(
        tokens["refresh_token"],
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )

    assert access_payload["sub"] == str(user.id)
    assert refresh_payload["sub"] == str(user.id)


@pytest.mark.asyncio
async def test_set_cookies_sets_both_access_and_refresh_cookies(patched_settings):
    user = UserFactory.build()
    manager = TokenManager(user)
    response = Response()

    manager.set_cookies(response)

    set_cookie_headers = [value.decode() for name, value in response.raw_headers if name == b"set-cookie"]

    assert len(set_cookie_headers) == 2
    assert any(settings.JWT_COOKIE_NAME in header for header in set_cookie_headers)
    assert any(settings.JWT_REFRESH_COOKIE_NAME in header for header in set_cookie_headers)


@pytest.mark.asyncio
async def test_set_cookies_sets_cookie_attributes(patched_settings):
    user = UserFactory.build()
    manager = TokenManager(user)
    response = Response()

    manager.set_cookies(response)

    set_cookie_headers = [value.decode() for name, value in response.raw_headers if name == b"set-cookie"]

    access_header = next(header for header in set_cookie_headers if settings.JWT_COOKIE_NAME in header)
    refresh_header = next(header for header in set_cookie_headers if settings.JWT_REFRESH_COOKIE_NAME in header)

    assert "HttpOnly" in access_header
    assert "HttpOnly" in refresh_header
    assert f"SameSite={settings.COOKIE_SAMESITE}" in access_header
    assert f"SameSite={settings.COOKIE_SAMESITE}" in refresh_header
    assert f"Max-Age={settings.ACCESS_TOKEN_TIME_OUT * 60}" in access_header
    assert f"Max-Age={settings.REFRESH_TOKEN_TIME_OUT * 24 * 60 * 60}" in refresh_header


@pytest.mark.asyncio
async def test_set_cookies_does_not_regenerate_access_cookie_when_already_present(
    patched_settings,
):
    user = UserFactory.build()
    manager = TokenManager(user)
    response = Response()

    existing_access = manager.generate_access_token()["access_token"]

    manager.set_cookies(response)

    set_cookie_headers = [value.decode() for name, value in response.raw_headers if name == b"set-cookie"]

    access_headers = [header for header in set_cookie_headers if settings.JWT_COOKIE_NAME in header]
    refresh_headers = [header for header in set_cookie_headers if settings.JWT_REFRESH_COOKIE_NAME in header]

    assert manager.access_token == existing_access
    assert len(access_headers) == 0
    assert len(refresh_headers) == 1


@pytest.mark.asyncio
async def test_set_cookies_does_not_regenerate_refresh_cookie_when_already_present(
    patched_settings,
):
    user = UserFactory.build()
    manager = TokenManager(user)
    response = Response()

    existing_refresh = manager.generate_refresh_token()["refresh_token"]

    manager.set_cookies(response)

    set_cookie_headers = [value.decode() for name, value in response.raw_headers if name == b"set-cookie"]

    access_headers = [header for header in set_cookie_headers if settings.JWT_COOKIE_NAME in header]
    refresh_headers = [header for header in set_cookie_headers if settings.JWT_REFRESH_COOKIE_NAME in header]

    assert manager.refresh_token == existing_refresh
    assert len(access_headers) == 1
    assert len(refresh_headers) == 0


@pytest.mark.asyncio
async def test_set_access_token_cookie_sets_access_cookie_and_internal_token(
    patched_settings,
):
    user = UserFactory.build()
    manager = TokenManager(user)
    response = Response()

    manager.set_access_token_cookie(response)

    assert isinstance(manager.access_token, dict)
    assert "access_token" in manager.access_token
    assert "access_token_expires" in manager.access_token

    set_cookie_headers = [value.decode() for name, value in response.raw_headers if name == b"set-cookie"]
    assert len(set_cookie_headers) == 1
    assert settings.JWT_COOKIE_NAME in set_cookie_headers[0]


@pytest.mark.asyncio
async def test_set_refresh_token_cookie_sets_refresh_cookie_and_internal_token(
    patched_settings,
):
    user = UserFactory.build()
    manager = TokenManager(user)
    response = Response()

    manager.set_refresh_token_cookie(response)

    assert isinstance(manager.refresh_token, dict)
    assert "refresh_token" in manager.refresh_token
    assert "refresh_token_expires" in manager.refresh_token

    set_cookie_headers = [value.decode() for name, value in response.raw_headers if name == b"set-cookie"]
    assert len(set_cookie_headers) == 1
    assert settings.JWT_REFRESH_COOKIE_NAME in set_cookie_headers[0]


@pytest.mark.asyncio
async def test_clear_cookies_adds_delete_cookie_headers(patched_settings):
    user = UserFactory.build()
    manager = TokenManager(user)
    response = Response()

    manager.clear_cookies(response)

    set_cookie_headers = [value.decode() for name, value in response.raw_headers if name == b"set-cookie"]

    assert any(settings.JWT_COOKIE_NAME in header for header in set_cookie_headers)
    assert any(settings.JWT_REFRESH_COOKIE_NAME in header for header in set_cookie_headers)


@pytest.mark.asyncio
async def test_clear_cookies_sets_zero_max_age_for_deleted_cookies(patched_settings):
    user = UserFactory.build()
    manager = TokenManager(user)
    response = Response()

    manager.clear_cookies(response)

    set_cookie_headers = [value.decode() for name, value in response.raw_headers if name == b"set-cookie"]

    access_header = next(header for header in set_cookie_headers if settings.JWT_COOKIE_NAME in header)
    refresh_header = next(header for header in set_cookie_headers if settings.JWT_REFRESH_COOKIE_NAME in header)

    assert "Max-Age=0" in access_header
    assert "Max-Age=0" in refresh_header


@pytest.mark.asyncio
async def test_get_access_token_cookie_returns_payload_when_cookie_is_valid(
    patched_settings,
):
    user = UserFactory.build()
    manager = TokenManager(user)

    access_token = jwt.encode(
        {
            "sub": str(user.id),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    request = SimpleNamespace(cookies={settings.JWT_COOKIE_NAME: access_token})

    payload = manager.get_access_token_cookie(request)

    assert payload["sub"] == str(user.id)


@pytest.mark.asyncio
async def test_get_access_token_cookie_raises_when_cookie_missing(patched_settings):
    user = UserFactory.build()
    manager = TokenManager(user)
    request = SimpleNamespace(cookies={})

    with pytest.raises(UnAuthorizedException, match="Missing access token cookie"):
        manager.get_access_token_cookie(request)


@pytest.mark.asyncio
async def test_get_access_token_cookie_raises_when_token_expired(patched_settings):
    user = UserFactory.build()
    manager = TokenManager(user)

    expired_token = jwt.encode(
        {
            "sub": str(user.id),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    request = SimpleNamespace(cookies={settings.JWT_COOKIE_NAME: expired_token})

    with pytest.raises(UnAuthorizedException, match="Access token expired"):
        manager.get_access_token_cookie(request)


@pytest.mark.asyncio
async def test_get_access_token_cookie_raises_when_token_invalid(patched_settings):
    user = UserFactory.build()
    manager = TokenManager(user)
    request = SimpleNamespace(cookies={settings.JWT_COOKIE_NAME: "not-a-token"})

    with pytest.raises(UnAuthorizedException, match="Invalid access token"):
        manager.get_access_token_cookie(request)


@pytest.mark.asyncio
async def test_get_refresh_token_cookie_returns_payload_when_cookie_is_valid(
    patched_settings,
):
    user = UserFactory.build()
    manager = TokenManager(user)

    refresh_token = jwt.encode(
        {
            "sub": str(user.id),
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    request = SimpleNamespace(cookies={settings.JWT_REFRESH_COOKIE_NAME: refresh_token})

    payload = manager.get_refresh_token_cookie(request)

    assert payload["sub"] == str(user.id)


@pytest.mark.asyncio
async def test_get_refresh_token_cookie_raises_when_cookie_missing(patched_settings):
    user = UserFactory.build()
    manager = TokenManager(user)
    request = SimpleNamespace(cookies={})

    with pytest.raises(UnAuthorizedException, match="Missing refresh token cookie"):
        manager.get_refresh_token_cookie(request)


@pytest.mark.asyncio
async def test_get_refresh_token_cookie_raises_when_token_expired(patched_settings):
    user = UserFactory.build()
    manager = TokenManager(user)

    expired_token = jwt.encode(
        {
            "sub": str(user.id),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    request = SimpleNamespace(cookies={settings.JWT_REFRESH_COOKIE_NAME: expired_token})

    with pytest.raises(UnAuthorizedException, match="Refresh token expired"):
        manager.get_refresh_token_cookie(request)


@pytest.mark.asyncio
async def test_get_refresh_token_cookie_raises_when_token_invalid(patched_settings):
    user = UserFactory.build()
    manager = TokenManager(user)
    request = SimpleNamespace(cookies={settings.JWT_REFRESH_COOKIE_NAME: "not-a-token"})

    with pytest.raises(UnAuthorizedException, match="Invalid refresh token"):
        manager.get_refresh_token_cookie(request)


@pytest.mark.asyncio
async def test_get_access_token_returns_generated_access_token_string(patched_settings):
    user = UserFactory.build()
    manager = TokenManager(user)

    generated = manager.generate_access_token()
    current = manager.get_access_token()

    assert isinstance(current, str)
    assert current == generated["access_token"]

    payload = jwt.decode(
        current,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    assert payload["sub"] == str(user.id)
