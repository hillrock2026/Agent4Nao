"""Authorization boundary: free-form text cannot become an executable action."""

from uuid import uuid4

import pytest

from agent4nao.action import (
    AuthorizedAction,
    Capability,
    InvalidParametersError,
    ProposedAction,
    WalkParameters,
    authorize,
    build_request_from_authorized,
    parse_proposal,
)


def sid():
    return {"session_id": str(uuid4()), "turn_id": str(uuid4())}


# 3. free-form text does not execute ------------------------------------

def test_free_form_text_does_not_parse_to_proposal() -> None:
    for text in (
        "please walk forward a little",
        "can you make the robot stand up?",
        "Walk",
        "",
        "   ",
        "not json at all {",
        "[1, 2, 3]",
        '"walk"',
        "null",
        "42",
    ):
        assert parse_proposal(text) is None


def test_proposal_requires_exact_keys() -> None:
    assert parse_proposal('{"capability": "walk"}') is None
    assert parse_proposal('{"capability": "walk", "parameters": {}, "extra": 1}') is None
    assert parse_proposal('{"capability": "jump", "parameters": {}}') is None
    assert parse_proposal('{"capability": "walk", "parameters": []}') is None


def test_valid_proposal_parses() -> None:
    proposal = parse_proposal(
        '{"capability": "walk", "parameters": {"distance_m": 0.3, "speed": 0.2}}')
    assert isinstance(proposal, ProposedAction)
    assert proposal.capability is Capability.WALK


# 4. explicit authorization is required ----------------------------------

def test_proposal_requires_authorization_before_request() -> None:
    proposal = parse_proposal(
        '{"capability": "walk", "parameters": {"distance_m": 0.3, "speed": 0.2}}')
    authorized = authorize(proposal)
    assert isinstance(authorized, AuthorizedAction)
    assert isinstance(authorized.parameters, WalkParameters)
    req = build_request_from_authorized(authorized, **sid())
    assert req.capability is Capability.WALK
    assert req.parameters.distance_m == 0.3


def test_authorize_rejects_invalid_parameters() -> None:
    proposal = parse_proposal(
        '{"capability": "walk", "parameters": {"distance_m": 99.0, "speed": 0.2}}')
    with pytest.raises(InvalidParametersError):
        authorize(proposal)


def test_authorize_requires_proposed_action() -> None:
    with pytest.raises(InvalidParametersError):
        authorize("walk forward")


def test_build_request_from_authorized_requires_authorized_action() -> None:
    with pytest.raises(InvalidParametersError):
        build_request_from_authorized("walk forward", **sid())


def test_there_is_no_string_to_request_path() -> None:
    # The action package exposes no function that maps text directly to a
    # request; parse_proposal yields None or a proposal that still needs
    # explicit authorization.
    assert parse_proposal("walk forward") is None
