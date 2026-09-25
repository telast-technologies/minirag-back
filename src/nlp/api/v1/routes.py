from uuid import UUID

from fastapi import APIRouter, Request, Response

from src.config.db.session import DBSession
from src.config.exceptions import BadRequestException, InternalServerException, NotFoundException
from src.config.loggers import Logger
from src.config.permissions import CurrentUserDep
from src.config.settings import settings
from src.nlp.api.v1.schemas import SearchRequest
from src.nlp.services.controllers import NLPController
from src.projects.crud import ProjectCRUD
from src.projects.models import Project
from src.utils.vectordb.schemas import RetrievedDocument

logger = Logger(name=__name__)
router = APIRouter(prefix="/api/v1/nlp", tags=["nlp"])


@router.post("/{project_id}/index_search", response_model=list[RetrievedDocument])
@settings.LIMITER.limit("50/minute")
async def search_index(
    request: Request,
    response: Response,
    project_id: UUID,
    db: DBSession,
    user: CurrentUserDep,
    body: SearchRequest,
):
    try:
        project_crud = ProjectCRUD()
        project = await project_crud.get(Project.id == project_id, Project.user_id == user.id)
        if not project:
            raise NotFoundException("Project not found")

        nlp_controller = NLPController(project=project, vectordb=request.app.vectordb, embedder=request.app.embedder)

        results = await nlp_controller.search(text=body.text, limit=body.limit)

        if not results or len(results) == 0:
            raise BadRequestException("No results found")

        return results

    except NotFoundException:
        raise
    except BadRequestException:
        raise
    except Exception:
        raise InternalServerException("Failed to get collection info")
