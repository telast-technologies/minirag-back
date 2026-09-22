
from datetime import datetime
from uuid import UUID
from typing import Annotated, List

from fastapi import File, UploadFile
from pydantic import BaseModel, ConfigDict, HttpUrl, Field, AfterValidator

from src.knowledge_base.enums import AssetStatus, AssetType


class CreateTextAssetSchema(BaseModel):
    content: str = Field(..., max_length=100000, min_length=100)

class CreateURlAssetSchema(BaseModel):
    content: Annotated[HttpUrl, AfterValidator(lambda url: str(url))]
    

class CreateFileAssetSchema(BaseModel):
    content: List[UploadFile]

    @classmethod
    def as_form(
        cls,
        content: List[UploadFile] = File(...),
    ):
        return cls(
            content=content,
        )


class AssetDetailSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    type: AssetType
    content: str
    asset_metadata: dict | None = None
    status: AssetStatus
    created_at: datetime
    updated_at: datetime

