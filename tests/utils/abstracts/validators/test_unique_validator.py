# tests/utils/test_unique_validator.py

from unittest.mock import AsyncMock

import pytest

from src.config.exceptions import BadRequestException
from src.utils.abstracts.validators import UniqueValidator


class FakeModel:
    email = object()
    username = object()


class FakeCrud:
    model = FakeModel

    def __init__(self):
        self.get = AsyncMock()


@pytest.mark.asyncio
async def test_check_raises_value_error_when_no_filters():
    crud = FakeCrud()
    validator = UniqueValidator(crud)

    with pytest.raises(ValueError, match="At least one filter is required"):
        await validator.check()


@pytest.mark.asyncio
async def test_check_raises_value_error_for_invalid_field():
    crud = FakeCrud()
    validator = UniqueValidator(crud)

    with pytest.raises(ValueError, match="Invalid field: phone"):
        await validator.check(phone="+201234567890")

    crud.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_check_raises_bad_request_when_duplicate_exists():
    crud = FakeCrud()
    crud.get.return_value = object()
    validator = UniqueValidator(crud)

    with pytest.raises(BadRequestException, match="email already exists"):
        await validator.check(email="test@example.com")

    crud.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_passes_when_value_does_not_exist():
    crud = FakeCrud()
    crud.get.return_value = None
    validator = UniqueValidator(crud)

    await validator.check(email="test@example.com")

    crud.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_validates_multiple_fields_one_by_one():
    crud = FakeCrud()
    crud.get.return_value = None
    validator = UniqueValidator(crud)

    await validator.check(email="test@example.com", username="ahmed")

    assert crud.get.await_count == 2
