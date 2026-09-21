from typing import Any

from src.config.exceptions import BadRequestException


class UniqueValidator:
    def __init__(self, crud):
        self.crud = crud

    async def check(self, **filters: Any) -> None:
        if not filters:
            raise ValueError("At least one filter is required")

        for key, value in filters.items():
            if not hasattr(self.crud.model, key):
                raise ValueError(f"Invalid field: {key}")

            existing_obj = await self.crud.get(getattr(self.crud.model, key) == value)
            if existing_obj:
                raise BadRequestException(f"{key} already exists")
