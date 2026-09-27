from fastapi_storages.integrations.sqlalchemy import FileType
from sqlalchemy import Column
from sqlmodel import Field, Relationship, SQLModel

from src.config.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from src.config.hashers import hasher
from src.config.storage import S3Storage


class User(SQLModel, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, table=True):
    firebase_uid: str | None = Field(default=None, index=True, unique=True)
    username: str = Field(index=True, unique=True)
    password: str
    email: str = Field(index=True, unique=True)
    phone: str = Field(index=True, unique=True)
    avatar: str | None = Field(default=None, sa_column=Column(FileType(S3Storage), nullable=True))
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)

    # relationships
    projects: list["Project"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    sessions: list["Session"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    def set_password(self, password: str) -> None:
        self.password = hasher.encode(password)
