from src.config.hashers import HashTextService
from src.knowledge_base.crud import AssetCRUD
from src.knowledge_base.enums import AssetType
from src.projects.models import Project


class TextController:
    def __init__(self, content: str):
        self.content = content
        self.crud = AssetCRUD()

    async def save(self, project: Project):
        hasher = HashTextService()
        name = hasher.hash(self.content)
        return await self.crud.create(
            {
                "project_id": project.id,
                "name": name,
                "type": AssetType.TEXT.value,
                "asset_metadata": self.extract_metadata(),
                "content": self.content,
            }
        )

    def extract_metadata(self) -> dict:
        return {}
