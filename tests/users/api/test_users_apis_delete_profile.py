# tests/users/apis/test_users_delete_profile.py

import pytest
from fastapi import status

from src.config.permissions import current_user
from tests.conftest import authenticated
from tests.helpers.builders import create_user

BASE_URL = "/api/v1/users"


@pytest.mark.asyncio
async def test_delete_profile_success(test_client, app, db_session):
    user = await create_user(
        db_session,
        username="testuser_delete",
        email="delete@example.com",
        is_active=True,
    )
    await db_session.commit()

    async with authenticated(app, current_user, user):
        response = await test_client.delete(f"{BASE_URL}/profile")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == str(user.id)
    assert data["username"] == "testuser_delete"
    assert data["email"] == "delete@example.com"
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_delete_profile_unauthorized(test_client):
    response = await test_client.delete(f"{BASE_URL}/profile")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
