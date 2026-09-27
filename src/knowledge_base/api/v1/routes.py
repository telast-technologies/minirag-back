from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi_filter import FilterDepends
from fastapi_pagination import Page, Params
from fastapi_pagination.ext.sqlalchemy import apaginate

from src.config.db.session import DBSession
from src.config.exceptions import BadRequestException, InternalServerException, NotFoundException
from src.config.loggers import Logger
from src.config.permissions import CurrentUserDep
from src.config.settings import settings
from src.knowledge_base.api.v1.schemas import (
    AssetDetailSchema,
    CreateFileAssetSchema,
    CreateTextAssetSchema,
    CreateURlAssetSchema,
    EmbedAssetSchema,
    ProcessAssetSchema,
)
from src.knowledge_base.crud import AssetCRUD
from src.knowledge_base.filters import AssetFilter
from src.knowledge_base.models import Asset
from src.knowledge_base.services.controllers.FileController import FileController
from src.knowledge_base.services.controllers.TextController import TextController
from src.knowledge_base.services.controllers.URLController import URLController
from src.projects.crud import ProjectCRUD
from src.projects.models import Project
from src.workers.services.controllers import WorkflowController

logger = Logger(name=__name__)
router = APIRouter(prefix="/api/v1/assets", tags=["assets"])


@router.post("/{project_id}/create_texts", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
@settings.LIMITER.limit("50/minute")
async def create_text_assets(
    request: Request,
    response: Response,
    project_id: UUID,
    db: DBSession,
    user: CurrentUserDep,
    body: CreateTextAssetSchema,
):
    project_crud = ProjectCRUD()
    try:
        project = await project_crud.get(Project.id == project_id, Project.user_id == user.id)
        if not project:
            raise NotFoundException("Project not found")

        new_assets = [await TextController(content=content).save(project) for content in body.content]
        await db.commit()

        # trigger workflow
        workflow_status = WorkflowController.trigger_process_and_index(project_id=project_id, asset_ids=new_assets)

        logger.info(f"Triggered background processing for {len(new_assets)} text assets")
        return {"workflow": workflow_status, "created_assets_count": len(new_assets)}

    except NotFoundException:
        await db.rollback()
        raise
    except BadRequestException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise InternalServerException("Failed to create assets")


@router.post("/{project_id}/create_urls", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
@settings.LIMITER.limit("50/minute")
async def create_url_assets(
    request: Request,
    response: Response,
    project_id: UUID,
    db: DBSession,
    user: CurrentUserDep,
    body: CreateURlAssetSchema,
):
    project_crud = ProjectCRUD()

    try:
        project = await project_crud.get(Project.id == project_id, Project.user_id == user.id)
        if not project:
            raise NotFoundException("Project not found")

        new_assets = [await URLController(content=content).save(project) for content in body.content]
        await db.commit()

        # trigger workflow
        workflow_status = WorkflowController.trigger_process_and_index(project_id=project_id, asset_ids=new_assets)

        logger.info(f"Triggered background processing for {len(new_assets)} URL assets")
        return {"workflow": workflow_status, "created_assets_count": len(new_assets)}

    except NotFoundException:
        await db.rollback()
        raise
    except BadRequestException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise InternalServerException("Failed to create assets")


@router.post("/{project_id}/create_files", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
@settings.LIMITER.limit("50/minute")
async def create_file_assets(
    request: Request,
    response: Response,
    project_id: UUID,
    db: DBSession,
    # user: CurrentUserDep,
    body: CreateFileAssetSchema = Depends(CreateFileAssetSchema.as_form),
):
    project_crud = ProjectCRUD()
    try:
        project = await project_crud.get(Project.id == project_id)
        if not project:
            raise NotFoundException("Project not found")

        new_assets = [await FileController(file=content).save(project) for content in body.content]
        await db.commit()

        # trigger workflow
        workflow_status = WorkflowController.trigger_process_and_index(project_id=project_id, asset_ids=new_assets)

        logger.info(f"Triggered background processing for {len(new_assets)} file assets")
        return {"workflow": workflow_status, "created_assets_count": len(new_assets)}

    except NotFoundException:
        await db.rollback()
        raise
    except BadRequestException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise InternalServerException("Failed to create assets")


@router.get("/{project_id}/assets", response_model=Page[AssetDetailSchema], status_code=status.HTTP_200_OK)
async def get_assets(
    request: Request,
    response: Response,
    project_id: UUID,
    db: DBSession,
    user: CurrentUserDep,
    filters: AssetFilter = FilterDepends(AssetFilter),
    pagination: Params = Depends(),
):
    # هذه الدالة كما هي لأنها مخصصة فقط للاستعلام عن البيانات
    project_crud = ProjectCRUD()
    asset_crud = AssetCRUD()

    try:
        project = await project_crud.get(Project.id == project_id, Project.user_id == user.id)
        if not project:
            raise NotFoundException("Project not found")

        query = asset_crud.select(Asset.project_id == project_id)
        query = filters.filter(query)
        query = filters.sort(query)

        return await apaginate(db, query, pagination, subquery_count=True, unwrap_mode="auto")
    except NotFoundException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise InternalServerException("Failed to get assets")


@router.post("/{project_id}/process_assets", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def process_assets(
    request: Request,
    response: Response,
    project_id: UUID,
    db: DBSession,
    user: CurrentUserDep,
    body: ProcessAssetSchema,
):
    project_crud = ProjectCRUD()

    try:
        project = await project_crud.get(Project.id == project_id, Project.user_id == user.id)
        if not project:
            raise NotFoundException("Project not found")

        # trigger workflow
        workflow_status = WorkflowController.trigger_process_and_index(
            project_id=project_id,
            asset_ids=body.asset_ids,
            chunk_size=body.chunk_size,
            chunk_overlap=body.chunk_overlap,
        )

        return {"workflow": workflow_status, "message": "Processing triggered"}
    except NotFoundException:
        await db.rollback()
        raise
    except BadRequestException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise InternalServerException("Failed to process asset")


@router.post("/{project_id}/index_assets", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
@settings.LIMITER.limit("50/minute")
async def index_assets(
    request: Request,
    response: Response,
    project_id: UUID,
    db: DBSession,
    user: CurrentUserDep,
    body: EmbedAssetSchema,
):
    try:
        project_crud = ProjectCRUD()

        project = await project_crud.get(
            Project.id == project_id,
            Project.user_id == user.id,
        )
        if not project:
            raise NotFoundException("Project not found")

        # trigger workflow
        workflow_status = WorkflowController.trigger_index_only(project_id=project_id, asset_ids=body.asset_ids)

        return {"workflow": workflow_status, "message": "Indexing triggered"}
    except NotFoundException:
        await db.rollback()
        raise
    except BadRequestException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise InternalServerException("Failed to index asset")
