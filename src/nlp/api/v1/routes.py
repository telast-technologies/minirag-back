from uuid import UUID

from fastapi import APIRouter, Request, Response

from src.config.db.session import DBSession
from src.config.exceptions import BadRequestException, InternalServerException, NotFoundException
from src.config.loggers import Logger
from src.config.permissions import CurrentUserDep
from src.config.settings import settings
from src.nlp.api.v1.schemas import AnswerSchema, SearchRequest
from src.nlp.services.controllers import GenerationController
from src.projects.crud import ProjectCRUD
from src.projects.models import Project
from src.utils.llm.generation.factory import GenerationLLMProviderFactory

logger = Logger(name=__name__)
router = APIRouter(prefix="/api/v1/nlp", tags=["nlp"])


@router.post("/{project_id}/index_answer", response_model=AnswerSchema)
@settings.LIMITER.limit("50/minute")
async def answer_rag(
    request: Request, response: Response, db: DBSession, user: CurrentUserDep, project_id: UUID, body: SearchRequest
):
    try:
        project_crud = ProjectCRUD()
        project = await project_crud.get(Project.id == project_id, Project.user_id == user.id)
        if not project:
            raise NotFoundException("Project not found")

        # setup generation model
        generation_model_id = project.generation_model_id
        generation_backend = settings.GENERATION_BACKEND(generation_model_id)
        generation_api_key = settings.GENERATION_API_KEY(generation_backend)
        generation_client = GenerationLLMProviderFactory(generation_backend).create(
            {
                "api_key": generation_api_key,
                "generation_model_id": generation_model_id,
                "default_generation_max_output_tokens": settings.DAFAULT_GENERATION_MAX_TOKENS,
                "default_generation_temperature": settings.DEFAULT_GENERATION_TEMPERATURE,
                "default_input_max_characters": settings.DAFAULT_INPUT_MAX_CHARACTERS,
            }
        )
        generator = GenerationController(generation_client)

        nlp_controller = request.app.nlp_controller
        if (
            not nlp_controller.generator
            or nlp_controller.generator.provider.generation_model_id != generation_model_id
        ):
            nlp_controller.set_generator(generator)
        answer, full_prompt, chat_history = await nlp_controller.answer(project, query=body.text, limit=body.limit)

        if not answer:
            raise BadRequestException("No results found")

        return {"answer": answer, "full_prompt": full_prompt, "chat_history": chat_history}

    except NotFoundException:
        raise
    except BadRequestException:
        raise
    except Exception:
        raise InternalServerException("Failed to get collection info")
