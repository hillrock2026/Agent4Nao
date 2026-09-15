"""Authorization boundary: ModelResult text never becomes a typed action.

This module enforces the Phase 2 invariant::

    ModelResult (free-form assistant text) != typed ActionRequest

There is no function here (or anywhere in the action package) that turns a
``ModelResult`` or an arbitrary string directly into an ``ActionRequest``. The
only text-to-proposal path is :func:`parse_proposal`, which is strict and
returns ``None`` for free-form text. A parsed proposal must then be explicitly
:func:`authorize`-d and built via :func:`build_request_from_authorized` before a
request exists.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Optional

from agent4nao.action.errors import InvalidParametersError
from agent4nao.action.parameters import parameters_from_dict
from agent4nao.action.request import ActionRequest
from agent4nao.action.schema import Capability
from agent4nao.action.validation import build_request

_PROPOSAL_KEYS = {"capability", "parameters"}


@dataclass(frozen=True)
class ProposedAction:
    """A candidate action parsed from a model output. Not yet authorized."""

    capability: Capability
    parameters: object  # raw dict; validated and typed only at authorization


@dataclass(frozen=True)
class AuthorizedAction:
    """An explicitly authorized action with validated, typed parameters."""

    capability: Capability
    parameters: object  # typed, validated parameter value object
    authorized_at: float


def _coerce_capability_lenient(value: object) -> Optional[Capability]:
    if not isinstance(value, str):
        return None
    try:
        return Capability(value)
    except ValueError:
        return None


def parse_proposal(text: object) -> Optional[ProposedAction]:
    """Strictly parse a proposal string; return ``None`` for free-form text.

    Recognized format is a JSON object with exactly the keys ``capability`` and
    ``parameters`` and a known capability. Anything else (including arbitrary
    assistant prose) yields ``None`` and can never become an action.
    """
    if not isinstance(text, str) or not text.strip():
        return None
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    if set(data.keys()) != _PROPOSAL_KEYS:
        return None
    capability = _coerce_capability_lenient(data.get("capability"))
    if capability is None:
        return None
    if not isinstance(data.get("parameters"), dict):
        return None
    return ProposedAction(capability=capability, parameters=data["parameters"])


def authorize(proposed: ProposedAction, *, clock: object = None) -> AuthorizedAction:
    """Explicitly authorize a proposal into a validated, typed action.

    Validates and types the proposal's raw parameters against the capability
    schema, raising :class:`InvalidParametersError` on violation.
    """
    if not isinstance(proposed, ProposedAction):
        raise InvalidParametersError("authorize requires a ProposedAction")
    parameters = parameters_from_dict(proposed.capability, proposed.parameters)
    authorized_at = clock.now() if clock is not None else time.time()
    return AuthorizedAction(
        capability=proposed.capability,
        parameters=parameters,
        authorized_at=authorized_at,
    )


def build_request_from_authorized(
    authorized: AuthorizedAction,
    *,
    session_id: object,
    turn_id: object,
    clock: object = None,
    ttl_seconds: object = None,
) -> ActionRequest:
    """Build a validated request from an authorized action."""
    if not isinstance(authorized, AuthorizedAction):
        raise InvalidParametersError(
            "build_request_from_authorized requires an AuthorizedAction")
    kwargs = {"clock": clock}
    if ttl_seconds is not None:
        kwargs["ttl_seconds"] = ttl_seconds
    return build_request(
        capability=authorized.capability,
        parameters=authorized.parameters,
        session_id=session_id,
        turn_id=turn_id,
        **kwargs,
    )
