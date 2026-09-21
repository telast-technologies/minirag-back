# tests/users/apis/test_users_profile.py

import pytest
from fastapi import status

from src.config.permissions import current_user
from tests.conftest import authenticated
from tests.helpers.builders import create_user

BASE_URL = "/api/v1/users"


@pytest.mark.asyncio
async def test_get_profile_returns_current_user(test_client, app, db_session):
    user = await create_user(
        db_session,
        username="testuser_profile",
        email="profile@example.com",
        is_active=True,
    )
    await db_session.commit()

    async with authenticated(app, current_user, user):
        response = await test_client.get(f"{BASE_URL}/profile")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == str(user.id)
    assert data["username"] == user.username
    assert data["email"] == user.email
    assert data["phone"] == user.phone
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_get_profile_unauthorized(test_client):
    response = await test_client.get(f"{BASE_URL}/profile")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_profile_returns_fresh_user_data(test_client, app, db_session):
    user = await create_user(
        db_session,
        username="fresh_profile_user",
        email="fresh_profile@example.com",
        phone="+201211824711",
        is_active=True,
    )
    await db_session.commit()

    async with authenticated(app, current_user, user):
        user.username = "fresh_profile_user_updated"
        await db_session.flush()

        response = await test_client.get(f"{BASE_URL}/profile")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["username"] == "fresh_profile_user_updated"
