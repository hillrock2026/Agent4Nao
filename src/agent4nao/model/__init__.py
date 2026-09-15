"""Agent4NAO model boundary package.

Provider-neutral model requests, results, and providers (Ollama adapter and a
deterministic fake for tests).
"""

from agent4nao.model.messages import Message, ROLE_ASSISTANT, ROLE_SYSTEM, ROLE_USER
from agent4nao.model.provider import ModelProvider
from agent4nao.model.request import ModelRequest
from agent4nao.model.result import ModelErrorCategory, ModelResult, ModelStatus
from agent4nao.model.fake import FakeModelProvider
from agent4nao.model.ollama import OllamaProvider

__all__ = [
    "Message",
    "ROLE_ASSISTANT",
    "ROLE_SYSTEM",
    "ROLE_USER",
    "ModelProvider",
    "ModelRequest",
    "ModelErrorCategory",
    "ModelResult",
    "ModelStatus",
    "FakeModelProvider",
    "OllamaProvider",
]
