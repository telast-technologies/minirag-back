from fastapi_filter.contrib.sqlalchemy import Filter
from pydantic import Field

from src.users.models import User


class UserFilter(Filter):
    # Direct field on the User model
    is_active: bool | None = Field(default=None, description="Filter by active status of the user", alias="is_active")

    class Constants(Filter.Constants):
        model = User
