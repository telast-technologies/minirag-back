from uuid import UUID

from pydantic import BaseModel, Field


class EmbedAssetSchema(BaseModel):
    asset_ids: list[UUID] = Field(default_factory=list)