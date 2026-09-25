from src.config.settings import VectorDBBackend
from src.utils.vectordb import PGVectorProvider, QDrantProvider


class VectorDBProviderFactory:
    VECTORDB_PROVIDER_MAP = {
        VectorDBBackend.PGVECTOR.value: PGVectorProvider,
        VectorDBBackend.QDRANT.value: QDrantProvider,
    }

    def __init__(self, backend: str):
        self.backend = backend

    def create(self, config: dict):
        try:
            return self.VECTORDB_PROVIDER_MAP[self.backend](**config)
        except KeyError:
            raise ValueError(f"Invalid VectorDB backend: {self.backend}")
            
        
