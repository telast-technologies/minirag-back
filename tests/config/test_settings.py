# tests/users/test_models.py
import pytest

from tests.factories import UserFactory


@pytest.mark.asyncio
async def test_user_property(db_session):
    user = UserFactory.build(
        username="dbuser",
        email="dbuser@example.com",
    )
    db_session.add(user)
    await db_session.flush()

    await db_session.refresh(user)

    assert user.username == "dbuser"
