from src.config.loggers import Logger
from src.knowledge_base.crud import AssetCRUD
from src.knowledge_base.enums import AssetStatus
from src.knowledge_base.models import Asset

logger = Logger(__name__)


class AssetService:
    def __init__(self, asset: Asset):
        self.asset = asset

    async def update_status(self, status: AssetStatus):
        asset_crud = AssetCRUD()
        updated_asset = await asset_crud.update(self.asset, {"status": status})
        logger.info(f"Asset: {updated_asset.id} updated to status: {status}")
        return updated_asset
