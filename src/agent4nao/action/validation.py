"""Action request construction and (de)serialization.

This module is the only sanctioned way to build an :class:`ActionRequest` from
either explicit arguments or a strict dictionary. It also provides JSON
serialization. Validation is deterministic and raises typed
:class:`~agent4nao.action.errors.SchemaValidationError` subclasses.
"""

from __future__ import annotations

import json
import time
from typing import Optional
from uuid import uuid4

from agent4nao.action.errors import (
    InvalidParametersError,
    SchemaValidationError,
    UnknownFieldError,
)
from agent4nao.action.parameters import (
    parameter_type,
    parameters_from_dict,
)
from agent4nao.action.request import ActionRequest
from agent4nao.action.schema import (
    DEFAULT_TTL_SECONDS,
    SCHEMA_VERSION,
    Capability,
    Priority,
)

_REQUEST_FIELDS = {
    "schema_version",
    "request_id",
    "session_id",
    "turn_id",
    "capability",
    "parameters",
    "created_at",
    "ttl_seconds",
    "priority",
    "idempotency_key",
}


def _coerce_capability(value: object) -> Capability:
    if isinstance(value, Capability):
        return value
    if isinstance(value, str):
        try:
            return Capability(value)
        except ValueError:
            raise InvalidParametersError(f"unknown capability {value!r}") from None
    raise InvalidParametersError(
        f"capability must be a Capability or string, got {type(value).__name__}")


def _coerce_priority(value: object) -> Priority:
    if isinstance(value, Priority):
        return value
    if isinstance(value, str):
        try:
            return Priority(value)
        except ValueError:
            raise InvalidParametersError(f"unknown priority {value!r}") from None
    raise InvalidParametersError(
        f"priority must be a Priority or string, got {type(value).__name__}")


def _coerce_parameters(capability: Capability, parameters: object) -> object:
    if isinstance(parameters, dict):
        return parameters_from_dict(capability, parameters)
    expected = parameter_type(capability)
    if isinstance(parameters, expected):
        return parameters
    raise InvalidParametersError(
        f"capability {capability.value} requires {expected.__name__} parameters, "
        f"got {type(parameters).__name__}")


def default_priority(capability: Capability) -> Priority:
    return Priority.EMERGENCY if capability is Capability.STOP else Priority.NORMAL


def build_request(
    *,
    capability: object,
    parameters: object,
    session_id: object,
    turn_id: object,
    priority: object = None,
    ttl_seconds: object = DEFAULT_TTL_SECONDS,
    created_at: object = None,
    request_id: object = None,
    idempotency_key: object = None,
    clock: object = None,
) -> ActionRequest:
    """Build and validate an action request.

    Generated identifiers default to UUID4. ``created_at`` defaults to the
    supplied clock (or wall-clock time). ``priority`` defaults to EMERGENCY for
    ``stop`` and NORMAL otherwise.
    """
    cap = _coerce_capability(capability)
    params = _coerce_parameters(cap, parameters)
    if priority is None:
        priority = default_priority(cap)
    else:
        priority = _coerce_priority(priority)
    if created_at is None:
        created_at = clock.now() if clock is not None else time.time()
    if request_id is None:
        request_id = str(uuid4())
    if idempotency_key is None:
        idempotency_key = str(uuid4())
    return ActionRequest(
        schema_version=SCHEMA_VERSION,
        request_id=request_id,
        session_id=session_id,
        turn_id=turn_id,
        capability=cap,
        parameters=params,
        created_at=created_at,
        ttl_seconds=ttl_seconds,
        priority=priority,
        idempotency_key=idempotency_key,
    )


def request_from_dict(data: object) -> ActionRequest:
    """Strictly parse a request from a dict; unknown/missing fields raise."""
    if not isinstance(data, dict):
        raise SchemaValidationError(
            f"request must be an object, got {type(data).__name__}")
    unknown = set(data) - _REQUEST_FIELDS
    if unknown:
        raise UnknownFieldError(f"unknown request fields: {sorted(unknown)}")
    missing = _REQUEST_FIELDS - set(data)
    if missing:
        raise SchemaValidationError(f"missing required fields: {sorted(missing)}")

    capability = _coerce_capability(data["capability"])
    parameters = parameters_from_dict(capability, data["parameters"])
    priority = _coerce_priority(data["priority"])
    return ActionRequest(
        schema_version=data["schema_version"],
        request_id=data["request_id"],
        session_id=data["session_id"],
        turn_id=data["turn_id"],
        capability=capability,
        parameters=parameters,
        created_at=data["created_at"],
        ttl_seconds=data["ttl_seconds"],
        priority=priority,
        idempotency_key=data["idempotency_key"],
    )


def request_to_dict(request: ActionRequest) -> dict:
    return request.to_dict()


def request_to_json(request: ActionRequest) -> str:
    return json.dumps(request.to_dict(), sort_keys=True)


def request_from_json(text: str) -> ActionRequest:
    try:
        data = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise SchemaValidationError(f"request is not valid JSON: {exc}") from None
    return request_from_dict(data)
