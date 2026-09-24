from src.knowledge_base.models import Asset, AssetChunk
from src.utils.crud import CRUDBase


class AssetCRUD(CRUDBase[Asset]):
    model = Asset


class AssetChunkCRUD(CRUDBase[AssetChunk]):
    model = AssetChunk
