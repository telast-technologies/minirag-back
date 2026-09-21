# tests/users/apis/test_users_request_username_change.py

import pytest
from fastapi import status

from src.config.permissions import current_user
from tests.conftest import authenticated
from tests.helpers.builders import create_user

BASE_URL = "/api/v1/users"


@pytest.mark.asyncio
async def test_request_username_change(test_client, app, db_session):
    user = await create_user(
        db_session,
        username="testuser_requsername",
        email="requser@example.com",
        is_active=True,
    )
    await db_session.commit()

    async with authenticated(app, current_user, user):
        response = await test_client.patch(
            f"{BASE_URL}/request_username",
            json={"username": "newusername"},
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["username"] == "newusername"


@pytest.mark.asyncio
async def test_request_username_change_duplicate(test_client, app, db_session):
    current = await create_user(
        db_session,
        username="testuser_requsernamedupcurrent",
        email="currentdup@example.com",
        is_active=True,
    )
    await create_user(
        db_session,
        username="targetusername",
        email="targetdup@example.com",
        is_active=True,
    )
    await db_session.commit()

    async with authenticated(app, current_user, current):
        response = await test_client.patch(
            f"{BASE_URL}/request_username",
            json={"username": "targetusername"},
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_request_username_change_to_same_username_skips_uniqueness_conflict(test_client, app, db_session):
    user = await create_user(
        db_session,
        username="sameusername",
        email="sameusername@example.com",
        is_active=True,
    )
    await db_session.commit()

    async with authenticated(app, current_user, user):
        response = await test_client.patch(
            f"{BASE_URL}/request_username",
            json={"username": "sameusername"},
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["username"] == "sameusername"


@pytest.mark.asyncio
async def test_request_username_change_unauthorized(test_client):
    response = await test_client.patch(
        f"{BASE_URL}/request_username",
        json={"username": "newusername"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
