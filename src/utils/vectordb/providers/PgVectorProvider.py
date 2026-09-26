import json

from sqlalchemy.sql import text as sql_text

from src.config.loggers import Logger
from src.config.settings import settings
from src.utils.vectordb.enums import DistanceMethod
from src.utils.vectordb.schemas import RetrievedDocument
from src.utils.vectordb.VectorDBInterface import VectorDBInterface

logger = Logger(__name__)


class PGVectorProvider(VectorDBInterface):
    TABEL_SCHEMA = {
        "id": "id",
        "text": "text",
        "vector": "vector",
        "metadata": "metadata",
        "chunk_id": "chunk_id",
        "asset_id": "asset_id",
    }

    DISTANCE_METHOD = {
        DistanceMethod.COSINE.value: "vector_cosine_ops",
        DistanceMethod.DOT.value: "vector_l2_ops",
    }

    INDEX_TYPE = {"hnsw": "hnsw", "ivfflat": "ivfflat"}

    def __init__(
        self,
        db_client,
        distance_method: str = settings.VECTOR_DB_DISTANCE_METHOD,
        default_vector_size: int = settings.VECTOR_DB_DEFAULT_SIZE,
        index_threshold: int = settings.VECTOR_DB_INDEX_THRESHOLD,
    ):
        self.db_client = db_client
        self.default_vector_size = default_vector_size
        self.index_threshold = index_threshold
        self.distance_method = self.DISTANCE_METHOD[distance_method]
        self.table_prefix = "pgvector"
        self.default_index_name = lambda collection_name: f"{collection_name}_vector_idx"

    async def connect(self):
        async with self.db_client() as session:
            try:
                result = await session.exec(sql_text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
                extension_exists = result.scalar_one_or_none()

                if not extension_exists:
                    await session.exec(sql_text("CREATE EXTENSION vector"))
                    await session.commit()
            except Exception as e:
                logger.warning(f"Vector extension setup: {str(e)}")
                await session.rollback()

    async def disconnect(self):
        pass

    async def is_collection_existed(self, collection_name: str) -> bool:
        record = None
        async with self.db_client() as session:
            list_tbl = sql_text("SELECT * FROM pg_tables WHERE tablename = :collection_name")
            results = await session.exec(list_tbl, params={"collection_name": collection_name})
            record = results.scalar_one_or_none()

        return record

    async def list_all_collections(self) -> list:
        records = []
        async with self.db_client() as session:
            list_tbl = sql_text("SELECT tablename FROM pg_tables WHERE tablename LIKE :prefix")
            results = await session.exec(list_tbl, params={"prefix": f"{self.table_prefix}%"})
            records = results.scalars().all()

        return records

    async def get_collection_info(self, collection_name: str) -> dict:
        async with self.db_client() as session:
            table_info_sql = sql_text(
                """
                    SELECT schemaname, tablename, tableowner, tablespace, hasindexes
                    FROM pg_tables
                    WHERE tablename = :collection_name
                """
            )
            count_sql = sql_text(f'SELECT COUNT(*) FROM "{collection_name}"')

            table_info = await session.exec(table_info_sql, params={"collection_name": collection_name})
            record_count = await session.exec(count_sql)

            table_data = table_info.fetchone()
            if not table_data:
                return None

            return {
                "table_info": {
                    "schemaname": table_data[0],
                    "tablename": table_data[1],
                    "tableowner": table_data[2],
                    "tablespace": table_data[3],
                    "hasindexes": table_data[4],
                },
                "record_count": record_count.scalar_one(),
            }

    async def delete_collection(self, collection_name: str):
        async with self.db_client() as session:
            logger.info(f"Deleting collection: {collection_name}")
            delete_sql = sql_text(f'DROP TABLE IF EXISTS "{collection_name}"')
            await session.exec(delete_sql)
            await session.commit()

        return True

    async def create_collection(self, collection_name: str, embedding_size: int):
        is_collection_existed = await self.is_collection_existed(collection_name=collection_name)
        if not is_collection_existed:
            logger.info(f"Creating collection: {collection_name}")
            async with self.db_client() as session:
                create_sql = sql_text(
                    f'CREATE TABLE "{collection_name}" ('
                    f'{self.TABEL_SCHEMA["id"]} bigserial PRIMARY KEY,'
                    f'{self.TABEL_SCHEMA["text"]} text, '
                    f'{self.TABEL_SCHEMA["vector"]} vector({embedding_size}), '
                    f'{self.TABEL_SCHEMA["metadata"]} jsonb DEFAULT \'{{}}\', '
                    f'{self.TABEL_SCHEMA["chunk_id"]} uuid, '
                    f'{self.TABEL_SCHEMA["asset_id"]} uuid, '
                    f'FOREIGN KEY ({self.TABEL_SCHEMA["chunk_id"]}) REFERENCES assetchunk(id),'
                    f'FOREIGN KEY ({self.TABEL_SCHEMA["asset_id"]}) REFERENCES asset(id)'
                    ")"
                )
                await session.exec(create_sql)
                await session.commit()

            return True

        return False

    async def is_index_existed(self, collection_name: str) -> bool:
        index_name = self.default_index_name(collection_name)
        async with self.db_client() as session:
            check_sql = sql_text(
                """
                    SELECT 1
                    FROM pg_indexes
                    WHERE tablename = :collection_name
                    AND indexname = :index_name
                """
            )
            results = await session.exec(
                check_sql, params={"index_name": index_name, "collection_name": collection_name}
            )
            return bool(results.scalar_one_or_none())

    async def create_vector_index(self, collection_name: str, index_type: str = "hnsw"):
        is_index_existed = await self.is_index_existed(collection_name=collection_name)
        if is_index_existed:
            return False

        async with self.db_client() as session:
            count_sql = sql_text(f'SELECT COUNT(*) FROM "{collection_name}"')
            result = await session.exec(count_sql)
            records_count = result.scalar_one()

            if records_count < self.index_threshold:
                return False

            logger.info(f"START: Creating vector index for collection: {collection_name}")

            index_name = self.default_index_name(collection_name)
            create_idx_sql = sql_text(
                f'CREATE INDEX "{index_name}" ON "{collection_name}" '
                f'USING {index_type} ({self.TABEL_SCHEMA["vector"]} {self.distance_method})'
            )

            await session.exec(create_idx_sql)
            await session.commit()
            logger.info(f"END: Created vector index for collection: {collection_name}")

    async def reset_vector_index(self, collection_name: str, index_type: str = "hnsw") -> bool:
        index_name = self.default_index_name(collection_name)
        async with self.db_client() as session:
            drop_sql = sql_text(f'DROP INDEX IF EXISTS "{index_name}"')
            await session.exec(drop_sql)
            await session.commit()

        return await self.create_vector_index(collection_name=collection_name, index_type=index_type)

    async def insert_one(
        self,
        collection_name: str,
        text: str,
        vector: list,
        metadata: dict = None,
        chunk_id: str = None,
        asset_id: str = None,
    ):
        is_collection_existed = await self.is_collection_existed(collection_name=collection_name)
        if not is_collection_existed:
            logger.error(f"Can not insert new record to non-existed collection: {collection_name}")
            return False

        if not chunk_id:
            logger.error(f"Can not insert new record without chunk_id: {collection_name}")
            return False

        async with self.db_client() as session:
            # selected columns in the table
            text_tb = self.TABEL_SCHEMA["text"]
            vector_tb = self.TABEL_SCHEMA["vector"]
            metadata_tb = self.TABEL_SCHEMA["metadata"]
            chunk_id_tb = self.TABEL_SCHEMA["chunk_id"]
            asset_id_tb = self.TABEL_SCHEMA["asset_id"]

            insert_sql = sql_text(
                f'INSERT INTO "{collection_name}" '
                f"({text_tb}, {vector_tb}, {metadata_tb}, {chunk_id_tb}, {asset_id_tb}) "
                "VALUES (:text, :vector, :metadata, CAST(:chunk_id AS uuid), CAST(:asset_id AS uuid))"
            )
            metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata is not None else "{}"
            await session.exec(
                insert_sql,
                params={
                    "text": text,
                    "vector": "[" + ",".join([str(v) for v in vector]) + "]",
                    "metadata": metadata_json,
                    "chunk_id": chunk_id,
                    "asset_id": asset_id,
                },
            )
            await session.commit()

        await self.create_vector_index(collection_name=collection_name)
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
        is_collection_existed = await self.is_collection_existed(collection_name=collection_name)
        if not is_collection_existed:
            logger.error(f"Can not insert new records to non-existed collection: {collection_name}")
            return False

        if len(asset_ids) != len(chunk_ids):
            logger.error("Invalid data items for collection: {collection_name}")
            return False

        if len(vectors) != len(chunk_ids):
            logger.error(f"Invalid data items for collection: {collection_name}")
            return False

        if not metadata:
            metadata = [None] * len(texts)

        async with self.db_client() as session:
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i : i + batch_size]
                batch_vectors = vectors[i : i + batch_size]
                batch_metadata = metadata[i : i + batch_size]
                batch_chunk_ids = chunk_ids[i : i + batch_size]
                batch_asset_ids = asset_ids[i : i + batch_size]

                values = []
                for _text, _vector, _metadata, _chunk_id, _asset_id in zip(
                    batch_texts, batch_vectors, batch_metadata, batch_chunk_ids, batch_asset_ids
                ):
                    metadata_json = json.dumps(_metadata, ensure_ascii=False) if _metadata is not None else "{}"
                    values.append(
                        {
                            "text": _text,
                            "vector": "[" + ",".join([str(v) for v in _vector]) + "]",
                            "metadata": metadata_json,
                            "chunk_id": _chunk_id,
                            "asset_id": _asset_id,
                        }
                    )

                batch_insert_sql = sql_text(
                    f'INSERT INTO "{collection_name}" '
                    f'({self.TABEL_SCHEMA["text"]}, '
                    f'{self.TABEL_SCHEMA["vector"]}, '
                    f'{self.TABEL_SCHEMA["metadata"]}, '
                    f'{self.TABEL_SCHEMA["chunk_id"]}, '
                    f'{self.TABEL_SCHEMA["asset_id"]}) '
                    f"VALUES (:text, :vector, :metadata, CAST(:chunk_id AS uuid), CAST(:asset_id AS uuid))"
                )
                await session.exec(batch_insert_sql, params=values)

            await session.commit()

        await self.create_vector_index(collection_name=collection_name)
        return True

    async def search_by_vector(self, collection_name: str, vector: list, limit: int):
        is_collection_existed = await self.is_collection_existed(collection_name=collection_name)
        if not is_collection_existed:
            logger.error(f"Can not search for records in a non-existed collection: {collection_name}")
            return False

        vector_str = "[" + ",".join([str(v) for v in vector]) + "]"
        async with self.db_client() as session:
            search_sql = sql_text(
                f'SELECT {self.TABEL_SCHEMA["text"]} as text, 1 - ({self.TABEL_SCHEMA["vector"]} <=> :vector) as score'
                f' FROM "{collection_name}"'
                " ORDER BY score DESC "
                f"LIMIT {limit}"
            )

            result = await session.exec(search_sql, params={"vector": vector_str})
            records = result.fetchall()

            return [RetrievedDocument(text=record.text, score=record.score) for record in records]
