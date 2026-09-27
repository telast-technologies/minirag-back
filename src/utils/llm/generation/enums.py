from enum import Enum


class MsgRoles(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
