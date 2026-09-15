"""ActionSession: conversation integration with an explicit authorization path."""

from uuid import uuid4

from agent4nao.action import (
    ActionStatus,
    Capability,
    ErrorCategory,
    ProposedAction,
    parse_proposal,
)
from agent4nao.conversation import ActionSession, ActionTurn, TurnStatus
from agent4nao.execution import FakeClock, FakeNAOExecutionAgent
from agent4nao.model.fake import FakeModelProvider

PROPOSAL_WALK = '{"capability": "walk", "parameters": {"distance_m": 0.3, "speed": 0.2}}'
PROPOSAL_OBSERVE = '{"capability": "observe", "parameters": {}}'


def test_pure_text_conversation_unchanged_without_agent() -> None:
    session = ActionSession(FakeModelProvider(fixed_response="hello there"))
    turn = session.send("hi")
    assert isinstance(turn, ActionTurn)
    assert turn.ok
    assert turn.status is TurnStatus.OK
    assert turn.assistant_text == "hello there"
    assert turn.proposal is None
    assert turn.result is None
    assert not turn.executed


def test_free_form_model_text_produces_no_proposal() -> None:
    session = ActionSession(FakeModelProvider(fixed_response="please walk forward"))
    turn = session.send("move")
    assert turn.ok
    assert turn.proposal is None
    assert turn.result is None


def test_send_never_executes_even_for_proposal_text() -> None:
    agent = FakeNAOExecutionAgent(clock=FakeClock())
    session = ActionSession(
        FakeModelProvider(fixed_response=PROPOSAL_WALK), execution_agent=agent)
    turn = session.send("walk")
    assert turn.ok
    assert isinstance(turn.proposal, ProposedAction)
    # A proposal was parsed, but no action was executed without authorization.
    assert turn.result is None
    assert not turn.executed
    assert agent.events == []


def test_authorize_without_agent_yields_explicit_unavailable() -> None:
    session = ActionSession(FakeModelProvider(fixed_response=PROPOSAL_WALK))
    proposal = parse_proposal(PROPOSAL_WALK)
    turn = session.authorize(proposal)
    assert turn.executed
    assert turn.action is not None
    assert turn.result.status is ActionStatus.REJECTED
    assert turn.result.error_category is ErrorCategory.TARGET_UNAVAILABLE
    assert "no execution target configured" in turn.rejection


def test_authorize_executes_against_fake_agent() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock)
    session = ActionSession(
        FakeModelProvider(fixed_response=PROPOSAL_WALK),
        execution_agent=agent, clock=clock)
    proposal = parse_proposal(PROPOSAL_WALK)
    turn = session.authorize(proposal)

    assert turn.executed
    assert turn.action.session_id == session.session_id
    assert turn.action.capability is Capability.WALK
    assert turn.result.status is ActionStatus.COMPLETED
    assert turn.result.payload == {"distance_m": 0.3, "speed": 0.2}
    assert turn.result.request_id == turn.action.request_id


def test_authorize_rejects_invalid_parameters() -> None:
    agent = FakeNAOExecutionAgent(clock=FakeClock())
    session = ActionSession(
        FakeModelProvider(fixed_response="x"), execution_agent=agent)
    proposal = parse_proposal(
        '{"capability": "walk", "parameters": {"distance_m": 99.0, "speed": 0.2}}')
    turn = session.authorize(proposal)
    assert turn.result.status is ActionStatus.REJECTED
    assert turn.result.error_category is ErrorCategory.INVALID_PARAMETERS


def test_authorize_requires_proposed_action() -> None:
    session = ActionSession(FakeModelProvider(fixed_response="x"))
    turn = session.authorize("walk forward")  # type: ignore[arg-type]
    assert turn.result.error_category is ErrorCategory.INVALID_PARAMETERS


def test_observe_result_flows_through_observation() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock)
    session = ActionSession(
        FakeModelProvider(fixed_response=PROPOSAL_OBSERVE),
        execution_agent=agent, clock=clock)
    proposal = parse_proposal(PROPOSAL_OBSERVE)
    turn = session.authorize(proposal)

    assert turn.result.status is ActionStatus.COMPLETED
    assert turn.observation is not None
    assert turn.observation.summary["battery_pct"] == 87


def test_end_to_end_conversation_to_execution() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock)
    session = ActionSession(
        FakeModelProvider(fixed_response=PROPOSAL_WALK),
        execution_agent=agent, clock=clock)

    turn = session.send("go forward a bit")
    assert turn.proposal is not None
    result_turn = session.authorize(turn.proposal, turn_id=turn.turn_id)
    assert result_turn.action.turn_id == turn.turn_id
    assert result_turn.result.status is ActionStatus.COMPLETED


def test_text_conversation_still_usable_when_target_absent() -> None:
    session = ActionSession(FakeModelProvider(fixed_response="still chatting"))
    first = session.send("hello")
    second = session.send("how are you")
    assert first.ok and second.ok
    assert first.result is None and second.result is None
    assert len(session.history()) == 4
