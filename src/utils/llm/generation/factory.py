from src.config.settings import LLMBackend
from src.utils.llm.generation import CoHereGenerationProvider, OpenAIGenerationProvider


class GenerationLLMProviderFactory:
    generation_PROVIDER_MAP = {
        LLMBackend.COHERE.value: CoHereGenerationProvider,
        LLMBackend.OPENAI.value: OpenAIGenerationProvider,
    }

    def __init__(self, backend: str):
        self.backend = backend

    def create(self, config: dict):
        try:
            return self.generation_PROVIDER_MAP[self.backend](**config)
        except KeyError:
            raise ValueError(f"Invalid LLM backend: {self.backend}")
