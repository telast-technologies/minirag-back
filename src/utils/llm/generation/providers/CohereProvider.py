import cohere

from src.config.loggers import Logger
from src.config.settings import settings
from src.utils.llm.generation.interfaces import GenerationLLMInterface
from src.utils.llm.generation.enums import GenerationRolesEnums


logger = Logger(__name__)


class CoHereGenerationProvider(GenerationLLMInterface):
    ROLES = {
        GenerationRolesEnums.SYSTEM.value: "system",
        GenerationRolesEnums.USER.value: "user",
        GenerationRolesEnums.ASSISTANT.value: "assistant"
    }

    def __init__(
        self,
        api_key: str,
        generation_model_id: str,
        default_input_max_characters: int=settings.DAFAULT_INPUT_MAX_CHARACTERS,
        default_generation_max_output_tokens: int=settings.DAFAULT_GENERATION_MAX_TOKENS,
        default_generation_temperature: float=settings.DEFAULT_GENERATION_TEMPERATURE
    ):
        
        self.api_key = api_key
        self.generation_model_id = generation_model_id

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature


        self.client = cohere.ClientV2(api_key=self.api_key)


    def set_model(self, model_id: str):
        self.generation_model_id = model_id


    def process_text(self, text: str):
        return text[:self.default_input_max_characters].strip()

    def generate_text(
        self, 
        prompt: str, 
        chat_history: list=[], 
        max_output_tokens: int=settings.DAFAULT_GENERATION_MAX_TOKENS,
        temperature: float = settings.DEFAULT_GENERATION_TEMPERATURE
        ):

        if not self.client:
            logger.error("CoHere client was not set")
            return None

        if not self.generation_model_id:
            logger.error("Generation model for CoHere was not set")
            return None

        messages = [
            {
                "role": message["role"],
                "content": message["text"],
            }
            for message in chat_history
        ]
        messages.append({
            "role": GenerationRolesEnums.USER.value,
            "content": prompt
        })
        response = self.client.chat(
            model = self.generation_model_id,
            messages = messages,
            temperature = temperature
        )

        if not response or not getattr(response, "message", None) or not response.message.content:
            logger.error("Error while generating text with CoHere: Empty or invalid response")
            return None
        
        # Iterate through the content blocks to find the actual text response
        # This safely skips 'thinking' blocks or tool call blocks
        texts = [
            block.text
            for block in response.message.content
            if block.type == "text"
        ]

        return "\n".join(texts)

    def construct_prompt(self, prompt: str, role: str):
        return {
            "role": role,
            "text": prompt,
        }