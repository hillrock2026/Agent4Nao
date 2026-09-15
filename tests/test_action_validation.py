"""Capability parameter validation: Observe field set and Walk constraints."""

import pytest

from agent4nao.action import (
    OBSERVE_FIELDS,
    Capability,
    InvalidParametersError,
    ObserveParameters,
    StandParameters,
    StopParameters,
    UnknownFieldError,
    WalkParameters,
    parameters_from_dict,
)


def test_observe_full_defaults() -> None:
    params = ObserveParameters()
    assert params.fields is None


def test_observe_subset_fields() -> None:
    params = ObserveParameters(fields=["battery_pct", "posture"])
    assert params.fields == ("battery_pct", "posture")


def test_observe_unknown_field_rejected() -> None:
    with pytest.raises(InvalidParametersError):
        ObserveParameters(fields=["camera"])


def test_observe_duplicate_field_rejected() -> None:
    with pytest.raises(InvalidParametersError):
        ObserveParameters(fields=["battery_pct", "battery_pct"])


def test_observe_fields_from_dict() -> None:
    params = parameters_from_dict(Capability.OBSERVE, {"fields": ["fall_state"]})
    assert isinstance(params, ObserveParameters)
    assert params.fields == ("fall_state",)


def test_observe_unknown_field_in_dict_rejected() -> None:
    with pytest.raises(UnknownFieldError):
        parameters_from_dict(Capability.OBSERVE, {"bogus": 1})


def test_stop_and_stand_accept_no_parameters() -> None:
    assert isinstance(parameters_from_dict(Capability.STOP, {}), StopParameters)
    assert isinstance(parameters_from_dict(Capability.STAND, {}), StandParameters)


def test_stop_rejects_parameters() -> None:
    with pytest.raises(UnknownFieldError):
        parameters_from_dict(Capability.STOP, {"speed": 0.1})


def test_walk_missing_field_rejected() -> None:
    with pytest.raises(InvalidParametersError):
        parameters_from_dict(Capability.WALK, {"distance_m": 0.3})


def test_walk_extra_field_rejected() -> None:
    with pytest.raises(UnknownFieldError):
        parameters_from_dict(Capability.WALK, {"distance_m": 0.3, "speed": 0.2, "x": 1})


def test_parameters_must_be_object() -> None:
    with pytest.raises(InvalidParametersError):
        parameters_from_dict(Capability.WALK, [0.3, 0.2])
    with pytest.raises(InvalidParametersError):
        parameters_from_dict(Capability.WALK, "forward")


def test_walk_parameters_round_trip() -> None:
    params = WalkParameters(distance_m=0.5, speed=0.25)
    assert params.distance_m == 0.5
    assert params.speed == 0.25


def test_observe_fields_membership() -> None:
    assert set(OBSERVE_FIELDS) == {"battery_pct", "posture", "fall_state"}
