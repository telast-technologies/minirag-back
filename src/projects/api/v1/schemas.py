from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.config.settings import settings
from src.utils.schemas import GenerationModel


class CreateProjectSchema(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    system_prompt: str = Field(..., max_length=10000, min_length=100)
    generation_model_id: GenerationModel = Field(default=settings.DEFAULT_GENERATION_MODEL_ID)


class UpdateProjectSchema(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=50)
    system_prompt: str | None = Field(default=None, max_length=10000, min_length=100)
    generation_model_id: GenerationModel | None = Field(default=None)


class ProjectDetailSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    system_prompt: str
    generation_model_id: GenerationModel
    created_at: datetime
    updated_at: datetime
