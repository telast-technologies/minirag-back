import asyncio
from uuid import UUID

from src.config.db.session import get_db
from src.config.loggers import Logger
from src.knowledge_base.crud import AssetCRUD
from src.knowledge_base.enums import AssetStatus
from src.knowledge_base.models import Asset
from src.nlp.factory import NLPFactory
from src.projects.crud import ProjectCRUD
from src.projects.models import Project
from src.workers.celery_app import celery_app

logger = Logger(name=__name__)


@celery_app.task(bind=True, name="tasks.index_assets")
def index_assets_task(self, project_id: str, asset_ids: list[str]):
    return asyncio.run(_async_index_assets(project_id, asset_ids))


async def _async_index_assets(project_id_str: str, asset_ids_str: list[str]):
    project_id = UUID(project_id_str)
    asset_ids = [UUID(aid) for aid in asset_ids_str]

    result = None  # 1. تعريف متغير النتيجة قبل اللوب

    async for db in get_db():
        try:
            project_crud = ProjectCRUD()
            asset_crud = AssetCRUD()

            project = await project_crud.get(Project.id == project_id)

            assets = [
                await asset_crud.get(
                    Asset.id == asset_id, Asset.project_id == project_id, Asset.status == AssetStatus.PROCESSED
                )
                for asset_id in asset_ids
            ]
            assets = [a for a in assets if a]

            if not assets:
                result = {"status": "NO_ASSETS_TO_INDEX"}
                break  # 2. خروج آمن بدلاً من return المباشر

            nlp_controller = await NLPFactory.get_controller()
            await nlp_controller.index_and_push_into_vectordb(project, assets)
            await db.commit()

            result = {"status": "SUCCESS", "indexed_assets_count": len(assets)}
            break  # 3. خروج آمن بعد النجاح

        except Exception as e:
            await db.rollback()
            logger.error(f"Error in index_assets_task: {e}")
            raise

    return result  # 4. إرجاع النتيجة من خارج اللوب تماماً
