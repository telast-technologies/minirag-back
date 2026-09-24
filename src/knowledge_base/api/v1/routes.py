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
    ProcessAssetSchema,
)
from src.knowledge_base.crud import AssetCRUD
from src.knowledge_base.filters import AssetFilter
from src.knowledge_base.models import Asset
from src.knowledge_base.services.controllers.FileController import FileController
from src.knowledge_base.services.controllers.ProcessController import ProcessController
from src.knowledge_base.services.controllers.TextController import TextController
from src.knowledge_base.services.controllers.URLController import URLController
from src.projects.crud import ProjectCRUD
from src.projects.models import Project

logger = Logger(name=__name__)
router = APIRouter(prefix="/api/v1/assets", tags=["assets"])


@router.post("/{project_id}/create_texts", response_model=list[AssetDetailSchema], status_code=status.HTTP_201_CREATED)
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

        new_assets = []
        for content in body.content:
            # normalized_name is content without spaces and with underscore
            text_controller = TextController(content)
            asset = await text_controller.save(project)
            # add text to asset
            new_assets.append(asset)
        # process assests
        process_controller = ProcessController(new_assets)
        processed_assets = await process_controller.process()
        await db.commit()
        logger.info(f"Processed {len(processed_assets)} assets")
        return [AssetDetailSchema.model_validate(asset) for asset in processed_assets]
    except NotFoundException:
        await db.rollback()
        raise
    except BadRequestException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise InternalServerException("Failed to create assets")


@router.post("/{project_id}/create_urls", response_model=list[AssetDetailSchema], status_code=status.HTTP_201_CREATED)
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

        new_assets = []
        for content in body.content:
            # add url to assets
            url_controller = URLController(content=content)
            asset = await url_controller.save(project)
            new_assets.append(asset)
        # process assests
        process_controller = ProcessController(new_assets)
        processed_assets = await process_controller.process()
        await db.commit()
        logger.info(f"Processed {len(processed_assets)} assets")
        return [AssetDetailSchema.model_validate(asset) for asset in processed_assets]
    except NotFoundException:
        await db.rollback()
        raise
    except BadRequestException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise InternalServerException("Failed to create assets")


@router.post("/{project_id}/create_files", response_model=list[AssetDetailSchema], status_code=status.HTTP_201_CREATED)
@settings.LIMITER.limit("50/minute")
async def create_file_assets(
    request: Request,
    response: Response,
    project_id: UUID,
    db: DBSession,
    user: CurrentUserDep,
    body: CreateFileAssetSchema = Depends(CreateFileAssetSchema.as_form),
):
    project_crud = ProjectCRUD()
    try:
        project = await project_crud.get(Project.id == project_id, Project.user_id == user.id)
        if not project:
            raise NotFoundException("Project not found")

        new_assets = []
        for content in body.content:
            # normalized_name is content without spaces and with underscore
            file_controller = FileController(file=content)
            asset = await file_controller.save(project)
            # create file as asset
            new_assets.append(asset)
        # process the new assets
        process_controller = ProcessController(new_assets)
        processed_assets = await process_controller.process()
        await db.commit()
        logger.info(f"Processed {len(processed_assets)} assets")
        return [AssetDetailSchema.model_validate(asset) for asset in processed_assets]
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
    pagination_params: Params = Depends(),
):
    project_crud = ProjectCRUD()
    asset_crud = AssetCRUD()

    try:
        project = await project_crud.get(Project.id == project_id, Project.user_id == user.id)
        if not project:
            raise NotFoundException("Project not found")

        query = asset_crud.select(Asset.project_id == project_id)
        query = filters.filter(query)
        query = filters.sort(query)

        return await apaginate(db, query, pagination_params)
    except NotFoundException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise InternalServerException("Failed to get assets")


@router.post(
    "/{project_id}/process_assets", response_model=list[AssetDetailSchema], status_code=status.HTTP_201_CREATED
)
async def process_assets(
    request: Request,
    response: Response,
    project_id: UUID,
    db: DBSession,
    user: CurrentUserDep,
    body: ProcessAssetSchema,
):
    project_crud = ProjectCRUD()
    asset_crud = AssetCRUD()

    try:
        project = await project_crud.get(Project.id == project_id, Project.user_id == user.id)
        if not project:
            raise NotFoundException("Project not found")

        assets = [
            asset
            for asset in body.asset_ids
            if await asset_crud.get(Asset.id == asset.id, Asset.project_id == project_id)
        ]
        if not assets:
            assets = [asset for asset in await asset_crud.list(Asset.project_id == project_id)]
        process_controller = ProcessController(assets)
        processed_assets = await process_controller.process(body.chunk_size, body.chunk_overlap)
        return processed_assets
    except NotFoundException:
        await db.rollback()
        raise
    except BadRequestException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise InternalServerException("Failed to process asset")
