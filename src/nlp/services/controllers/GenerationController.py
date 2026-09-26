
from src.config.loggers import Logger
from src.utils.llm.generation.interfaces import GenerationLLMInterface

logger = Logger(__name__)

class GenerationController:
    def __init__(self, provider: GenerationLLMInterface):
        self.provider = provider
    