import uuid

from sqlmodel import Field, Relationship, SQLModel

from src.config.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from src.knowledge_base.models import Asset
from src.users.models import User


class Project(SQLModel, UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    name: str = Field(index=True, unique=True)
    system_prompt: str

    # relationships
    user: "User" = Relationship(back_populates="projects", sa_relationship_kwargs={"lazy": "joined"})
    assets: list["Asset"] = Relationship(back_populates="project", sa_relationship_kwargs={"lazy": "joined"})
