import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, false, func
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field


class TimestampMixin:
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
        nullable=False,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
        nullable=False,
        sa_column_kwargs={
            "server_default": func.now(),
            "onupdate": func.now(),
        },
    )


class UUIDPrimaryKeyMixin:
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_type=UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
    )


class SoftDeleteMixin:
    is_deleted: bool = Field(
        default=False,
        nullable=False,
        sa_column_kwargs={"server_default": false()},
    )
    deleted_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=True,
    )
