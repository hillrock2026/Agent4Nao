"""Conversation domain errors.

Explicit, typed errors for the session boundary. These are carried on
:class:`TurnResult` (not raised across the public ``send`` boundary) so callers
can handle outcomes without control-flow exceptions.
"""

from __future__ import annotations


class ConversationError(Exception):
    """Base class for conversation domain errors."""


class EmptyInputError(ConversationError):
    def __init__(self) -> None:
        super().__init__("input is empty or whitespace-only")


class InputTooLargeError(ConversationError):
    def __init__(self, size: int, limit: int) -> None:
        self.size = size
        self.limit = limit
        super().__init__(f"input of {size} chars exceeds limit {limit}")


class SessionClosedError(ConversationError):
    def __init__(self) -> None:
        super().__init__("session is closed")


class ConcurrentRequestError(ConversationError):
    def __init__(self) -> None:
        super().__init__("a generation is already in flight for this session")


class ModelTimeoutError(ConversationError):
    def __init__(self, detail: str = "model generation timed out") -> None:
        super().__init__(detail)


class ModelUnavailableError(ConversationError):
    def __init__(self, detail: str = "model provider unavailable") -> None:
        super().__init__(detail)


class ProviderProtocolError(ConversationError):
    def __init__(self, detail: str = "provider protocol error") -> None:
        super().__init__(detail)


class InvalidModelResponseError(ConversationError):
    def __init__(self, detail: str = "invalid model response") -> None:
        super().__init__(detail)


class CancelledError(ConversationError):
    def __init__(self, detail: str = "request cancelled") -> None:
        super().__init__(detail)


class ModelFailureError(ConversationError):
    def __init__(self, detail: str = "model failure") -> None:
        super().__init__(detail)
