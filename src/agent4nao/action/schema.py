"""Agent4NAO Phase 2 action schema constants and enums.

This module defines the versioned, Agent4NAO-owned *simulation* action
contract. It is explicitly NOT:

- an Agent-Kernel ``ak::agent::ModelAction``;
- a NAOqi command;
- a final network protocol version.

It exists to prove the desktop authorization boundary before any real
transport, ROS 2, NAOqi, or actuator integration is introduced. The contract
is owned by Agent4NAO and may later be mapped to a real NAO Execution Agent,
but it never executes a real robot in this phase.
"""

from __future__ import annotations

from enum import Enum

SCHEMA_VERSION = "1.0"
TTL_MAX_SECONDS = 60.0
DEFAULT_TTL_SECONDS = 5.0
DEFAULT_QUEUE_CAPACITY = 2


class Capability(str, Enum):
    OBSERVE = "observe"
    STOP = "stop"
    STAND = "stand"
    WALK = "walk"


class Priority(str, Enum):
    EMERGENCY = "emergency"
    NORMAL = "normal"

    @property
    def rank(self) -> int:
        """Lower rank means higher priority (``EMERGENCY`` < ``NORMAL``)."""
        return 0 if self is Priority.EMERGENCY else 1


class ActionStatus(str, Enum):
    ACCEPTED = "accepted"
    RUNNING = "running"
    COMPLETED = "completed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in _TERMINAL_STATUSES


_TERMINAL_STATUSES = frozenset(
    {
        ActionStatus.COMPLETED,
        ActionStatus.REJECTED,
        ActionStatus.EXPIRED,
        ActionStatus.CANCELLED,
        ActionStatus.FAILED,
    }
)


class ErrorCategory(str, Enum):
    NONE = "none"
    INVALID_PARAMETERS = "invalid_parameters"
    SCHEMA_INCOMPATIBLE = "schema_incompatible"
    UNKNOWN_REQUEST = "unknown_request"
    DUPLICATE = "duplicate"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    STALE = "stale"
    CANCELLED = "cancelled"
    TARGET_UNAVAILABLE = "target_unavailable"
    RESOURCE_CONFLICT = "resource_conflict"
    QUEUE_FULL = "queue_full"
    INTERNAL = "internal"
