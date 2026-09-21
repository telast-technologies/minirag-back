import pytest

from src.users.crud import UserCRUD
from tests.factories import UserFactory


@pytest.mark.asyncio
async def test_user_crud_create_creates_user(db_session):
    crud = UserCRUD(db_session)

    created = await crud.create(
        {
            "username": "cruduser",
            "email": "cruduser@example.com",
            "phone": "+201300000001",
            "password": "password123",
        }
    )

    assert created.id is not None
    assert created.username == "cruduser"
    assert created.email == "cruduser@example.com"


@pytest.mark.asyncio
async def test_user_crud_update_updates_user_fields(db_session):
    user = UserFactory.build(
        username="beforecrudupdate",
        email="beforecrudupdate@example.com",
    )
    db_session.add(user)
    await db_session.commit()

    crud = UserCRUD(db_session)

    updated = await crud.update(
        user,
        {
            "username": "aftercrudupdate",
            "email": "aftercrudupdate@example.com",
        },
    )

    assert updated.username == "aftercrudupdate"
    assert updated.email == "aftercrudupdate@example.com"
