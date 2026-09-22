import uuid

from fastapi_filter import FilterDepends, with_prefix
from fastapi_filter.contrib.sqlalchemy import Filter
from pydantic import Field

from src.knowledge_base.models import Asset
from src.knowledge_base.models import AssetType, AssetStatus

class AssetFilter(Filter):
    type: AssetType | None = None
    status: AssetStatus | None = None
    order_by: list[str] | None = Field(
        default=None, description="Order by fields, e.g., ['-created_at', 'created_at']"
    )
    search: str | None = Field(default=None, description="Search by content")

    class Constants(Filter.Constants):
        model = Asset
        search_model_fields = ["content"]