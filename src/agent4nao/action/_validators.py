"""Low-level validation primitives shared by the action contract.

Kept private: only the action package uses these helpers. They enforce strict
type and format rules (finite floats, canonical UUID strings) so that a typed
action value cannot be constructed with ``bool``/``NaN``/``inf`` or a
malformed identifier.
"""

from __future__ import annotations

import math
import re

from agent4nao.action.errors import InvalidIdentifierError, InvalidParametersError

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def is_uuid(value: object) -> bool:
    """Return True for a strictly formatted hyphenated UUID string."""
    if not isinstance(value, str):
        return False
    return _UUID_RE.match(value) is not None


def require_uuid(value: object, name: str) -> str:
    """Validate *value* as a UUID string and return it, else raise."""
    if not isinstance(value, str) or not is_uuid(value):
        raise InvalidIdentifierError(
            f"{name} must be a UUID string, got {value!r}")
    return value


def require_finite_float(value: object, name: str) -> float:
    """Require a finite number; reject bool, NaN, and +/-inf."""
    if isinstance(value, bool):
        raise InvalidParametersError(f"{name} must be a finite number, got bool")
    if not isinstance(value, (int, float)):
        raise InvalidParametersError(
            f"{name} must be a finite number, got {type(value).__name__}")
    number = float(value)
    if not math.isfinite(number):
        raise InvalidParametersError(f"{name} must be finite, got {value!r}")
    return number


def require_string(value: object, name: str, non_empty: bool = True) -> str:
    """Require a string, optionally non-empty."""
    if not isinstance(value, str):
        raise InvalidParametersError(
            f"{name} must be a string, got {type(value).__name__}")
    if non_empty and not value:
        raise InvalidParametersError(f"{name} must not be empty")
    return value
