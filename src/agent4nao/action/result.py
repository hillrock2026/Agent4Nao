"""Typed action result and observation.

Every result is correlated to its original request by ``request_id``. Results
are immutable; nested ``payload``/``summary`` mappings are defensively copied so
serialization never exposes a shared mutable reference.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from agent4nao.action.schema import ActionStatus, Capability, ErrorCategory


@dataclass(frozen=True)
class Observation:
    """A correlated observation summary produced by a simulated capability."""

    request_id: str
    observed_at: float
    capability: Capability
    summary: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary", dict(self.summary))

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "observed_at": self.observed_at,
            "capability": self.capability.value,
            "summary": dict(self.summary),
        }


@dataclass(frozen=True)
class ActionResult:
    """The typed outcome of one action request."""

    request_id: str
    status: ActionStatus
    error_category: ErrorCategory = ErrorCategory.NONE
    reason: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0
    duration_seconds: float = 0.0
    payload: Optional[Mapping[str, Any]] = None
    observation: Optional[Observation] = None

    def __post_init__(self) -> None:
        if self.payload is not None:
            object.__setattr__(self, "payload", dict(self.payload))

    @property
    def is_terminal(self) -> bool:
        return self.status.is_terminal

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "status": self.status.value,
            "error_category": self.error_category.value,
            "reason": self.reason,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "payload": None if self.payload is None else dict(self.payload),
            "observation": (
                None if self.observation is None else self.observation.to_dict()
            ),
        }
