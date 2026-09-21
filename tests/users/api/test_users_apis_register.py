# tests/users/apis/test_users_register.py

from unittest.mock import AsyncMock

import pytest
from fastapi import status

from tests.helpers.builders import create_user

BASE_URL = "/api/v1/users"
ROUTE_MODULE = "src.users.api.v1.routes"


@pytest.mark.asyncio
async def test_register_success(test_client):
    response = await test_client.post(
        f"{BASE_URL}/register",
        json={
            "username": "newuser",
            "password": "password123",
            "email": "newuser@example.com",
            "phone": "+201211824710",
            "dob": "2000-01-01T00:00:00Z",
            "following": [],
        },
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["username"] == "newuser"
    assert "id" in data
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_register_duplicate_username(test_client, db_session):
    await create_user(
        db_session,
        username="duplicateuser",
        email="dup1@example.com",
    )
    await db_session.commit()

    response = await test_client.post(
        f"{BASE_URL}/register",
        json={
            "username": "duplicateuser",
            "password": "password123",
            "email": "duplicateuser@example.com",
            "phone": "+201211824712",
            "dob": "2000-01-01T00:00:00Z",
            "following": [],
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_register_duplicate_email(test_client, db_session):
    await create_user(
        db_session,
        username="existingemailuser",
        email="duplicate@example.com",
    )
    await db_session.commit()

    response = await test_client.post(
        f"{BASE_URL}/register",
        json={
            "username": "newemailuser",
            "password": "password123",
            "email": "duplicate@example.com",
            "phone": "+201211824714",
            "dob": "2000-01-01T00:00:00Z",
            "following": [],
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_register_duplicate_phone(test_client, db_session):
    await create_user(
        db_session, username="existingphoneuser", email="existingphone@example.com", phone="+201211824715"
    )
    await db_session.commit()

    response = await test_client.post(
        f"{BASE_URL}/register",
        json={
            "username": "newphoneuser",
            "password": "password123",
            "email": "newphoneuser@example.com",
            "phone": "+201211824715",
            "dob": "2000-01-01T00:00:00Z",
            "following": [],
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_register_weak_password(test_client):
    response = await test_client.post(
        f"{BASE_URL}/register",
        json={
            "username": "weakuser",
            "password": "123",
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
async def test_register_returns_500_when_user_create_fails(test_client, monkeypatch):
    mocked_create = AsyncMock(side_effect=Exception("db failure"))
    monkeypatch.setattr(f"{ROUTE_MODULE}.UserCRUD.create", mocked_create)

    response = await test_client.post(
        f"{BASE_URL}/register",
        json={
            "username": "failinguser",
            "password": "password123",
            "email": "failinguser@example.com",
            "phone": "+201211824716",
            "dob": "2000-01-01T00:00:00Z",
            "following": [],
        },
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["detail"] == "Failed to register user"
