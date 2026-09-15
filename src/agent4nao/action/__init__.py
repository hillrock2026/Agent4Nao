"""Agent4NAO Phase 2 action contract package.

Agent-owned, versioned, validated action/result/observation schemas plus the
explicit authorization boundary. This is a desktop simulation contract, not an
Agent-Kernel ``ModelAction``, a NAOqi command, or a network protocol.
"""

from agent4nao.action.errors import (
    ActionError,
    InvalidIdentifierError,
    InvalidParametersError,
    SchemaValidationError,
    SchemaVersionError,
    UnknownFieldError,
)
from agent4nao.action.parameters import (
    OBSERVE_FIELDS,
    ObserveParameters,
    StandParameters,
    StopParameters,
    WalkParameters,
    parameters_from_dict,
    parameters_to_dict,
)
from agent4nao.action.request import ActionRequest
from agent4nao.action.result import ActionResult, Observation
from agent4nao.action.schema import (
    DEFAULT_TTL_SECONDS,
    SCHEMA_VERSION,
    TTL_MAX_SECONDS,
    ActionStatus,
    Capability,
    ErrorCategory,
    Priority,
)
from agent4nao.action.validation import (
    build_request,
    request_from_dict,
    request_from_json,
    request_to_dict,
    request_to_json,
)
from agent4nao.action.authorization import (
    AuthorizedAction,
    ProposedAction,
    authorize,
    build_request_from_authorized,
    parse_proposal,
)

__all__ = [
    "ActionError",
    "InvalidIdentifierError",
    "InvalidParametersError",
    "SchemaValidationError",
    "SchemaVersionError",
    "UnknownFieldError",
    "OBSERVE_FIELDS",
    "ObserveParameters",
    "StandParameters",
    "StopParameters",
    "WalkParameters",
    "parameters_from_dict",
    "parameters_to_dict",
    "ActionRequest",
    "ActionResult",
    "Observation",
    "DEFAULT_TTL_SECONDS",
    "SCHEMA_VERSION",
    "TTL_MAX_SECONDS",
    "ActionStatus",
    "Capability",
    "ErrorCategory",
    "Priority",
    "build_request",
    "request_from_dict",
    "request_from_json",
    "request_to_dict",
    "request_to_json",
    "AuthorizedAction",
    "ProposedAction",
    "authorize",
    "build_request_from_authorized",
    "parse_proposal",
]
