from openai import OpenAI

from src.config.loggers import Logger
from src.utils.llm.embedding.interfaces import EmbeddingLLMInterface

logger = Logger(__name__)


class OpenAIEmbeddingProvider(EmbeddingLLMInterface):
    def __init__(
        self,
        api_key: str,
        embedding_model_id: str,
        embedding_size: int,
        default_input_max_characters: int = 1000,
        api_url: str = None,
    ):
        self.api_key = api_key
        self.api_url = api_url

        self.embedding_model_id = embedding_model_id
        self.embedding_size = embedding_size
        self.default_input_max_characters = default_input_max_characters

        self.client = OpenAI(
            api_key=self.api_key, base_url=self.api_url if self.api_url and len(self.api_url) else None
        )

    def set_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def process_text(self, text: str):
        return text[: self.default_input_max_characters].strip()

    def embed_text(self, text: str | list[str], document_type: str = None):
        if not self.client:
            logger.error("OpenAI client was not set")
            return None

        if isinstance(text, str):
            text = [text]

        if not self.embedding_model_id:
            logger.error("Embedding model for OpenAI was not set")
            return None

        response = self.client.embeddings.create(
            model=self.embedding_model_id,
            input=self.process_text(text),
        )

        if not response or not response.data or len(response.data) == 0 or not response.data[0].embedding:
            logger.error("Error while embedding text with OpenAI")
            return None

        return [rec.embedding for rec in response.data]
