from openai import OpenAI

from src.config.loggers import Logger
from src.config.settings import settings
from src.utils.llm.generation.interfaces import GenerationLLMInterface
from src.utils.llm.generation.enums import GenerationRolesEnums


logger = Logger(__name__)

class OpenAIGenerationProvider(GenerationLLMInterface):
    ROLES = {
        GenerationRolesEnums.SYSTEM.value: "system",
        GenerationRolesEnums.USER.value: "user",
        GenerationRolesEnums.ASSISTANT.value: "assistant"
    }

    def __init__(
        self, 
        api_key: str,
        generation_model_id: str,
        api_url: str = "",
        default_input_max_characters: int = settings.DAFAULT_INPUT_MAX_CHARACTERS,
        default_generation_max_output_tokens: int = settings.DAFAULT_GENERATION_MAX_TOKENS,
        default_generation_temperature: float = settings.DEFAULT_GENERATION_TEMPERATURE
    ):
        
        self.api_key = api_key
        self.generation_model_id = generation_model_id
        self.api_url = api_url if api_url else None

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature

        self.client = OpenAI(
            api_key = self.api_key,
            base_url = self.api_url
        )


    def set_model(self, model_id: str):
        self.generation_model_id = model_id

    def process_text(self, text: str):
        return text[:self.default_input_max_characters].strip()

    def generate_text(
        self, 
        prompt: str, 
        chat_history: list = [], 
        max_output_tokens: int = settings.DAFAULT_GENERATION_MAX_TOKENS,
        temperature: float = settings.DEFAULT_GENERATION_TEMPERATURE
    ):
        
        if not self.client:
            logger.error("OpenAI client was not set")
            return None

        if not self.generation_model_id:
            logger.error("Generation model for OpenAI was not set")
            return None
        

        chat_history.append(
            self.construct_prompt(prompt=prompt, role=self.ROLES[GenerationRolesEnums.USER.value])
        )

        response = self.client.chat.completions.create(
            model = self.generation_model_id,
            messages = chat_history,
            max_tokens = max_output_tokens,
            temperature = temperature
        )

        if not response or not response.choices or len(response.choices) == 0 or not response.choices[0].message:
            logger.error("Error while generating text with OpenAI")
            return None

        return response.choices[0].message.content


    def construct_prompt(self, prompt: str, role: str):
        return {
            "role": role,
            "content": prompt,
        }
    


    

