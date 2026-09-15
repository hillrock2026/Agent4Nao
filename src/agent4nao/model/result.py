"""Provider-neutral model result.

Mirrors the Agent-Kernel concept of a model result: a provider produces a
typed result (success payload or a categorized failure); interpretation into
an action is a separate, later concern (Phase 2). Phase 1 never turns a model
result into a physical action.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ModelStatus(str, Enum):
    SUCCESS = "success"
    INVALID_RESULT = "invalid_result"
    FAILURE = "failure"


class ModelErrorCategory(str, Enum):
    NONE = "none"
    INVALID_INPUT = "invalid_input"
    TIMEOUT = "timeout"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PROTOCOL_ERROR = "protocol_error"
    CANCELLED = "cancelled"
    MODEL_FAILURE = "model_failure"


@dataclass(frozen=True)
class ModelResult:
    """The outcome of one model generation request."""

    status: ModelStatus
    payload: Optional[str] = None
    category: ModelErrorCategory = ModelErrorCategory.NONE
    diagnostic: str = ""
    request_id: str = ""

    @classmethod
    def success(cls, payload: str, request_id: str = "") -> "ModelResult":
        return cls(
            status=ModelStatus.SUCCESS,
            payload=payload,
            request_id=request_id,
        )

    @classmethod
    def invalid_result(cls, diagnostic: str, request_id: str = "") -> "ModelResult":
        return cls(
            status=ModelStatus.INVALID_RESULT,
            diagnostic=diagnostic,
            request_id=request_id,
        )

    @classmethod
    def failure(
        cls,
        diagnostic: str,
        category: ModelErrorCategory,
        request_id: str = "",
    ) -> "ModelResult":
        return cls(
            status=ModelStatus.FAILURE,
            category=category,
            diagnostic=diagnostic,
            request_id=request_id,
        )

    @property
    def is_success(self) -> bool:
        return self.status is ModelStatus.SUCCESS

    @property
    def is_invalid_result(self) -> bool:
        return self.status is ModelStatus.INVALID_RESULT

    @property
    def is_failure(self) -> bool:
        return self.status is ModelStatus.FAILURE
