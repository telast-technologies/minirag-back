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
from src.utils.llm.generation.enums import MsgRoles

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

    async def _prepare_rag_payload(self, project: Project, query: str, history: list = None, limit: int = 10):
        """
        دالة مساعدة مركزية لتجهيز سجل المحادثات (History)، تعليمات النظام (System Prompt)، وبناء سياق الـ RAG.
        """
        # 1. بناء الـ System Prompt كأول رسالة
        system_prompt_msg = [
            self.generator.provider.construct_prompt(
                prompt=self.get_system_prompt(project),
                role=self.generator.provider.ROLES[MsgRoles.SYSTEM.value],
            )
        ]

        # 2. إضافة تاريخ المحادثة السابقة لتفادي فقدان سياق الجلسة
        chat_history = system_prompt_msg + [
            self.generator.provider.construct_prompt(
                prompt=msg["text"], role=self.generator.provider.ROLES[msg["role"]]
            )
            for msg in history
        ]

        # 3. جلب المستندات ذات الصلة (مع تصحيح تمرير الـ project)
        retrieved_documents = await self.search(project=project, text=query, limit=limit)

        if not retrieved_documents:
            logger.info("No retrieved documents found")
            return query, chat_history

        # 4. تجهيز المستندات وتغليفها بـ XML Tags (<context>) لتحسين دقة استخراج النماذج
        document_prompts = "\n".join(
            [
                document_template.substitute(doc_num=idx, chunk_text=self.generator.provider.process_text(doc.text))
                for idx, doc in enumerate(retrieved_documents, start=1)
            ]
        )
        # 5. دمج الـ Context مع الـ Header Prompt الخاص بالسؤال
        header_prompt = header_template.substitute(query=query)
        # 6. construct the full prompt
        full_prompt = "\n\n".join([header_prompt, document_prompts])

        return full_prompt, chat_history

    async def answer(self, project: Project, query: str, history: list = None, limit: int = 10):
        """الإجابة العادية (Non-streaming)"""
        if not self.generator:
            raise ValueError("Generator not set")

        full_prompt, chat_history = await self._prepare_rag_payload(project, query, history, limit)

        answer = self.generator.provider.generate_text(
            prompt=full_prompt,
            chat_history=chat_history,
            max_output_tokens=self.generator.provider.default_generation_max_output_tokens,
            temperature=self.generator.provider.default_generation_temperature,
        )
        return answer, full_prompt, chat_history

    async def answer_stream(self, project: Project, query: str, history: list = None, limit: int = 10):
        """الإجابة التدفقية (Streaming) المتوافقة مع دالة ask"""
        if not self.generator:
            raise ValueError("Generator not set")

        full_prompt, chat_history = await self._prepare_rag_payload(project, query, history, limit)

        print(full_prompt)
        print("=================================")
        print(chat_history)
        print("=================================")
        async for chunk in self.generator.provider.generate_stream(
            prompt=full_prompt,
            chat_history=chat_history,
            max_output_tokens=self.generator.provider.default_generation_max_output_tokens,
            temperature=self.generator.provider.default_generation_temperature,
        ):
            yield chunk
