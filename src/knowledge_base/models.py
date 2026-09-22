import uuid
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from pydantic import HttpUrl

from src.config.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from src.knowledge_base.enums import AssetStatus, AssetType
from src.projects.models import Project


class Asset(SQLModel, UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    project_id: uuid.UUID = Field(foreign_key="project.id", index=True)
    name: str = Field(index=True, description="a normailzed name of the asset")
    type: AssetType = Field(index=True)
    content: str
    asset_metadata: dict | None = Field(
        default=None, 
        sa_column=Column("asset_metadata", JSONB)
    )
    status: AssetStatus = Field(default=AssetStatus.PENDING)

    # relationships
    project: 'Project' = Relationship(
        back_populates="assets",
        sa_relationship_kwargs={"lazy": "joined"}
    )
    

# class AssetChunk(SQLModel, UUIDPrimaryKeyMixin, TimestampMixin, table=True):
#     project_id: uuid.UUID = Field(foreign_key="project.id", index=True)
#     asset_id: uuid.UUID = Field(foreign_key="asset.id", index=True)
#     text: str
#     metadata: dict | None = Field(
#         default=None, 
#         sa_column=Column("metadata", JSONB)
#     )
#     order: int

#     # relationships
#     project: 'Project' = Relationship(
#         back_populates="chunks",
#         sa_relationship_kwargs={"lazy": "joined"}
#     )
#     asset: 'Asset' = Relationship(
#         back_populates="chunks",
#         sa_relationship_kwargs={"lazy": "joined"}
#     )