import json
from typing import Any
from uuid import UUID

from src.projects.models import Project


class VectorDBController:

    def __init__(self, session):
        self.session = session

    def get_collection_name(self, project: Project) -> str:
        return f"{self.session.table_prefix}_{self.session.default_vector_size}_{project.id}".strip()
    
    async def delete_collection(self, project: Project):
        collection_name = self.get_collection_name(project)
        return await self.session.delete_collection(collection_name=collection_name)
    
    async def get_collection_info(self, project: Project):
        collection_name = self.get_collection_name(project)
        collection_info = await self.session.get_collection_info(collection_name=collection_name)

        return json.loads(
            json.dumps(collection_info, default=lambda x: x.__dict__)
        )

    async def create_collection(self, collection_name: str, embedding_size: int):
        return await self.session.create_collection(collection_name=collection_name, embedding_size=embedding_size)

    
    async def insert_many(
        self,
        collection_name: str,
        texts: list[str],
        metadata: list[dict[str, Any]],
        vectors: list[list[float]],
        record_ids: list[UUID],
    ):
        return await self.session.insert_many(
            collection_name=collection_name,
            texts=texts,
            metadata=metadata,
            vectors=vectors,
            record_ids=record_ids,
        )

    