from enum import Enum


class GenerationRolesEnums(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
