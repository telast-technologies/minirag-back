# tests/users/apis/test_users_change_password.py

from unittest.mock import MagicMock

import pytest
from fastapi import status

from src.config.permissions import current_user
from tests.conftest import authenticated
from tests.helpers.builders import create_user

BASE_URL = "/api/v1/users"


@pytest.mark.asyncio
async def test_change_password_success(test_client, app, db_session, monkeypatch):
    user = await create_user(
        db_session,
        username="testuser_change_pw_01",
        password="stored-old-password",
        email="changepw01@example.com",
        is_active=True,
    )
    await db_session.commit()

    old_hashed_password = user.password

    decode_spy = MagicMock(return_value=True)
    encode_spy = MagicMock(return_value="hashed-newpassword456")

    monkeypatch.setattr(app.state.hashing, "decode", decode_spy)
    monkeypatch.setattr(app.state.hashing, "encode", encode_spy)

    async with authenticated(app, current_user, user):
        response = await test_client.patch(
            f"{BASE_URL}/change_password",
            json={
                "old_password": "oldpassword123",
                "new_password": "newpassword456",
            },
        )

    assert response.status_code == status.HTTP_200_OK
    decode_spy.assert_called_once_with("oldpassword123", old_hashed_password)
    encode_spy.assert_called_once_with("newpassword456")
    assert user.password == "hashed-newpassword456"


@pytest.mark.asyncio
async def test_change_password_wrong_old_password(test_client, app, db_session, monkeypatch):
    user = await create_user(
        db_session,
        username="testuser_wrong_old_pw_01",
        password="stored-correct-password",
        email="wrongold01@example.com",
        is_active=True,
    )
    await db_session.commit()

    decode_spy = MagicMock(return_value=False)
    encode_spy = MagicMock()

    monkeypatch.setattr(app.state.hashing, "decode", decode_spy)
    monkeypatch.setattr(app.state.hashing, "encode", encode_spy)

    async with authenticated(app, current_user, user):
        response = await test_client.patch(
            f"{BASE_URL}/change_password",
            json={
                "old_password": "wrongpassword",
                "new_password": "newpassword456",
            },
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Old password is incorrect"
    decode_spy.assert_called_once_with("wrongpassword", user.password)
    encode_spy.assert_not_called()


@pytest.mark.asyncio
async def test_change_password_same_as_old(test_client, app, db_session, monkeypatch):
    user = await create_user(
        db_session,
        username="testuser_same_pw_01",
        password="stored-same-password",
        email="samepw01@example.com",
        is_active=True,
    )
    await db_session.commit()

    decode_spy = MagicMock(return_value=True)
    encode_spy = MagicMock()

    monkeypatch.setattr(app.state.hashing, "decode", decode_spy)
    monkeypatch.setattr(app.state.hashing, "encode", encode_spy)

    async with authenticated(app, current_user, user):
        response = await test_client.patch(
            f"{BASE_URL}/change_password",
            json={
                "old_password": "samepassword123",
                "new_password": "samepassword123",
            },
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "New password cannot be the same as old password"
    decode_spy.assert_called_once_with("samepassword123", user.password)
    encode_spy.assert_not_called()
