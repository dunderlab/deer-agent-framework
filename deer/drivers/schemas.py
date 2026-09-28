from enum import Enum
from pydantic import BaseModel, Field


class Role(str, Enum):
    """
    Strict enumeration of allowed roles in a conversation.
    Using 'str' as a mixin allows the role to be treated as a string
    while maintaining Enum validation.
    """

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ChatMessage(BaseModel):
    """
    A single message in a conversation history.
    Ensures that every message has a role and content.
    """

    role: Role = Field(..., description="The role of the message sender.")
    content: str = Field(..., description="The actual text content of the message.")
