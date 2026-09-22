from src.knowledge_base.models import Asset
from src.utils.crud import CRUDBase


class AssetCRUD(CRUDBase[Asset]):
    model = Asset
