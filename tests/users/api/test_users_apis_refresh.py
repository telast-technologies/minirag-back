# tests/users/apis/test_users_refresh_token.py

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi import status

from src.config.permissions import current_user
from src.users.services.tokens import TokenManager
from tests.conftest import authenticated
from tests.helpers.builders import create_user

BASE_URL = "/api/v1/users"


@pytest.mark.asyncio
async def test_refresh_token_success(test_client, app, db_session):
    user = await create_user(
        db_session,
        username="testuser_refresh",
        email="refresh@example.com",
    )
    await db_session.commit()

    fake_token_data = {
        "access_token": "fake-access-token",
        "access_token_expires": datetime.now(timezone.utc) + timedelta(minutes=15),
    }

    async with authenticated(app, current_user, user):
        with (
            patch.object(
                TokenManager,
                "get_refresh_token_cookie",
                return_value={"sub": str(user.id)},
            ) as mocked_get_refresh_cookie,
            patch.object(
                TokenManager,
                "set_access_token_cookie",
                return_value=None,
            ) as mocked_set_access_cookie,
            patch.object(
                TokenManager,
                "get_access_token",
                return_value=fake_token_data,
            ) as mocked_get_access_token,
        ):
            response = await test_client.post(f"{BASE_URL}/refresh_token")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["access_token"] == "fake-access-token"
    assert "access_token_expires" in data

    mocked_get_refresh_cookie.assert_called_once()
    mocked_set_access_cookie.assert_called_once()
    mocked_get_access_token.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_token_sets_cookie_header(test_client, app, db_session):
    user = await create_user(
        db_session,
        username="refresh_cookie_user",
        email="refresh_cookie_user@example.com",
    )
    await db_session.commit()

    fake_token_data = {
        "access_token": "cookie-access-token",
        "access_token_expires": datetime.now(timezone.utc) + timedelta(minutes=15),
    }

    async with authenticated(app, current_user, user):
        with (
            patch.object(
                TokenManager,
                "get_refresh_token_cookie",
                return_value={"sub": str(user.id)},
            ),
            patch.object(
                TokenManager,
                "get_access_token",
                return_value=fake_token_data,
            ),
        ):
            response = await test_client.post(f"{BASE_URL}/refresh_token")

    assert response.status_code == status.HTTP_200_OK
    assert "set-cookie" in response.headers


@pytest.mark.asyncio
async def test_refresh_token_requires_authenticated_user(test_client):
    response = await test_client.post(f"{BASE_URL}/refresh_token")

    assert response.status_code in {
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    }
