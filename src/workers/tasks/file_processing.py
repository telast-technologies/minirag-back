import asyncio
from uuid import UUID

from src.config.db.session import get_db
from src.config.loggers import Logger
from src.knowledge_base.crud import AssetCRUD
from src.knowledge_base.enums import AssetStatus
from src.knowledge_base.models import Asset
from src.knowledge_base.services.controllers.ProcessController import ProcessController
from src.workers.celery_app import celery_app

logger = Logger(name=__name__)


@celery_app.task(bind=True, name="tasks.process_assets")
def process_assets_task(
    self, project_id: str, asset_ids: list[str], chunk_size: int = None, chunk_overlap: int = None
):
    return asyncio.run(_async_process_assets(project_id, asset_ids, chunk_size, chunk_overlap))


async def _async_process_assets(project_id_str: str, asset_ids_str: list[str], chunk_size: int, chunk_overlap: int):
    project_id = UUID(project_id_str)
    asset_ids = [UUID(aid) for aid in asset_ids_str]

    result = None

    async for db in get_db():
        try:
            asset_crud = AssetCRUD(db)

            assets = []
            for asset_id in asset_ids:
                asset = await asset_crud.get(
                    Asset.id == asset_id, Asset.project_id == project_id, Asset.status == AssetStatus.PENDING
                )
                if asset:
                    assets.append(asset)

            if not assets:
                result = {"status": "NO_ASSETS_TO_PROCESS"}
                break

            process_controller = ProcessController(assets)
            process_kwargs = {}
            if chunk_size:
                process_kwargs["chunk_size"] = chunk_size
            if chunk_overlap:
                process_kwargs["chunk_overlap"] = chunk_overlap

            await process_controller.process(**process_kwargs)
            await db.commit()

            result = {"status": "SUCCESS", "processed_assets_count": len(assets)}
            break

        except Exception as e:
            await db.rollback()
            logger.error(f"Error in process_assets_task: {e}")
            raise

    return result
