from uuid import UUID

from pydantic import BaseModel, Field


class EmbedAssetSchema(BaseModel):
    asset_ids: list[UUID] = Field(default_factory=list)


class SearchRequest(BaseModel):
    text: str = Field(default="", description="the text to search for")
    limit: int = Field(default=5, description="the number of results to return")
