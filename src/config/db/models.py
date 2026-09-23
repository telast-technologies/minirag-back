from sqlmodel import SQLModel

from src.knowledge_base.models import Asset  # noqa: F401
from src.projects.models import Project  # noqa: F401

# TODO: import all models
from src.users.models import User  # noqa: F401

metadata = SQLModel.metadata
