"""Action request schema: valid/invalid construction and (de)serialization."""

import json
from dataclasses import replace
from uuid import uuid4

import pytest

from agent4nao.action import (
    DEFAULT_TTL_SECONDS,
    SCHEMA_VERSION,
    TTL_MAX_SECONDS,
    ActionRequest,
    Capability,
    InvalidIdentifierError,
    InvalidParametersError,
    Priority,
    SchemaValidationError,
    SchemaVersionError,
    UnknownFieldError,
    WalkParameters,
    build_request,
    request_from_dict,
    request_from_json,
    request_to_dict,
    request_to_json,
)


def ids(**kw):
    return {
        "request_id": kw.get("request_id", str(uuid4())),
        "session_id": kw.get("session_id", str(uuid4())),
        "turn_id": kw.get("turn_id", str(uuid4())),
        "idempotency_key": kw.get("idempotency_key", str(uuid4())),
    }


def make_walk(**overrides):
    base = ids()
    base.update(overrides)
    return build_request(
        capability=Capability.WALK,
        parameters=WalkParameters(distance_m=0.3, speed=0.2),
        **base,
    )


# 1. valid action schema -------------------------------------------------

def test_valid_walk_request() -> None:
    req = make_walk()
    assert isinstance(req, ActionRequest)
    assert req.schema_version == SCHEMA_VERSION
    assert req.capability is Capability.WALK
    assert req.parameters.distance_m == 0.3
    assert req.parameters.speed == 0.2
    assert req.priority is Priority.NORMAL
    assert req.ttl_seconds == DEFAULT_TTL_SECONDS


def test_request_round_trip_dict() -> None:
    req = make_walk()
    data = request_to_dict(req)
    again = request_from_dict(data)
    assert again == req


def test_request_round_trip_json() -> None:
    req = make_walk()
    again = request_from_json(request_to_json(req))
    assert again == req


def test_to_dict_is_json_serializable_and_deterministic() -> None:
    req = make_walk()
    first = json.dumps(request_to_dict(req), sort_keys=True)
    second = json.dumps(request_to_dict(req), sort_keys=True)
    assert first == second


# 14. schema version rejection ------------------------------------------

def test_unsupported_schema_version_rejected() -> None:
    req = make_walk()
    with pytest.raises(SchemaVersionError):
        replace(req, schema_version="2.0")


def test_unsupported_schema_version_rejected_from_dict() -> None:
    req = make_walk()
    data = request_to_dict(req)
    data["schema_version"] = "9.9"
    with pytest.raises(SchemaVersionError):
        request_from_dict(data)


# 2. invalid action schema ----------------------------------------------

def test_malformed_uuid_rejected() -> None:
    with pytest.raises(InvalidIdentifierError):
        make_walk(request_id="not-a-uuid")


def test_non_uuid_session_id_rejected() -> None:
    with pytest.raises(InvalidIdentifierError):
        make_walk(session_id="session-1")


def test_unknown_capability_rejected() -> None:
    with pytest.raises(InvalidParametersError):
        build_request(
            capability="jump", parameters={}, **ids())


def test_capability_parameter_mismatch_rejected() -> None:
    with pytest.raises(InvalidParametersError):
        build_request(
            capability=Capability.STOP,
            parameters=WalkParameters(distance_m=0.3, speed=0.2),
            **ids(),
        )


def test_unknown_request_field_rejected() -> None:
    req = make_walk()
    data = request_to_dict(req)
    data["surprise"] = "field"
    with pytest.raises(UnknownFieldError):
        request_from_dict(data)


def test_missing_required_field_rejected() -> None:
    req = make_walk()
    data = request_to_dict(req)
    del data["turn_id"]
    with pytest.raises(SchemaValidationError):
        request_from_dict(data)


def test_request_must_be_dict() -> None:
    with pytest.raises(SchemaValidationError):
        request_from_dict([1, 2, 3])


# construction boundary ---------------------------------------------------

def test_walk_parameters_reject_bool_nan_inf() -> None:
    for bad in (True, False, float("nan"), float("inf"), float("-inf")):
        with pytest.raises(InvalidParametersError):
            WalkParameters(distance_m=bad, speed=0.2)
        with pytest.raises(InvalidParametersError):
            WalkParameters(distance_m=0.3, speed=bad)


def test_walk_parameters_range_bounds() -> None:
    with pytest.raises(InvalidParametersError):
        WalkParameters(distance_m=0.0, speed=0.2)
    with pytest.raises(InvalidParametersError):
        WalkParameters(distance_m=1.5, speed=0.2)
    with pytest.raises(InvalidParametersError):
        WalkParameters(distance_m=0.3, speed=0.0)
    with pytest.raises(InvalidParametersError):
        WalkParameters(distance_m=0.3, speed=0.9)


def test_ttl_bounds_rejected() -> None:
    for bad in (0.0, -1.0, TTL_MAX_SECONDS + 1.0, float("nan"), float("inf"), True):
        with pytest.raises(InvalidParametersError):
            make_walk(ttl_seconds=bad)


def test_ttl_max_exactly_accepted() -> None:
    req = make_walk(ttl_seconds=TTL_MAX_SECONDS)
    assert req.ttl_seconds == TTL_MAX_SECONDS


def test_parameters_are_immutable_and_copied() -> None:
    req = make_walk()
    data = request_to_dict(req)
    data["parameters"]["distance_m"] = 999.0
    data2 = request_to_dict(req)
    assert data2["parameters"]["distance_m"] == 0.3


def test_priority_invariants() -> None:
    assert make_walk().priority is Priority.NORMAL
    stop = build_request(
        capability=Capability.STOP,
        parameters={},
        **ids(),
    )
    assert stop.priority is Priority.EMERGENCY


def test_emergency_priority_only_for_stop() -> None:
    with pytest.raises(InvalidParametersError):
        make_walk(priority=Priority.EMERGENCY)
