from uuid import UUID

from fastapi import APIRouter, Request, Response, status

from src.config.db.session import DBSession
from src.config.exceptions import BadRequestException, InternalServerException, NotFoundException
from src.config.loggers import Logger
from src.config.permissions import CurrentUserDep
from src.config.settings import settings
from src.knowledge_base.crud import AssetCRUD
from src.knowledge_base.enums import AssetStatus
from src.knowledge_base.models import Asset
from src.nlp.api.v1.schemas import EmbedAssetSchema
from src.nlp.services.controllers import NLPController
from src.projects.crud import ProjectCRUD
from src.projects.models import Project

logger = Logger(name=__name__)
router = APIRouter(prefix="/api/v1/nlp", tags=["nlp"])


@router.get("/get_generation_models", response_model=list[str])
@settings.LIMITER.limit("50/minute")
async def get_generation_models(
    request: Request,
    response: Response,
    user: CurrentUserDep,
):
    return settings.GENERATION_MODEL_IDS


@router.post("/{project_id}/index_assets", response_model=list[Asset], status_code=status.HTTP_201_CREATED)
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
        asset_crud = AssetCRUD()

        project = await project_crud.get(
            Project.id == project_id,
            Project.user_id == user.id,
        )
        if not project:
            raise NotFoundException("Project not found")

        assets = [
            await asset_crud.get(
                Asset.id == asset_id, Asset.project_id == project_id, Asset.status == AssetStatus.PROCESSED
            )
            for asset_id in body.asset_ids
        ]
        await db.commit()
        # embed the new assets
        nlp_controller = NLPController(project=project, vectordb=request.app.vectordb, embedder=request.app.embedder)
        await nlp_controller.index_and_push_into_vectordb(assets)
        await db.commit()
        return assets
    except NotFoundException:
        await db.rollback()
        raise
    except BadRequestException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise InternalServerException("Failed to process asset")
