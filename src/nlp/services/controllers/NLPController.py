from typing import Any
from uuid import UUID

from src.knowledge_base.crud import AssetCRUD
from src.knowledge_base.enums import AssetStatus
from src.knowledge_base.models import Asset
from src.knowledge_base.services.assets import AssetService
from src.nlp.services.controllers.EmbeddingController import EmbeddingController
from src.nlp.services.controllers.VectorDBController import VectorDBController
from src.projects.models import Project
from src.utils.llm.embedding.enums import EmbeddingDocumentType


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

    async def index_assets(self, assets: list[Asset]):
        return await self.embedder.embed_assets(assets=assets)

    async def push_into_vectordb(self, embeddings: dict[UUID, dict[str, list[list[float]] | list[dict[str, Any]]]]):
        # step1: create collection if not exists
        _ = await self.vectordb.create_collection(
            collection_name=self.collection_name,
            embedding_size=self.embedding_size,
        )
        # step2: insert into vector db
        asset_curd = AssetCRUD()
        for asset_id, embedding in embeddings.items():
            asset = await asset_curd.get(Asset.id == asset_id)
            asset_service = AssetService(asset)
            asset_ids = [asset_id] * len(embedding["chunk_ids"])
            _ = await self.vectordb.insert_many(
                collection_name=self.collection_name,
                texts=embedding["texts"],
                metadata=embedding["metadata"],
                vectors=embedding["vectors"],
                chunk_ids=embedding["chunk_ids"],
                asset_ids=asset_ids,
            )
            await asset_service.update_status(AssetStatus.INDEXED)

    async def index_and_push_into_vectordb(self, assets: list[Asset]) -> list[UUID]:
        # step1: get text embedding vector
        embeddings = await self.index_assets(assets=assets)
        # step2: push into vectordb
        _ = await self.push_into_vectordb(embeddings)

        return True

    async def search(self, text: str, limit: int):
        # embed the query text commming from the user query
        vector = await self.embedder.embed_text(text=text, document_type=EmbeddingDocumentType.QUERY.value)

        if not vector or len(vector) == 0:
            return False

        # get the semantically similar texts from the vector db
        results = await self.vectordb.search_by_vector(
            collection_name=self.collection_name,
            vector=vector,
            limit=limit,
        )
        # return results comming from the vector db
        return [result for result in results if result.score >= 0.5]
