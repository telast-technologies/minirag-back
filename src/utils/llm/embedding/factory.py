from src.config.settings import LLMBackend
from src.utils.llm.embedding import CohereEmbeddingProvider, OpenAIEmbeddingProvider

class EmbeddingLLMProviderFactory:
    EMBEDDING_PROVIDER_MAP = {
        LLMBackend.COHERE.value: CohereEmbeddingProvider,
        LLMBackend.OPENAI.value: OpenAIEmbeddingProvider,
    }

    def __init__(self, backend: str):
        self.backend = backend

    def create(self, config: dict):
        try:
            return self.EMBEDDING_PROVIDER_MAP[self.backend](**config)
        except KeyError:
            raise ValueError(f"Invalid LLM backend: {self.backend}")
            
        
