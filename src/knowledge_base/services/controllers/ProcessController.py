from langchain_community.document_loaders import UnstructuredURLLoader, WebBaseLoader
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
        AssetType.FILE.value: UnstructuredURLLoader,
        AssetType.URL.value: WebBaseLoader,
    }

    def __init__(self, asset: Asset):
        self.asset = asset

    def get_loader(self):
        try:
            if self.asset.type == AssetType.FILE.value:
                direct_url = S3Storage.get_path(self.asset.content)
                loader = self.LOADER_MAP[self.asset.type]([direct_url])
                logger.info(f"Initialized loader for file: {direct_url}")
                return loader
            elif self.asset.type == AssetType.URL.value:
                # WebBaseLoader expects a URL string or a list of URLs
                loader = self.LOADER_MAP[self.asset.type]([self.asset.content])
                logger.info(f"Initialized loader for url: {self.asset.content}")
                return loader
            else:
                raise ValueError(f"Asset type {self.asset.type} does not use a loader.")
        except KeyError:
            logger.error(f"Unsupported asset type for loader: {self.asset.type}")
            raise ValueError(f"Unsupported asset type for loader: {self.asset.type}")

    def load(self):
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

            # Handle FILES and URLS using loaders
            loader = self.get_loader()
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

        except Exception as e:
            logger.error(f"Error while loading asset: {str(e)}")
            raise Exception(f"Error while loading asset: {str(e)}")

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

        chunk_objs = []
        paginator = Paginator(chunks, 10)

        global_idx = 0
        for page in paginator.get_page():
            for chunk in page.items:
                chunk_curd = AssetChunkCRUD()
                chunk_obj = await chunk_curd.create(
                    {
                        "project_id": self.asset.project_id,
                        "asset_id": self.asset.id,
                        "text": chunk.page_content,
                        "chunk_metadata": chunk.metadata,
                        "order": global_idx,
                    }
                )
                global_idx += 1
                chunk_objs.append(chunk_obj)

        await AssetService(self.asset).update_status(AssetStatus.PROCESSED)
        logger.info(f"Created {len(chunk_objs)} chunks for asset {self.asset.name}")
        return chunk_objs


class ProcessController:
    def __init__(self, assets):
        self.assets = assets

    async def process(
        self, chunk_size: int = settings.DEFAULT_CHUNK_SIZE, chunk_overlap: int = settings.DEFAULT_CHUNK_OVERLAP
    ):
        processed_assets = []
        paginator = Paginator(self.assets, 10)

        for page in paginator.get_page():
            for asset in page.items:
                if asset:
                    chunck_controller = ChunckAssetController(asset)
                    chunks = await chunck_controller.create_chunks(chunk_size, chunk_overlap)
                    logger.info(f"Created {len(chunks)} chunks for asset {asset.name}")
                    processed_assets.append(asset)
                    # TODO: embed the chunks

        return processed_assets
