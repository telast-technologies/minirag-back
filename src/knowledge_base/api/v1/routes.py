from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi_filter import FilterDepends
from fastapi_pagination import Page, Params
from fastapi_pagination.ext.sqlalchemy import apaginate

from src.config.db.session import DBSession
from src.config.exceptions import InternalServerException, NotFoundException
from src.config.hashers import HashTextService
from src.config.loggers import Logger
from src.config.permissions import CurrentUserDep
from src.config.settings import settings
from src.config.storage import S3Storage
from src.knowledge_base.api.v1.schemas import (
    AssetDetailSchema,
    CreateFileAssetSchema,
    CreateTextAssetSchema,
    CreateURlAssetSchema,
)
from src.knowledge_base.crud import AssetCRUD
from src.knowledge_base.enums import AssetType
from src.knowledge_base.filters import AssetFilter
from src.knowledge_base.models import Asset
from src.projects.crud import ProjectCRUD
from src.projects.models import Project

logger = Logger(name=__name__)
router = APIRouter(prefix="/api/v1/assets", tags=["assets"])


@router.post("/{project_id}/create_text", response_model=list[AssetDetailSchema], status_code=status.HTTP_201_CREATED)
@settings.LIMITER.limit("50/minute")
async def create_text_assets(
    request: Request,
    response: Response,
    db: DBSession,
    project_id: UUID,
    user: CurrentUserDep,
    body: list[CreateTextAssetSchema],
):
    project_crud = ProjectCRUD(db)
    asset_crud = AssetCRUD(db)

    hasher = HashTextService()
    try:
        project = await project_crud.get(Project.id == project_id, Project.user_id == user.id)
        if not project:
            raise NotFoundException("Project not found")

        new_assets = []
        for asset in body:
            # normalized_name is content without spaces and with underscore
            name = hasher.hash(asset.content)
            # add text to asset
            new_assets.append(
                await asset_crud.create(
                    {
                        "project_id": project.id,
                        "name": name,
                        "type": AssetType.TEXT.value,
                        "asset_metadata": {},
                        **asset.model_dump(exclude_unset=True, exclude_none=True),
                    }
                )
            )
        await db.commit()
        # TODO: chunk the assets content and save the chunks
        logger.info(f"Created new assets: {new_assets}")
        return [AssetDetailSchema.model_validate(asset) for asset in new_assets]
    except NotFoundException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise InternalServerException("Failed to create assets")


@router.post("/{project_id}/create_url", response_model=list[AssetDetailSchema], status_code=status.HTTP_201_CREATED)
@settings.LIMITER.limit("50/minute")
async def create_url_assets(
    request: Request,
    response: Response,
    db: DBSession,
    project_id: UUID,
    user: CurrentUserDep,
    body: list[CreateURlAssetSchema],
):
    project_crud = ProjectCRUD(db)
    asset_crud = AssetCRUD(db)

    hasher = HashTextService()
    try:
        project = await project_crud.get(Project.id == project_id, Project.user_id == user.id)
        if not project:
            raise NotFoundException("Project not found")

        new_assets = []
        for asset in body:
            # normalized_name is content without spaces and with underscore
            name = hasher.hash(asset.content)
            # add url to assets
            new_assets.append(
                await asset_crud.create(
                    {
                        "project_id": project.id,
                        "name": name,
                        "type": AssetType.URL.value,
                        "asset_metadata": {},
                        **asset.model_dump(exclude_unset=True, exclude_none=True),
                    }
                )
            )
        await db.commit()
        # TODO: chunk the assets content and save the chunks
        logger.info(f"Created new assets: {new_assets}")
        return [AssetDetailSchema.model_validate(asset) for asset in new_assets]
    except NotFoundException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise InternalServerException("Failed to create assets")


@router.post("/{project_id}/create_file", response_model=list[AssetDetailSchema], status_code=status.HTTP_201_CREATED)
@settings.LIMITER.limit("50/minute")
async def create_file_assets(
    request: Request,
    response: Response,
    db: DBSession,
    project_id: UUID,
    user: CurrentUserDep,
    body: CreateFileAssetSchema = Depends(CreateFileAssetSchema.as_form),
):
    project_crud = ProjectCRUD(db)
    asset_crud = AssetCRUD(db)

    hasher = HashTextService()
    try:
        project = await project_crud.get(Project.id == project_id, Project.user_id == user.id)
        if not project:
            raise NotFoundException("Project not found")

        new_assets = []
        for asset in body.content:
            # normalized_name is content without spaces and with underscore
            name = f"{project.id}_{hasher.hash(asset.filename)}_{asset.filename}"
            # writ to r2 then store key
            storage_key = S3Storage.write(asset.file, name)
            # create file as asset
            new_assets.append(
                await asset_crud.create(
                    {
                        "project_id": project.id,
                        "name": name,
                        "type": AssetType.FILE.value,
                        "asset_metadata": {
                            "size": asset.size,
                            "original_name": asset.filename,
                            "content_type": asset.content_type,
                        },
                        "content": storage_key,
                    }
                )
            )
        await db.commit()
        # # TODO: chunk the assets content and save the chunks
        logger.info(f"Created new assets: {new_assets}")
        return [AssetDetailSchema.model_validate(asset) for asset in new_assets]
    except NotFoundException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise InternalServerException("Failed to create assets")


@router.get("/{project_id}/assets", response_model=Page[AssetDetailSchema], status_code=status.HTTP_200_OK)
async def get_assets(
    request: Request,
    response: Response,
    db: DBSession,
    project_id: UUID,
    user: CurrentUserDep,
    filters: AssetFilter = FilterDepends(AssetFilter),
    pagination_params: Params = Depends(),
):
    project_crud = ProjectCRUD(db)
    asset_crud = AssetCRUD(db)

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
