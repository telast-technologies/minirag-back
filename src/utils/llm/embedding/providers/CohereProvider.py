import cohere

from src.config.loggers import Logger
from src.config.settings import LLMBackend
from src.utils.llm.embedding.enums import EmbeddingDocumentType
from src.utils.llm.embedding.interfaces import EmbeddingLLMInterface

logger = Logger(__name__)


class CohereEmbeddingProvider(EmbeddingLLMInterface):
    name: str = LLMBackend.COHERE.value

    INPUT_TYPE = {
        EmbeddingDocumentType.DOCUMENT.value: "search_document",
        EmbeddingDocumentType.QUERY.value: "search_query",
    }

    def __init__(
        self,
        api_key: str,
        embedding_model_id: str,
        embedding_size: int,
        default_input_max_characters: int = 1000,
    ):
        self.api_key = api_key
        self.embedding_model_id = embedding_model_id
        self.embedding_size = embedding_size
        self.default_input_max_characters = default_input_max_characters

        self.client = cohere.Client(api_key=self.api_key)

    def set_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def process_text(self, text: str):
        return text[: self.default_input_max_characters].strip()

    def embed_text(self, text: str | list[str], document_type: str = None):
        if not self.client:
            logger.error("CoHere client was not set")
            return None

        if isinstance(text, str):
            text = [text]

        if not self.embedding_model_id:
            logger.error("Embedding model for CoHere was not set")
            return None

        response = self.client.embed(
            model=self.embedding_model_id,
            texts=[self.process_text(t) for t in text],
            input_type=self.INPUT_TYPE[document_type],
            embedding_types=["float"],
        )

        if not response or not response.embeddings or not response.embeddings.float:
            logger.error("Error while embedding text with CoHere")
            return None

        return response.embeddings.float
