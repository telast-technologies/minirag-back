from src.projects.models import Project
from src.utils.crud import CRUDBase


class ProjectCRUD(CRUDBase[Project]):
    model = Project