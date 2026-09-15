"""Provider-neutral model boundary.

The session depends only on this interface; concrete providers (Ollama, fake)
implement it. Ollama-specific types never leak past the provider adapter.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from agent4nao.model.request import ModelRequest
from agent4nao.model.result import ModelResult


class ModelProvider(ABC):
    """Synchronous, provider-neutral model boundary."""

    name: str = "model"

    @abstractmethod
    def generate(self, request: ModelRequest) -> ModelResult:
        """Produce one ModelResult for a request.

        Implementations must return a typed :class:`ModelResult` and should
        prefer a categorized failure over raising, so the session can map
        failures to explicit domain outcomes.
        """

    def cancel(self, request_id: str = "") -> None:
        """Best-effort cancellation.

        Providers that cannot hard-cancel an in-flight request (e.g. a blocking
        HTTP call) must document that semantic. The default is a no-op.
        """
        return None
