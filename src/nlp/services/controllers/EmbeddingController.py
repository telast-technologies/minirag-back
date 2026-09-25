
from uuid import UUID
from typing import Any

from src.config.loggers import Logger
from src.knowledge_base.models import Asset
from src.utils.llm.embedding.interfaces import EmbeddingLLMInterface
from src.utils.llm.embedding.enums import EmbeddingDocumentType

logger = Logger(__name__)

class EmbeddingController:

    def __init__(self, provider:EmbeddingLLMInterface): 
        self.provider = provider

    async def embed(self, assets: list[Asset]) -> dict[UUID, dict[str, list[list[float]] | list[dict[str, Any]]]]:
      
        try:
            embeddings = {}
            for asset in assets:
                texts = [chunk.text for chunk in asset.chunks]
                chunk_metadata = [chunk.chunk_metadata for chunk in asset.chunks]
                chunk_ids = [chunk.id for chunk in asset.chunks]
                vectors = self.provider.embed_text(texts, document_type=EmbeddingDocumentType.DOCUMENT.value)
                embeddings[asset.id] = {
                    "vectors": vectors, 
                    "metadata": chunk_metadata, 
                    "chunk_ids": chunk_ids, 
                    "texts": texts
                }
            return embeddings
        except KeyError:
            logger.error(f"Embedding provider {self.provider.name} not found")
            return {}
        except Exception as e:
            logger.error(f"Error while embedding text with {self.provider.name} : {str(e)}")
            return {}
