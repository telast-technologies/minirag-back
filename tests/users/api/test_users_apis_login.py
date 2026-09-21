# tests/users/apis/test_users_login.py

import pytest
from fastapi import status

from tests.helpers.builders import create_user

BASE_URL = "/api/v1/users"


@pytest.mark.asyncio
async def test_login_success(test_client, db_session):
    await create_user(
        db_session,
        username="loginuser",
        password="password123",
        email="loginuser@example.com",
        is_active=True,
    )
    await db_session.commit()

    response = await test_client.post(
        f"{BASE_URL}/login",
        json={"username": "loginuser", "password": "password123"},
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["username"] == "loginuser"
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_sets_auth_cookies_on_success(test_client, db_session):
    await create_user(
        db_session,
        username="cookieuser",
        password="password123",
        email="cookieuser@example.com",
        is_active=True,
    )
    await db_session.commit()

    response = await test_client.post(
        f"{BASE_URL}/login",
        json={"username": "cookieuser", "password": "password123"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert "set-cookie" in response.headers


@pytest.mark.asyncio
async def test_login_fails_when_user_does_not_exist(test_client):
    response = await test_client.post(
        f"{BASE_URL}/login",
        json={"username": "missinguser", "password": "password123"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Invalid username or password"


@pytest.mark.asyncio
async def test_login_fails_when_password_is_invalid(test_client, db_session):
    await create_user(
        db_session,
        username="wrongpassworduser",
        password="password123",
        email="wrongpassworduser@example.com",
        is_active=True,
    )
    await db_session.commit()

    response = await test_client.post(
        f"{BASE_URL}/login",
        json={"username": "wrongpassworduser", "password": "wrongpassword"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Invalid username or password"


@pytest.mark.asyncio
async def test_login_fails_when_user_is_inactive(test_client, db_session):
    await create_user(
        db_session,
        username="inactiveuser",
        password="password123",
        email="inactiveuser@example.com",
        is_active=False,
    )
    await db_session.commit()

    response = await test_client.post(
        f"{BASE_URL}/login",
        json={"username": "inactiveuser", "password": "password123"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Invalid username or password"
