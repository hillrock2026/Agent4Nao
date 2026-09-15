"""Provider-neutral model request."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from agent4nao.model.messages import Message


@dataclass(frozen=True)
class ModelRequest:
    """A bounded generation request sent to a model provider."""

    model: str
    messages: Tuple[Message, ...]
    request_id: str
    timeout_seconds: float
