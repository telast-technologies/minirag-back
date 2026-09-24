from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi_pagination import Page, Params
from fastapi_pagination.ext.sqlalchemy import apaginate

from src.config.db.session import DBSession
from src.config.exceptions import InternalServerException, NotFoundException
from src.config.loggers import Logger
from src.config.permissions import CurrentUserDep
from src.config.settings import settings
from src.projects.api.v1.schemas import ModifyProjectSchema, ProjectDetailSchema
from src.projects.crud import ProjectCRUD
from src.projects.models import Project

logger = Logger(name=__name__)
router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.post("/create", response_model=ProjectDetailSchema, status_code=status.HTTP_201_CREATED)
@settings.LIMITER.limit("50/minute")
async def create_project(
    request: Request,
    response: Response,
    db: DBSession,
    user: CurrentUserDep,
    body: ModifyProjectSchema,
):
    project_crud = ProjectCRUD()
    data = body.model_dump()

    try:
        new_project = await project_crud.create({"user_id": user.id, **data})
        await db.commit()
        await db.refresh(new_project)
        logger.info(f"Created new project: {new_project.name}")
        return new_project
    except Exception:
        await db.rollback()
        raise InternalServerException("Failed to create project")


@router.get("/get_projects", response_model=Page[ProjectDetailSchema])
@settings.LIMITER.limit("50/minute")
async def get_projects(
    request: Request,
    response: Response,
    db: DBSession,
    user: CurrentUserDep,
    pagination_params: Params = Depends(),
):
    try:
        project_crud = ProjectCRUD()
        projects = project_crud.select(
            Project.user_id == user.id,
        )
        return await apaginate(db, projects, pagination_params, subquery_count=True, unwrap_mode="auto")
    except Exception:
        await db.rollback()
        raise InternalServerException("Failed to get projects")


@router.patch("/update/{project_id}", response_model=ProjectDetailSchema)
@settings.LIMITER.limit("50/minute")
async def update_project(
    request: Request,
    response: Response,
    project_id: UUID,
    db: DBSession,
    user: CurrentUserDep,
    body: ModifyProjectSchema,
):
    project_crud = ProjectCRUD()
    data = body.model_dump(exclude_unset=True, exclude_none=True)

    try:
        project = await project_crud.get(Project.id == project_id, Project.user_id == user.id)
        if not project:
            raise NotFoundException("Project not found")

        updated_project = await project_crud.update(project, data)
        await db.commit()
        await db.refresh(updated_project)
        logger.info(f"Updated project: {updated_project.name}")
        return updated_project
    except NotFoundException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise InternalServerException("Failed to update project")
