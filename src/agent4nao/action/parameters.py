"""Typed, capability-specific parameter value objects.

Each parameter type is an immutable (``frozen``) value object that validates its
own invariants in ``__post_init__``, so a parameter cannot be constructed in a
form that violates its capability schema. ``Walk`` is intentionally constrained:
it accepts only ``distance_m`` in ``(0, 1.0]`` and ``speed`` in ``(0, 0.5]`` and
rejects arbitrary dictionaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from agent4nao.action._validators import require_finite_float
from agent4nao.action.errors import InvalidParametersError, UnknownFieldError
from agent4nao.action.schema import Capability

OBSERVE_FIELDS = ("battery_pct", "posture", "fall_state")

WALK_MAX_DISTANCE_M = 1.0
WALK_MAX_SPEED = 0.5


@dataclass(frozen=True)
class ObserveParameters:
    """Read-only observation request. ``fields=None`` requests the full summary."""

    fields: Optional[Tuple[str, ...]] = None

    def __post_init__(self) -> None:
        if self.fields is None:
            return
        if isinstance(self.fields, str):
            raise InvalidParametersError(
                "ObserveParameters.fields must be a list of field names, not a string")
        fields = tuple(self.fields)
        for name in fields:
            if name not in OBSERVE_FIELDS:
                raise InvalidParametersError(
                    f"unknown observe field {name!r}; allowed {OBSERVE_FIELDS}")
        if len(set(fields)) != len(fields):
            raise InvalidParametersError(
                "ObserveParameters.fields must not contain duplicates")
        object.__setattr__(self, "fields", fields)


@dataclass(frozen=True)
class StopParameters:
    """Emergency stop. Accepts no parameters."""


@dataclass(frozen=True)
class StandParameters:
    """Stand up. Accepts no parameters."""


@dataclass(frozen=True)
class WalkParameters:
    """Constrained walk: forward distance and speed, both strictly bounded."""

    distance_m: float
    speed: float

    def __post_init__(self) -> None:
        distance = require_finite_float(self.distance_m, "distance_m")
        speed = require_finite_float(self.speed, "speed")
        if not (0.0 < distance <= WALK_MAX_DISTANCE_M):
            raise InvalidParametersError(
                f"distance_m must be in (0, {WALK_MAX_DISTANCE_M}], got {distance!r}")
        if not (0.0 < speed <= WALK_MAX_SPEED):
            raise InvalidParametersError(
                f"speed must be in (0, {WALK_MAX_SPEED}], got {speed!r}")
        object.__setattr__(self, "distance_m", distance)
        object.__setattr__(self, "speed", speed)


_PARAMETER_TYPES = {
    Capability.OBSERVE: ObserveParameters,
    Capability.STOP: StopParameters,
    Capability.STAND: StandParameters,
    Capability.WALK: WalkParameters,
}


def parameter_type(capability: Capability) -> type:
    return _PARAMETER_TYPES[capability]


def parameters_from_dict(capability: Capability, data: object) -> object:
    """Strictly build a typed parameter object from a raw dict.

    Unknown fields, missing required fields, and type/range violations raise.
    """
    if not isinstance(data, dict):
        raise InvalidParametersError(
            f"parameters for {capability.value} must be an object, "
            f"got {type(data).__name__}")
    if capability is Capability.OBSERVE:
        unknown = set(data) - {"fields"}
        if unknown:
            raise UnknownFieldError(
                f"unknown observe parameters: {sorted(unknown)}")
        fields = data.get("fields")
        if fields is None:
            return ObserveParameters()
        return ObserveParameters(fields=fields)
    if capability is Capability.WALK:
        unknown = set(data) - {"distance_m", "speed"}
        if unknown:
            raise UnknownFieldError(
                f"unknown walk parameters: {sorted(unknown)}")
        missing = {"distance_m", "speed"} - set(data)
        if missing:
            raise InvalidParametersError(
                f"walk parameters missing required fields: {sorted(missing)}")
        return WalkParameters(distance_m=data["distance_m"], speed=data["speed"])
    # Stop and Stand accept no parameters.
    if data:
        raise UnknownFieldError(
            f"{capability.value} accepts no parameters, got {sorted(data)}")
    return parameter_type(capability)()


def parameters_to_dict(parameters: object) -> dict:
    """Serialize a typed parameter object back to a plain dict."""
    if isinstance(parameters, ObserveParameters):
        if parameters.fields is None:
            return {}
        return {"fields": list(parameters.fields)}
    if isinstance(parameters, WalkParameters):
        return {"distance_m": parameters.distance_m, "speed": parameters.speed}
    if isinstance(parameters, (StopParameters, StandParameters)):
        return {}
    raise InvalidParametersError(
        f"unhandled parameters type {type(parameters).__name__}")
