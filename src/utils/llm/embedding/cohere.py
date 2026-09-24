import cohere
from typing import List, Union

from src.utils.llm.embedding.interfaces import EmbeddingLLMInterface
from src.config.loggers import Logger

logger = Logger(__name__)

class CoHereProvider(EmbeddingLLMInterface):

    def __init__(
        self, 
        api_key: str,
        embedding_model_id: str,
        embedding_size: int,
        default_input_max_characters: int=1000,
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
        return text[:self.default_input_max_characters].strip()

    
    def embed_text(self, text: Union[str, List[str]], document_type: str = None):
        if not self.client:
            logger.error("CoHere client was not set")
            return None
        
        if isinstance(text, str):
            text = [text]
        
        if not self.embedding_model_id:
            logger.error("Embedding model for CoHere was not set")
            return None
        
        response = self.client.embed(
            model = self.embedding_model_id,
            texts = [ self.process_text(t) for t in text ],
            input_type = document_type.lower(),
            embedding_types=['float'],
        )

        if not response or not response.embeddings or not response.embeddings.float:
            logger.error("Error while embedding text with CoHere")
            return None
        
        return response.embeddings.float
