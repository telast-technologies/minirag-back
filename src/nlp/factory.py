from src.config.db.session import init_vectordb
from src.config.settings import settings
from src.nlp.services.controllers import EmbeddingController, GenerationController, VectorDBController
from src.nlp.services.controllers.NLPController import NLPController
from src.utils.llm.embedding.factory import EmbeddingLLMProviderFactory
from src.utils.llm.generation.factory import GenerationLLMProviderFactory


class NLPFactory:
    nlp_controller = None

    @classmethod
    def set_controller(cls, controller) -> NLPController:
        cls.nlp_controller = controller
        return cls.nlp_controller

    @classmethod
    async def get_controller(cls) -> NLPController:
        if cls.nlp_controller is not None:
            return cls.nlp_controller

        # initialize vectordb provider to app
        vectordb_session = await init_vectordb()
        vectordb = VectorDBController(vectordb_session)
        # initialize embedding provider to app
        embedding_model_id = settings.DEFAULT_EMBEDDING_MODEL_ID
        embedding_backend = settings.EMBEDDING_BACKEND(embedding_model_id)
        embedding_api_key = settings.EMBEDDING_API_KEY(embedding_backend)
        embedding_client = EmbeddingLLMProviderFactory(embedding_backend).create(
            {
                "api_key": embedding_api_key,
                "embedding_model_id": embedding_model_id,
                "embedding_size": settings.EMBEDDING_SIZE,
                "default_input_max_characters": settings.DAFAULT_INPUT_MAX_CHARACTERS,
            }
        )
        embedder = EmbeddingController(embedding_client)
        # initialize generation provider to app
        generation_model_id = settings.DEFAULT_GENERATION_MODEL_ID
        generation_backend = settings.GENERATION_BACKEND(generation_model_id)
        generation_api_key = settings.GENERATION_API_KEY(generation_backend)
        generation_client = GenerationLLMProviderFactory(generation_backend).create(
            {
                "api_key": generation_api_key,
                "generation_model_id": generation_model_id,
                "default_generation_max_output_tokens": settings.DAFAULT_GENERATION_MAX_TOKENS,
                "default_generation_temperature": settings.DEFAULT_GENERATION_TEMPERATURE,
                "default_input_max_characters": settings.DAFAULT_INPUT_MAX_CHARACTERS,
            }
        )
        generator = GenerationController(generation_client)
        # initialize nlp controller
        nlp_controller = NLPController(
            vectordb=vectordb,
            embedder=embedder,
            generator=generator,
        )
        return nlp_controller
