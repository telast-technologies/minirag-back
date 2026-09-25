from fastapi import UploadFile

from src.config.hashers import hash_text_service
from src.config.storage import S3Storage
from src.knowledge_base.crud import AssetCRUD
from src.knowledge_base.enums import AssetType
from src.knowledge_base.models import Asset
from src.projects.models import Project


class FileController:
    file_scale: int = 1024 * 1024

    def __init__(self, file: UploadFile, *args, **kwargs):
        self.file = file
        self.crud = AssetCRUD()

    async def save(self, project: Project) -> Asset:
        name = f"{project.id}_{hash_text_service.hash(self.file.filename)}_{self.file.filename}"

        storage_key = S3Storage.write(self.file.file, name)

        return await self.crud.create(
            {
                "project_id": project.id,
                "name": name,
                "type": AssetType.FILE.value,
                "asset_metadata": self.extract_metadata(),
                "content": storage_key,
            }
        )

    def extract_metadata(self) -> dict:
        return {
            "size": self.file.size,
            "original_name": self.file.filename,
            "content_type": self.file.content_type,
        }
