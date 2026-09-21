# tests/users/apis/test_users_logout.py

from unittest.mock import MagicMock

import pytest
from fastapi import status

from src.config.permissions import current_user
from tests.conftest import authenticated
from tests.helpers.builders import create_user

BASE_URL = "/api/v1/users"
ROUTE_MODULE = "src.users.api.v1.routes"


@pytest.mark.asyncio
async def test_logout_success(test_client, app, db_session):
    user = await create_user(
        db_session,
        username="testuser_logout",
        email="logout@example.com",
    )
    await db_session.commit()

    async with authenticated(app, current_user, user):
        response = await test_client.post(f"{BASE_URL}/logout")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}


@pytest.mark.asyncio
async def test_logout_calls_clear_cookies(test_client, app, db_session, monkeypatch):
    user = await create_user(
        db_session,
        username="testuser_logout_spy",
        email="logout_spy@example.com",
    )
    await db_session.commit()

    clear_cookies_spy = MagicMock()

    class FakeTokenManager:
        def __init__(self, passed_user):
            self.user = passed_user

        def clear_cookies(self, response):
            clear_cookies_spy(response)

    monkeypatch.setattr(f"{ROUTE_MODULE}.TokenManager", FakeTokenManager)

    async with authenticated(app, current_user, user):
        response = await test_client.post(f"{BASE_URL}/logout")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}
    clear_cookies_spy.assert_called_once()


@pytest.mark.asyncio
async def test_logout_sets_cookie_header_when_cookies_are_cleared(test_client, app, db_session):
    user = await create_user(
        db_session,
        username="testuser_logout_cookie",
        email="logout_cookie@example.com",
    )
    await db_session.commit()

    async with authenticated(app, current_user, user):
        response = await test_client.post(f"{BASE_URL}/logout")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}

    if "set-cookie" in response.headers:
        assert response.headers["set-cookie"]


@pytest.mark.asyncio
async def test_logout_requires_authenticated_user(test_client):
    response = await test_client.post(f"{BASE_URL}/logout")

    assert response.status_code in {
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    }
