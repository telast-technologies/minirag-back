# tests/users/apis/test_users_update_profile.py

import pytest
from fastapi import status

from src.config.permissions import current_user
from tests.conftest import authenticated
from tests.helpers.builders import create_user

BASE_URL = "/api/v1/users"


@pytest.mark.asyncio
async def test_update_profile_fields(test_client, app, db_session):
    user = await create_user(
        db_session,
        username="updateprofileuser",
        email="old@example.com",
        is_active=True,
    )
    await db_session.commit()

    async with authenticated(app, current_user, user):
        response = await test_client.patch(
            f"{BASE_URL}/profile",
            data={
                "email": "new@example.com",
                "phone": "+201211824800",
            },
        )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["email"] == "new@example.com"
    assert data["phone"] == "+201211824800"
    assert data["username"] == "updateprofileuser"


@pytest.mark.asyncio
async def test_update_profile_partial_update_only_changes_sent_fields(test_client, app, db_session):
    user = await create_user(
        db_session,
        username="partialupdateuser",
        email="partialold@example.com",
        is_active=True,
    )
    await db_session.commit()

    async with authenticated(app, current_user, user):
        response = await test_client.patch(
            f"{BASE_URL}/profile",
            data={"email": "partialnew@example.com"},
        )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["email"] == "partialnew@example.com"
    assert data["phone"] == user.phone
    assert data["username"] == user.username


@pytest.mark.asyncio
async def test_update_profile_omitted_optional_fields_do_not_become_null(test_client, app, db_session):
    user = await create_user(
        db_session,
        username="omitfieldsuser",
        email="omitold@example.com",
        is_active=True,
    )
    await db_session.commit()

    async with authenticated(app, current_user, user):
        response = await test_client.patch(
            f"{BASE_URL}/profile",
            data={},
        )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["email"] == user.email
    assert data["phone"] == user.phone
    assert data["username"] == user.username


@pytest.mark.asyncio
async def test_update_profile_unauthorized(test_client):
    response = await test_client.patch(
        f"{BASE_URL}/profile",
        data={"email": "unauthorized@example.com"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
