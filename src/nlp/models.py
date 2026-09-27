import uuid

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from src.config.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from src.config.settings import settings
from src.utils.llm.generation.enums import MsgRoles


class Session(SQLModel, UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    project_id: uuid.UUID = Field(foreign_key="project.id", index=True)
    name: str = Field(index=True, description="a normailzed name of the session")
    generation_model_id: str = Field(
        default=settings.DEFAULT_GENERATION_MODEL_ID,
        sa_column=Column(String, nullable=False, server_default=settings.DEFAULT_GENERATION_MODEL_ID),
    )
    # relationships
    user: "User" = Relationship(back_populates="sessions", sa_relationship_kwargs={"lazy": "selectin"})
    project: "Project" = Relationship(back_populates="sessions", sa_relationship_kwargs={"lazy": "selectin"})
    messages: list["Message"] = Relationship(
        back_populates="session", sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan"}
    )


class Message(SQLModel, UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    session_id: uuid.UUID = Field(foreign_key="session.id", index=True)
    role: MsgRoles
    content: str
    message_metadata: dict | None = Field(default=None, sa_column=Column("message_metadata", JSONB))

    # relationships
    session: "Session" = Relationship(back_populates="messages", sa_relationship_kwargs={"lazy": "selectin"})
