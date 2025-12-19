from enum import Enum
from pydantic import BaseModel

class LLMModel(str, Enum):
    qwen = "qwen"
    deepseek = "deepseek"
    gemma = "gemma"

class ChatMode(str, Enum):
    ask = "ask"
    agent = "agent"
    local = "local"

class UserTopologyIn(BaseModel):
    username: str
    password: str

class ChatMessageIn(BaseModel):
    content: str
    model: LLMModel
    mode: ChatMode = ChatMode.agent