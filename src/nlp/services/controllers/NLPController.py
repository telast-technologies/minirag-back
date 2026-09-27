from typing import Any
from uuid import UUID

from src.config.loggers import Logger
from src.knowledge_base.crud import AssetCRUD
from src.knowledge_base.enums import AssetStatus
from src.knowledge_base.models import Asset
from src.knowledge_base.services.assets import AssetService
from src.nlp.services.controllers import EmbeddingController, GenerationController, VectorDBController
from src.nlp.templates import document_template, header_template
from src.projects.models import Project
from src.utils.llm.embedding.enums import EmbeddingDocumentType
from src.utils.llm.generation.enums import GenerationRolesEnums

logger = Logger(__name__)


class NLPController:
    def __init__(
        self,
        vectordb: VectorDBController,
        embedder: EmbeddingController,
        generator: GenerationController | None = None,
    ):
        self.vectordb = vectordb
        self.embedder = embedder
        self.generator = generator

    @property
    def embedding_size(self) -> int:
        if not self.embedder:
            raise ValueError("Embedder not set")
        return self.embedder.provider.embedding_size

    def get_system_prompt(self, project: Project) -> str:
        return project.system_prompt

    def get_collection_name(self, project: Project) -> str:
        return self.vectordb.get_collection_name(project)

    def set_generator(self, generator: GenerationController):
        self.generator = generator

    def set_embedder(self, embedder: EmbeddingController):
        self.embedder = embedder

    def set_vectordb(self, vectordb: VectorDBController):
        self.vectordb = vectordb

    async def index_assets(self, assets: list[Asset]):
        if not self.embedder:
            raise ValueError("Embedder not set")
        return await self.embedder.embed_assets(assets=assets)

    async def push_into_vectordb(
        self, project: Project, embeddings: dict[UUID, dict[str, list[list[float]] | list[dict[str, Any]]]]
    ):
        if not self.vectordb:
            raise ValueError("VectorDB not set")
        # step1: create collection if not exists
        _ = await self.vectordb.session.create_collection(
            collection_name=self.get_collection_name(project),
            embedding_size=self.embedding_size,
        )
        # step2: insert into vector db
        asset_curd = AssetCRUD()
        for asset_id, embedding in embeddings.items():
            asset = await asset_curd.get(Asset.id == asset_id)
            asset_service = AssetService(asset)
            asset_ids = [asset_id] * len(embedding["chunk_ids"])
            _ = await self.vectordb.session.insert_many(
                collection_name=self.get_collection_name(project),
                texts=embedding["texts"],
                metadata=embedding["metadata"],
                vectors=embedding["vectors"],
                chunk_ids=embedding["chunk_ids"],
                asset_ids=asset_ids,
            )
            await asset_service.update_status(AssetStatus.INDEXED)

    async def index_and_push_into_vectordb(self, project: Project, assets: list[Asset]) -> list[UUID]:
        # step1: get text embedding vector
        embeddings = await self.index_assets(assets=assets)
        # step2: push into vectordb
        _ = await self.push_into_vectordb(project, embeddings)

        return True

    async def search(self, project: Project, text: str, limit: int):
        if not self.embedder:
            raise ValueError("Embedder not set")
        if not self.vectordb:
            raise ValueError("VectorDB not set")
        # embed the query text commming from the user query
        vector = self.embedder.provider.embed_text(text=text, document_type=EmbeddingDocumentType.QUERY.value)

        if not vector:
            return False

        if len(vector) == 1:
            vector = vector[0]

        # get the semantically similar texts from the vector db
        results = await self.vectordb.session.search_by_vector(
            collection_name=self.get_collection_name(project),
            vector=vector,
            limit=limit,
        )
        # return results comming from the vector db
        return results

    async def answer(self, project: Project, query: str, limit: int = 10):
        if not self.generator:
            raise ValueError("Generator not set")

        answer, full_prompt, chat_history = "", "", []
        # step 1: retrieve related documents
        retrieved_documents = await self.search(query, limit)
        if not retrieved_documents:
            logger.info("No retrieved documents found")
            return answer, full_prompt, chat_history

        # step 2: construct header prompt
        header_prompt = header_template.substitute(query=query)
        # step 3: Get the document prompts
        document_prompts = "\n".join(
            [
                document_template.substitute(doc_num=idx, chunk_text=self.generator.provider.process_text(doc.text))
                for idx, doc in enumerate(retrieved_documents, start=1)
            ]
        )
        # step 4: construct the full prompt
        full_prompt = "\n\n".join([header_prompt, document_prompts])
        # step 5: Construct Generation Client Prompts
        chat_history = [
            self.generator.provider.construct_prompt(
                prompt=self.get_system_prompt(project),
                role=self.generator.provider.ROLES[GenerationRolesEnums.SYSTEM.value],
            )
        ]

        # step 6: generate text
        answer = self.generator.provider.generate_text(
            prompt=full_prompt,
            chat_history=chat_history,
            max_output_tokens=self.generator.provider.default_generation_max_output_tokens,
            temperature=self.generator.provider.default_generation_temperature,
        )
        return answer, full_prompt, chat_history
