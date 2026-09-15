"""Typed action request.

The request is an immutable (``frozen``) value object that validates all
invariants in ``__post_init__``, so the only way to obtain a valid request is a
validated construction (via :func:`~agent4nao.action.validation.build_request`
or :func:`~agent4nao.action.validation.request_from_dict`). Any construction
that violates schema version, identifier format, capability/parameter pairing,
TTL bounds, or priority rules raises immediately.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from agent4nao.action._validators import require_finite_float, require_uuid
from agent4nao.action.errors import (
    InvalidParametersError,
    SchemaVersionError,
)
from agent4nao.action.parameters import (
    ObserveParameters,
    StandParameters,
    StopParameters,
    WalkParameters,
    parameter_type,
    parameters_to_dict,
)
from agent4nao.action.schema import (
    SCHEMA_VERSION,
    TTL_MAX_SECONDS,
    Capability,
    Priority,
)

Parameters = Union[ObserveParameters, StopParameters, StandParameters, WalkParameters]


@dataclass(frozen=True)
class ActionRequest:
    """A validated, explicitly-authorized, typed action request."""

    schema_version: str
    request_id: str
    session_id: str
    turn_id: str
    capability: Capability
    parameters: Parameters
    created_at: float
    ttl_seconds: float
    priority: Priority
    idempotency_key: str

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise SchemaVersionError(
                f"unsupported schema version {self.schema_version!r}; "
                f"expected {SCHEMA_VERSION!r}")
        require_uuid(self.request_id, "request_id")
        require_uuid(self.session_id, "session_id")
        require_uuid(self.turn_id, "turn_id")
        require_uuid(self.idempotency_key, "idempotency_key")

        if not isinstance(self.capability, Capability):
            raise InvalidParametersError("capability must be a Capability")
        expected = parameter_type(self.capability)
        if not isinstance(self.parameters, expected):
            raise InvalidParametersError(
                f"capability {self.capability.value} requires "
                f"{expected.__name__} parameters, got {type(self.parameters).__name__}")

        require_finite_float(self.created_at, "created_at")
        ttl = require_finite_float(self.ttl_seconds, "ttl_seconds")
        if not (0.0 < ttl <= TTL_MAX_SECONDS):
            raise InvalidParametersError(
                f"ttl_seconds must be in (0, {TTL_MAX_SECONDS}], got {ttl!r}")
        object.__setattr__(self, "ttl_seconds", ttl)

        if not isinstance(self.priority, Priority):
            raise InvalidParametersError("priority must be a Priority")
        if self.capability is Capability.STOP:
            if self.priority is not Priority.EMERGENCY:
                raise InvalidParametersError(
                    "stop capability requires EMERGENCY priority")
        elif self.priority is not Priority.NORMAL:
            raise InvalidParametersError(
                "only stop capability may use EMERGENCY priority")

    def to_dict(self) -> dict:
        """Serialize to a plain JSON-safe dict (no shared mutable references)."""
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "capability": self.capability.value,
            "parameters": parameters_to_dict(self.parameters),
            "created_at": self.created_at,
            "ttl_seconds": self.ttl_seconds,
            "priority": self.priority.value,
            "idempotency_key": self.idempotency_key,
        }
