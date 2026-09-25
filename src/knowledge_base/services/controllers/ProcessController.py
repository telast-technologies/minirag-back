import mimetypes
import os
import tempfile

from langchain_community.document_loaders import PyMuPDFLoader, TextLoader, WebBaseLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config.loggers import Logger
from src.config.settings import settings
from src.config.storage import S3Storage
from src.knowledge_base.crud import AssetChunkCRUD
from src.knowledge_base.enums import AssetStatus, AssetType
from src.knowledge_base.models import Asset, AssetChunk
from src.knowledge_base.services.assets import AssetService
from src.utils.controllers.PaginatorController import Paginator

logger = Logger(__name__)


class ChunckAssetController:
    LOADER_MAP = {
        AssetType.URL.value: WebBaseLoader,
        "application/pdf": PyMuPDFLoader,
        "text/plain": lambda path: TextLoader(path, encoding="utf-8"),
        "application/json": lambda path: TextLoader(path, encoding="utf-8"),
        "text/markdown": lambda path: TextLoader(path, encoding="utf-8"),
        "text/csv": lambda path: TextLoader(path, encoding="utf-8"),
    }

    def __init__(self, asset: Asset):
        self.asset = asset

    def load(self) -> list[Document]:
        try:
            # Handle raw TEXT directly (Bypass loaders completely)
            if self.asset.type == AssetType.TEXT.value:
                # Directly instantiate the Document
                doc = Document(
                    page_content=self.asset.content,
                    metadata={
                        "asset_id": str(self.asset.id),
                        "project_id": str(self.asset.project_id),
                        "asset_name": self.asset.name,
                        **(self.asset.asset_metadata or {}),
                        "source": "raw_text_input",
                    },
                )
                logger.info(f"Loaded 1 document directly from text asset {self.asset.name}")
                return [doc]

            if self.asset.type == AssetType.FILE.value:
                file_key = self.asset.content
                ext = os.path.splitext(file_key)[1] or ".tmp"
                with tempfile.TemporaryDirectory() as tmp_dir:
                    tmp_path = os.path.join(tmp_dir, f"temp_asset{ext}")

                    file_stream = S3Storage.open(file_key)
                    file_stream.seek(0)
                    with open(tmp_path, "wb") as f:
                        f.write(file_stream.read())

                    mime_type = mimetypes.guess_type(tmp_path)[0]
                    loader = self.LOADER_MAP.get(mime_type, self.LOADER_MAP["text/plain"])(tmp_path)
                    logger.info(f"Initialized loader for file: {self.asset.content}")
                    docs = loader.load()
            elif self.asset.type == AssetType.URL.value:
                loader = self.LOADER_MAP[self.asset.type]([self.asset.content])
                logger.info(f"Initialized loader for url: {self.asset.content}")
                docs = loader.load()

            for doc in docs:
                doc.metadata.update(
                    {
                        "asset_id": str(self.asset.id),
                        "project_id": str(self.asset.project_id),
                        "asset_name": self.asset.name,
                        **(self.asset.asset_metadata or {}),
                        "source": self.asset.content,
                    }
                )

            logger.info(f"Loaded {len(docs)} documents from asset {self.asset.name}")
            return docs
        except KeyError as e:
            logger.error(f"Error while loading asset: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error while loading asset: {str(e)}")
            raise

    async def create_chunks(
        self, chunk_size: int = settings.DEFAULT_CHUNK_SIZE, chunk_overlap: int = settings.DEFAULT_CHUNK_OVERLAP
    ) -> list[AssetChunk]:
        documents = self.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", " "],
        )
        chunks = text_splitter.split_documents(documents)

        chunk_curd = AssetChunkCRUD()
        paginator = Paginator(chunks, 10)
        chunk_objs = [
            await chunk_curd.create(
                {
                    "project_id": self.asset.project_id,
                    "asset_id": self.asset.id,
                    "text": chunk.page_content,
                    "chunk_metadata": chunk.metadata,
                    "order": global_idx,
                }
            )
            for global_idx, chunk in enumerate(
                # This generator flattens the paginated chunks and filters out falsy ones
                c
                for page in paginator.get_page()
                for c in page.items
                if c
            )
        ]
        await AssetService(self.asset).update_status(AssetStatus.PROCESSED)
        logger.info(f"Created {len(chunk_objs)} chunks for asset {self.asset.name}")
        return chunk_objs


class ProcessController:
    def __init__(self, assets):
        self.assets = assets

    async def process(
        self, chunk_size: int = settings.DEFAULT_CHUNK_SIZE, chunk_overlap: int = settings.DEFAULT_CHUNK_OVERLAP
    ) -> list[Asset]:
        processed_assets = []
        paginator = Paginator(self.assets, 10)

        for page in paginator.get_page():
            for asset in page.items:
                if asset:
                    chunck_controller = ChunckAssetController(asset)
                    chunks = await chunck_controller.create_chunks(chunk_size, chunk_overlap)
                    logger.info(f"Created {len(chunks)} chunks for asset {asset.name}")
                    processed_assets.append(asset)
        return processed_assets
