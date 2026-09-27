import cohere

from src.config.loggers import Logger
from src.config.settings import settings
from src.utils.llm.generation.enums import MsgRoles
from src.utils.llm.generation.interfaces import GenerationLLMInterface

logger = Logger(__name__)


class CoHereGenerationProvider(GenerationLLMInterface):
    ROLES = {
        MsgRoles.SYSTEM.value: "system",
        MsgRoles.USER.value: "user",
        MsgRoles.ASSISTANT.value: "assistant",
    }

    def __init__(
        self,
        api_key: str,
        generation_model_id: str,
        default_input_max_characters: int = settings.DAFAULT_INPUT_MAX_CHARACTERS,
        default_generation_max_output_tokens: int = settings.DAFAULT_GENERATION_MAX_TOKENS,
        default_generation_temperature: float = settings.DEFAULT_GENERATION_TEMPERATURE,
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
        return text[: self.default_input_max_characters].strip()

    def generate_text(
        self,
        prompt: str,
        chat_history: list = [],
        max_output_tokens: int = settings.DAFAULT_GENERATION_MAX_TOKENS,
        temperature: float = settings.DEFAULT_GENERATION_TEMPERATURE,
    ):
        if not self.client or not self.generation_model_id:
            logger.error("CoHere client or model ID was not set")
            return None

        messages = [
            {
                "role": message["role"],
                "content": message["text"],
            }
            for message in chat_history
        ]
        messages.append({"role": MsgRoles.USER.value, "content": self.process_text(prompt)})

        try:
            response = self.client.chat(
                model=self.generation_model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=max_output_tokens,
            )

            if not response or not getattr(response, "message", None) or not response.message.content:
                logger.error("Error while generating text with CoHere: Empty or invalid response")
                return None

            texts = [block.text for block in response.message.content if getattr(block, "type", None) == "text"]
            return "\n".join(texts)
        except Exception as e:
            logger.error(f"Error in generate_text: {str(e)}")
            return None

    async def generate_stream(
        self,
        prompt: str,
        chat_history: list = [],
        max_output_tokens: int = settings.DAFAULT_GENERATION_MAX_TOKENS,
        temperature: float = settings.DEFAULT_GENERATION_TEMPERATURE,
    ):
        """
        دالة توليد النصوص تدفقياً (Streaming) متوافقة مع Cohere V2
        """
        if not self.client or not self.generation_model_id:
            logger.error("CoHere client or model ID was not set")
            return

        messages = [
            {
                "role": message["role"],
                "content": message["text"],
            }
            for message in chat_history
        ]
        messages.append({"role": MsgRoles.USER.value, "content": self.process_text(prompt)})

        try:
            response = self.client.chat_stream(
                model=self.generation_model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=max_output_tokens,
            )

            for event in response:
                # استخراج النصوص تدفقياً من أحداث Cohere V2
                if hasattr(event, "type") and event.type == "content-delta":
                    delta = getattr(event, "delta", None)
                    if delta and hasattr(delta, "message"):
                        msg = delta.message
                        if msg and hasattr(msg, "content"):
                            content = msg.content
                            if content and hasattr(content, "text"):
                                text_chunk = content.text
                                if text_chunk:
                                    yield text_chunk
                elif hasattr(event, "text") and event.text:
                    yield event.text
        except Exception as e:
            logger.error(f"Error during CoHere streaming: {str(e)}")
            yield f"\n\n[ERROR]: {str(e)}"

    def construct_prompt(self, prompt: str, role: str):
        return {
            "role": role,
            "text": prompt,
        }
