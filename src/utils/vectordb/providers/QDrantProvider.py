from qdrant_client import QdrantClient, models

from src.config.loggers import Logger
from src.config.settings import settings
from src.utils.vectordb.enums import DistanceMethod
from src.utils.vectordb.schemas import RetrievedDocument
from src.utils.vectordb.VectorDBInterface import VectorDBInterface

logger = Logger(__name__)


class QDrantProvider(VectorDBInterface):
    DISTANCE_METHOD = {
        DistanceMethod.COSINE.value: models.Distance.COSINE,
        DistanceMethod.DOT.value: models.Distance.DOT,
    }

    def __init__(
        self,
        db_client: str,
        distance_method: str = settings.VECTOR_DB_DISTANCE_METHOD,
        default_vector_size: int = settings.VECTOR_DB_DEFAULT_SIZE,
        index_threshold: int = settings.VECTOR_DB_INDEX_THRESHOLD,
    ):
        self.client = None
        self.db_client = db_client
        self.default_vector_size = default_vector_size
        self.distance_method = self.DISTANCE_METHOD[distance_method]
        self.index_threshold = index_threshold

        # additional attributes
        self.table_prefix = "qdrant"

    async def connect(self):
        self.client = QdrantClient(path=self.db_client)

    async def disconnect(self):
        self.client = None

    async def is_collection_existed(self, collection_name: str) -> bool:
        return self.client.collection_exists(collection_name=collection_name)

    async def list_all_collections(self) -> list:
        return self.client.get_collections()

    # تم إضافة async هنا لتتوافق مع باقي الدوال
    async def get_collection_info(self, collection_name: str) -> dict:
        return self.client.get_collection(collection_name=collection_name)

    async def delete_collection(self, collection_name: str):
        # تم إضافة await هنا
        if await self.is_collection_existed(collection_name):
            logger.info(f"Deleting collection: {collection_name}")
            return self.client.delete_collection(collection_name=collection_name)

    async def create_collection(self, collection_name: str, embedding_size: int):
        # تم إضافة await هنا
        if not await self.is_collection_existed(collection_name):
            logger.info(f"Creating new Qdrant collection: {collection_name}")

            _ = self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=embedding_size, distance=self.distance_method),
            )

            return True

        return False

    async def insert_one(
        self,
        collection_name: str,
        text: str,
        vector: list,
        metadata: dict = None,
        chunk_id: str = None,
        asset_id: str = None,
    ):
        # تم إضافة await هنا
        if not await self.is_collection_existed(collection_name):
            logger.error(f"Can not insert new record to non-existed collection: {collection_name}")
            return False

        try:
            _ = self.client.upload_records(
                collection_name=collection_name,
                records=[
                    models.Record(
                        id=str(chunk_id),
                        vector=vector,
                        payload={"text": text, "metadata": metadata, "asset_id": str(asset_id)},
                    )
                ],
            )
        except Exception as e:
            logger.error(f"Error while inserting batch: {e}")
            return False

        return True

    async def insert_many(
        self,
        collection_name: str,
        texts: list,
        vectors: list,
        metadata: list = None,
        chunk_ids: list = None,
        asset_ids: list = None,
        batch_size: int = 50,
    ):
        # تم إضافة فحص الـ Collection هنا لمزيد من الأمان والاتساق مع insert_one
        if not await self.is_collection_existed(collection_name):
            logger.error(f"Can not insert new records to non-existed collection: {collection_name}")
            return False

        if asset_ids is None:
            asset_ids = [None] * len(texts)

        if metadata is None:
            metadata = [None] * len(texts)

        if chunk_ids is None:
            chunk_ids = list(range(0, len(texts)))

        for i in range(0, len(texts), batch_size):
            batch_end = i + batch_size

            batch_texts = texts[i:batch_end]
            batch_vectors = vectors[i:batch_end]
            batch_metadata = metadata[i:batch_end]
            batch_chunk_ids = chunk_ids[i:batch_end]
            batch_asset_ids = asset_ids[i:batch_end]

            batch_records = [
                models.Record(
                    id=str(batch_chunk_ids[x]),
                    vector=batch_vectors[x],
                    payload={
                        "text": batch_texts[x],
                        "metadata": batch_metadata[x],
                        "asset_id": str(batch_asset_ids[x]),
                    },
                )
                for x in range(len(batch_texts))
            ]

            try:
                _ = self.client.upload_records(
                    collection_name=collection_name,
                    records=batch_records,
                )
            except Exception as e:
                logger.error(f"Error while inserting batch: {e}")
                return False

        return True

    async def search_by_vector(self, collection_name: str, vector: list, limit: int = 5):
        results = self.client.search(collection_name=collection_name, query_vector=vector, limit=limit)

        if not results or len(results) == 0:
            return None

        return [RetrievedDocument(score=result.score, text=result.payload["text"]) for result in results]
