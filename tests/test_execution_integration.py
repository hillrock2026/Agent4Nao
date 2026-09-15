"""End-to-end authorization -> execution path and conversation independence."""

from uuid import uuid4

from agent4nao.action import (
    ActionStatus,
    authorize,
    build_request_from_authorized,
    parse_proposal,
)
from agent4nao.conversation import ConversationSession
from agent4nao.execution import FakeClock, FakeNAOExecutionAgent
from agent4nao.model.fake import FakeModelProvider


def test_conversation_works_without_execution_target() -> None:
    # No FakeNAOExecutionAgent is constructed at all: pure text conversation
    # must remain fully usable (Phase 2 adds an optional simulation boundary,
    # it does not require the target to exist).
    session = ConversationSession(FakeModelProvider(fixed_response="hello"))
    result = session.send("hi")
    assert result.ok
    assert result.message == "hello"


def test_model_text_still_not_an_action_without_authorization() -> None:
    # A ModelResult's free-form payload cannot become an action by itself.
    provider = FakeModelProvider(fixed_response="walk forward now")
    session = ConversationSession(provider)
    result = session.send("go")
    assert result.ok
    assert parse_proposal(result.message) is None


def test_authorized_action_end_to_end() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock)
    proposal = parse_proposal(
        '{"capability": "walk", "parameters": {"distance_m": 0.3, "speed": 0.2}}')
    authorized = authorize(proposal, clock=clock)
    request = build_request_from_authorized(
        authorized, session_id=str(uuid4()), turn_id=str(uuid4()), clock=clock)
    result = agent.submit(request)

    assert result.status is ActionStatus.COMPLETED
    assert result.request_id == request.request_id
    assert result.payload == {"distance_m": 0.3, "speed": 0.2}
