import uuid

from sqlalchemy import Column, String
from sqlmodel import Field, Relationship, SQLModel

from src.config.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from src.config.settings import settings


class Project(SQLModel, UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    name: str = Field(index=True)
    system_prompt: str
    generation_model_id: str = Field(
        default=settings.DEFAULT_GENERATION_MODEL_ID,
        sa_column=Column(String, nullable=False, server_default=settings.DEFAULT_GENERATION_MODEL_ID),
    )
    # relationships
    user: "User" = Relationship(back_populates="projects", sa_relationship_kwargs={"lazy": "joined"})
    assets: list["Asset"] = Relationship(back_populates="project", sa_relationship_kwargs={"lazy": "joined"})
