from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateProjectSchema(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    system_prompt: str = Field(..., max_length=10000, min_length=100)



class ProjectDetailSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    system_prompt: str
    created_at: datetime
    updated_at: datetime



class UpdateProjectSchema(BaseModel):
    name: str | None = Field(None, min_length=3, max_length=50)
    system_prompt: str | None = Field(None, max_length=10000, min_length=100)
