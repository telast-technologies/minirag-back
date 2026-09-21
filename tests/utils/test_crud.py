# tests/utils/test_crud.py
import pytest
from sqlmodel import select

from src.users.models import User
from src.utils.crud import CRUDBase
from tests.factories import UserFactory


class UserCRUD(CRUDBase[User]):
    model = User


@pytest.mark.asyncio
async def test_select_returns_model_select_statement(db_session):
    crud = UserCRUD(db_session)

    statement = crud.select()

    assert statement is not None
    assert str(statement) == str(select(User))


@pytest.mark.asyncio
async def test_get_returns_none_when_not_found(db_session):
    crud = UserCRUD(db_session)

    result = await crud.get(User.username == "missing-user")

    assert result is None


@pytest.mark.asyncio
async def test_get_without_where_returns_some_object_when_rows_exist(db_session):
    first_user = UserFactory.build(
        username="get_without_where_first",
        email="get_without_where_first@example.com",
        phone="+201111111110",
    )
    second_user = UserFactory.build(
        username="get_without_where_second",
        email="get_without_where_second@example.com",
        phone="+201111111109",
    )
    db_session.add(first_user)
    db_session.add(second_user)
    await db_session.commit()

    crud = UserCRUD(db_session)

    result = await crud.get()

    assert result is not None
    assert isinstance(result, User)


@pytest.mark.asyncio
async def test_get_returns_first_matching_object(db_session):
    user = UserFactory.build(
        username="get_user",
        email="get_user@example.com",
        phone="+201111111111",
    )
    db_session.add(user)
    await db_session.commit()

    crud = UserCRUD(db_session)

    result = await crud.get(User.username == "get_user")

    assert result is not None
    assert result.id == user.id
    assert result.username == "get_user"


@pytest.mark.asyncio
async def test_get_accepts_multiple_where_conditions(db_session):
    matched = UserFactory.build(
        username="multi_where_user_a",
        email="multi_where_user_a@example.com",
    )
    non_matched_same_email = UserFactory.build(
        username="multi_where_user_b",
        email="multi_where_user_b@example.com",
    )
    db_session.add(matched)
    db_session.add(non_matched_same_email)
    await db_session.commit()

    crud = UserCRUD(db_session)

    result = await crud.get(
        User.username == "multi_where_user_a",
        User.email == "multi_where_user_a@example.com",
    )

    assert result is not None
    assert result.id == matched.id
    assert result.username == "multi_where_user_a"
    assert result.email == "multi_where_user_a@example.com"


@pytest.mark.asyncio
async def test_list_returns_all_matching_objects(db_session):
    user_1 = UserFactory.build(
        username="list_user_1",
        email="list_user_1@example.com",
        phone="+201111111112",
    )
    user_2 = UserFactory.build(
        username="list_user_2",
        email="list_user_2@example.com",
        phone="+201111111113",
    )
    db_session.add(user_1)
    db_session.add(user_2)
    await db_session.commit()

    crud = UserCRUD(db_session)

    result = await crud.list()

    usernames = {item.username for item in result}
    assert "list_user_1" in usernames
    assert "list_user_2" in usernames


@pytest.mark.asyncio
async def test_list_filters_results(db_session):
    matched = UserFactory.build(
        username="filtered_user",
        email="filtered_user@example.com",
        phone="+201111111114",
    )
    other = UserFactory.build(
        username="other_user",
        email="other_user@example.com",
        phone="+201111111115",
    )
    db_session.add(matched)
    db_session.add(other)
    await db_session.commit()

    crud = UserCRUD(db_session)

    result = await crud.list(User.username == "filtered_user")

    assert len(result) == 1
    assert result[0].username == "filtered_user"


@pytest.mark.asyncio
async def test_list_accepts_multiple_where_conditions(db_session):
    matched = UserFactory.build(
        username="list_multi_where_a",
        email="list_multi_where_a@example.com",
        phone="+201111111132",
    )
    same_email = UserFactory.build(
        username="list_multi_where_b",
        email="list_multi_where_b@example.com",
        phone="+201111111133",
    )
    other = UserFactory.build(
        username="another_user_entirely",
        email="another_user_entirely@example.com",
        phone="+201111111134",
    )
    db_session.add(matched)
    db_session.add(same_email)
    db_session.add(other)
    await db_session.commit()

    crud = UserCRUD(db_session)

    result = await crud.list(
        User.username == "list_multi_where_a",
        User.email == "list_multi_where_a@example.com",
    )

    assert len(result) == 1
    assert result[0].id == matched.id
    assert result[0].username == "list_multi_where_a"
    assert result[0].email == "list_multi_where_a@example.com"


@pytest.mark.asyncio
async def test_exec_runs_custom_statement(db_session):
    user = UserFactory.build(
        username="exec_user",
        email="exec_user@example.com",
        phone="+201111111116",
    )
    db_session.add(user)
    await db_session.commit()

    crud = UserCRUD(db_session)

    result = await crud.exec(select(User).where(User.username == "exec_user"))
    db_user = result.first()

    assert db_user is not None
    assert db_user.username == "exec_user"


@pytest.mark.asyncio
async def test_create_accepts_dict_and_persists(db_session):
    crud = UserCRUD(db_session)

    created = await crud.create(
        {
            "username": "created_from_dict",
            "email": "created_from_dict@example.com",
            "phone": "+201111111117",
            "password": "password123",
        }
    )

    assert created.id is not None
    assert created.username == "created_from_dict"

    fetched = await db_session.exec(select(User).where(User.username == "created_from_dict"))
    assert fetched.first() is not None


@pytest.mark.asyncio
async def test_create_accepts_model_instance(db_session):
    crud = UserCRUD(db_session)

    user = UserFactory.build(
        username="created_from_model",
        email="created_from_model@example.com",
        phone="+201111111118",
    )

    created = await crud.create(user)

    assert created.id is not None
    assert created.username == "created_from_model"


@pytest.mark.asyncio
async def test_update_accepts_dict(db_session):
    user = UserFactory.build(
        username="before_update_dict",
        email="before_update_dict@example.com",
        phone="+201111111119",
    )
    db_session.add(user)
    await db_session.commit()

    crud = UserCRUD(db_session)

    updated = await crud.update(
        user,
        {
            "username": "after_update_dict",
            "email": "after_update_dict@example.com",
        },
    )

    assert updated.username == "after_update_dict"
    assert updated.email == "after_update_dict@example.com"


@pytest.mark.asyncio
async def test_update_accepts_sqlmodel_schema_like_object(db_session):
    user = UserFactory.build(
        username="before_update_model",
        email="before_update_model@example.com",
        phone="+201111111120",
    )
    db_session.add(user)
    await db_session.commit()

    crud = UserCRUD(db_session)

    payload = User(
        username="after_update_model",
        email="after_update_model@example.com",
    )

    updated = await crud.update(user, payload)

    assert updated.username == "after_update_model"
    assert updated.email == "after_update_model@example.com"


@pytest.mark.asyncio
async def test_update_raises_for_unknown_field(db_session):
    user = UserFactory.build(
        username="before_invalid_update",
        email="before_invalid_update@example.com",
        phone="+201111111121",
    )
    db_session.add(user)
    await db_session.commit()

    crud = UserCRUD(db_session)

    with pytest.raises(AttributeError, match="has no field"):
        await crud.update(user, {"not_a_real_field": "value"})


@pytest.mark.asyncio
async def test_delete_removes_object(db_session):
    user = UserFactory.build(
        username="delete_me",
        email="delete_me@example.com",
        phone="+201111111122",
    )
    db_session.add(user)
    await db_session.commit()

    crud = UserCRUD(db_session)

    deleted = await crud.delete(user)

    assert deleted.id == user.id

    result = await db_session.exec(select(User).where(User.id == user.id))
    assert result.first() is None
