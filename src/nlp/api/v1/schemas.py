import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.utils.schemas import GenerationModel


class CreateSessionSchema(BaseModel):
    name: str = Field(default_factory=lambda: f"session_{uuid.uuid4()}")
    generation_model_id: GenerationModel | None


class SessionDetailSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    generation_model_id: GenerationModel
    created_at: datetime
    updated_at: datetime


class UpdateSessionSchema(BaseModel):
    name: str | None
    generation_model_id: GenerationModel | None


class SearchRequest(BaseModel):
    session: uuid.UUID | None = None
    text: str = Field(default="", description="the text to search for")
    limit: int = Field(default=5, description="the number of results to return")


class MessageDetailSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    message_metadata: dict | None
    created_at: datetime
    updated_at: datetime
