from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import StreamingResponse
from fastapi_pagination import Page, Params
from fastapi_pagination.ext.sqlalchemy import apaginate

from src.config.db.session import DBSession
from src.config.exceptions import BadRequestException, InternalServerException, NotFoundException
from src.config.hashers import hash_text_service
from src.config.loggers import Logger
from src.config.permissions import CurrentUserDep
from src.config.settings import settings
from src.nlp.api.v1.schemas import (
    CreateSessionSchema,
    MessageDetailSchema,
    SearchRequest,
    SessionDetailSchema,
    UpdateSessionSchema,
)
from src.nlp.crud import MessageCRUD, SessionCRUD
from src.nlp.models import Message, Session
from src.nlp.services.controllers import GenerationController
from src.nlp.services.messages import MessageService
from src.projects.crud import ProjectCRUD
from src.projects.models import Project
from src.utils.llm.generation.factory import GenerationLLMProviderFactory

logger = Logger(name=__name__)
router = APIRouter(prefix="/api/v1/nlp", tags=["nlp"])


@router.post("{project_id}/create_session", response_model=SessionDetailSchema, status_code=status.HTTP_201_CREATED)
@settings.LIMITER.limit("50/minute")
async def create_session(
    request: Request,
    response: Response,
    project_id: UUID,
    db: DBSession,
    user: CurrentUserDep,
    body: CreateSessionSchema,
):
    try:
        project_crud = ProjectCRUD()
        project = await project_crud.get(Project.id == project_id, Project.user_id == user.id)
        if not project:
            raise NotFoundException("Project not found")

        data = body.model_dump(exclude_unset=True, exclude_none=True)
        if not data.get("generation_model_id"):
            data["generation_model_id"] = project.generation_model_id
        data["project_id"] = project_id
        data["user_id"] = user.id
        session_crud = SessionCRUD()
        session = await session_crud.create(data)
        return session
    except NotFoundException:
        raise
    except BadRequestException:
        raise
    except Exception:
        raise InternalServerException("Failed to create session")


@router.get("/{project_id}/get_sessions", response_model=Page[SessionDetailSchema])
@settings.LIMITER.limit("50/minute")
async def get_sessions(
    request: Request,
    response: Response,
    project_id: UUID,
    db: DBSession,
    user: CurrentUserDep,
    pagination: Params = Depends(),
):
    try:
        project_crud = ProjectCRUD()
        project = await project_crud.get(Project.id == project_id, Project.user_id == user.id)
        if not project:
            raise NotFoundException("Project not found")

        session_crud = SessionCRUD()
        query = session_crud.select(Session.project_id == project_id, Session.user_id == user.id)
        return await apaginate(db, query, pagination, subquery_count=True, unwrap_mode="auto")
    except NotFoundException:
        raise
    except BadRequestException:
        raise
    except Exception:
        raise InternalServerException("Failed to list sessions")


@router.patch("/{session_id}/update_session", response_model=SessionDetailSchema)
@settings.LIMITER.limit("50/minute")
async def update_session(
    request: Request,
    response: Response,
    session_id: UUID,
    db: DBSession,
    user: CurrentUserDep,
    body: UpdateSessionSchema,
):
    try:
        session_crud = SessionCRUD()
        session = await session_crud.get(Session.id == session_id, Session.user_id == user.id)
        if not session:
            raise NotFoundException("Session not found")

        data = body.model_dump(exclude_unset=True, exclude_none=True)
        session_updated = await session_crud.update(session, data)
        return session_updated
    except NotFoundException:
        raise
    except BadRequestException:
        raise
    except Exception:
        raise InternalServerException("Failed to update session")


@router.post("/{project_id}/ask", status_code=status.HTTP_200_OK, response_class=StreamingResponse)
@settings.LIMITER.limit("50/minute")
async def ask(
    request: Request, response: Response, db: DBSession, user: CurrentUserDep, project_id: UUID, body: SearchRequest
):
    try:
        project_crud = ProjectCRUD()
        project = await project_crud.get(Project.id == project_id, Project.user_id == user.id)
        if not project:
            raise NotFoundException("Project not found")

        session_crud = SessionCRUD()
        session = None
        if body.session:
            session = await session_crud.get(Session.id == body.session, Session.project_id == project.id)
            if not session:
                raise NotFoundException("Session not found")
        else:
            session = await session_crud.create(
                {
                    "project_id": project.id,
                    "user_id": user.id,
                    "generation_model_id": project.generation_model_id,
                    "name": f"Session_{hash_text_service.hash(body.text)}_{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                }
            )
        # setup generation model
        generation_model_id = session.generation_model_id
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

        answer = await MessageService(session).ask(request=request, content=body.text, nlp_controller=nlp_controller)
        await db.commit()
        return StreamingResponse(answer(), media_type="text/event-stream")
    except NotFoundException:
        raise
    except BadRequestException:
        raise
    except Exception:
        raise InternalServerException("Failed to get collection info")


@router.get("/{session_id}/get_messages", response_model=Page[MessageDetailSchema])
@settings.LIMITER.limit("100/minute")
async def get_messages(
    request: Request,
    response: Response,
    session_id: UUID,
    user: CurrentUserDep,
    db: DBSession,
    pagination: Params = Depends(),
):
    session_crud = SessionCRUD()
    session = await session_crud.get(Session.id == session_id, Session.user_id == user.id)
    if not session:
        raise NotFoundException("Session not found")

    message_crud = MessageCRUD()
    query = message_crud.select(Message.session_id == session_id)
    return await apaginate(db, query, pagination, subquery_count=True, unwrap_mode="auto")
