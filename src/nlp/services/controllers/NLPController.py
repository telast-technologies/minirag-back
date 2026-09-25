from typing import Any
from uuid import UUID

from src.knowledge_base.models import Asset
from src.nlp.services.controllers.EmbeddingController import EmbeddingController
from src.nlp.services.controllers.VectorDBController import VectorDBController
from src.projects.models import Project


class NLPController:
    def __init__(self, project: Project, vectordb: VectorDBController, embedder: EmbeddingController):
        self.project = project
        self.vectordb = vectordb
        self.embedder = embedder

    @property
    def embedding_size(self) -> int:
        return self.embedder.provider.embedding_size

    @property
    def collection_name(self) -> str:
        return self.vectordb.get_collection_name(self.project)

    async def index(self, assets: list[Asset]):
        return await self.embedder.embed(assets=assets)

    async def push_into_vectordb(self, embeddings: dict[UUID, dict[str, list[list[float]] | list[dict[str, Any]]]]):
        # step1: create collection if not exists
        _ = await self.vectordb.create_collection(
            collection_name=self.collection_name,
            embedding_size=self.embedding_size,
        )
        # step2: insert into vector db
        for asset, embedding in embeddings.items():
            _ = await self.vectordb.insert_many(
                collection_name=self.collection_name,
                texts=embedding["texts"],
                metadata=embedding["metadata"],
                vectors=embedding["vectors"],
                record_ids=embedding["chunk_ids"],
            )

    async def index_and_push_into_vectordb(self, assets: list[Asset]) -> list[UUID]:
        # step1: get text embedding vector
        embeddings = await self.index(assets=assets)
        # step2: push into vectordb
        _ = await self.push_into_vectordb(embeddings)

        return True
