"""Fake Execution Agent: lifecycle, idempotency, correlation, determinism."""

from uuid import uuid4

from agent4nao.action import (
    ActionStatus,
    Capability,
    ErrorCategory,
    WalkParameters,
    build_request,
)
from agent4nao.execution import FakeClock, FakeNAOExecutionAgent


def sid():
    return {
        "session_id": str(uuid4()),
        "turn_id": str(uuid4()),
    }


def make_walk(clock, *, request_id=None, idempotency_key=None, session_id=None,
              distance=0.3, speed=0.2, ttl_seconds=None):
    kwargs = sid()
    if request_id is not None:
        kwargs["request_id"] = request_id
    if idempotency_key is not None:
        kwargs["idempotency_key"] = idempotency_key
    if session_id is not None:
        kwargs["session_id"] = session_id
    if ttl_seconds is not None:
        kwargs["ttl_seconds"] = ttl_seconds
    return build_request(
        capability=Capability.WALK,
        parameters=WalkParameters(distance_m=distance, speed=speed),
        created_at=clock.now(),
        **kwargs,
    )


# lifecycle: accepted -> running -> completed ----------------------------

def test_lifecycle_with_manual_completion() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock, auto_complete=False)
    req = make_walk(clock)
    result = agent.submit(req)
    assert result.status is ActionStatus.RUNNING
    assert agent.status(req.request_id) is ActionStatus.RUNNING
    assert agent.running_motion_id == req.request_id

    clock.advance(1.5)
    done = agent.complete(req.request_id)
    assert done.status is ActionStatus.COMPLETED
    assert done.duration_seconds == 1.5
    assert done.is_terminal
    assert done.payload == {"distance_m": 0.3, "speed": 0.2}


def test_auto_complete_default() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock)
    result = agent.submit(make_walk(clock))
    assert result.status is ActionStatus.COMPLETED
    assert result.is_terminal


# 17. action duration and terminal event ---------------------------------

def test_duration_and_terminal_event_correlated() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock, auto_complete=False)
    req = make_walk(clock)
    agent.submit(req)
    clock.advance(2.0)
    done = agent.complete(req.request_id)

    assert done.status is ActionStatus.COMPLETED
    assert done.duration_seconds == 2.0
    terminal_events = [e for e in agent.events if e["request_id"] == req.request_id]
    assert terminal_events[-1]["status"] == "completed"
    assert terminal_events[-1]["duration_seconds"] == 2.0


# 8. duplicate / idempotency ---------------------------------------------

def test_duplicate_request_id_returns_cached_terminal_result() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock)
    req = make_walk(clock)
    first = agent.submit(req)
    assert first.status is ActionStatus.COMPLETED

    dup = agent.submit(req)
    assert dup.error_category is ErrorCategory.DUPLICATE
    assert dup.status is first.status
    assert dup.reason == "duplicate request; returning cached result"


def test_duplicate_while_running_returns_current_state() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock, auto_complete=False)
    req = make_walk(clock)
    agent.submit(req)
    dup = agent.submit(req)
    assert dup.error_category is ErrorCategory.DUPLICATE
    assert dup.status is ActionStatus.RUNNING


def test_same_idempotency_key_different_request_is_conflict() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock)
    session_id = str(uuid4())
    key = str(uuid4())
    first = make_walk(clock, session_id=session_id, idempotency_key=key)
    agent.submit(first)

    conflicting = make_walk(clock, session_id=session_id, idempotency_key=key)
    result = agent.submit(conflicting)
    assert result.status is ActionStatus.REJECTED
    assert result.error_category is ErrorCategory.IDEMPOTENCY_CONFLICT


def test_same_request_id_different_payload_is_conflict() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock)
    first = make_walk(clock, distance=0.3)
    agent.submit(first)

    same_id = make_walk(clock, request_id=first.request_id, distance=0.8)
    result = agent.submit(same_id)
    assert result.status is ActionStatus.REJECTED
    assert result.error_category is ErrorCategory.IDEMPOTENCY_CONFLICT


def test_expired_resubmit_same_request_returns_duplicate() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock)
    req = make_walk(clock, ttl_seconds=5.0)
    clock.advance(10.0)
    first = agent.submit(req)
    assert first.status is ActionStatus.EXPIRED

    dup = agent.submit(req)
    assert dup.error_category is ErrorCategory.DUPLICATE
    assert dup.status is ActionStatus.EXPIRED
    assert dup.reason == "duplicate request; returning cached result"


def test_expired_same_key_new_request_is_conflict() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock)
    session_id = str(uuid4())
    key = str(uuid4())
    req = make_walk(clock, session_id=session_id, idempotency_key=key, ttl_seconds=5.0)
    clock.advance(10.0)
    agent.submit(req)  # expired

    new_req = make_walk(clock, session_id=session_id, idempotency_key=key, ttl_seconds=5.0)
    result = agent.submit(new_req)
    assert result.status is ActionStatus.REJECTED
    assert result.error_category is ErrorCategory.IDEMPOTENCY_CONFLICT


def test_duplicate_submission_adds_no_execution_event() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock)
    req = make_walk(clock, ttl_seconds=5.0)
    clock.advance(10.0)
    agent.submit(req)
    before = len(agent.events)
    agent.submit(req)  # duplicate
    assert len(agent.events) == before


# 13. result/observation correlation -------------------------------------

def test_result_correlates_to_request_id() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock)
    req = make_walk(clock)
    result = agent.submit(req)
    assert result.request_id == req.request_id
    assert agent.result_for(req.request_id) is result


def test_observation_correlates_to_request() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock)
    req = build_request(
        capability=Capability.OBSERVE,
        parameters={},
        created_at=clock.now(),
        **sid(),
    )
    result = agent.submit(req)
    assert result.status is ActionStatus.COMPLETED
    assert result.observation is not None
    assert result.observation.request_id == req.request_id
    assert result.observation.summary == {
        "battery_pct": 87,
        "posture": "standing",
        "fall_state": "none",
    }


# 18. deterministic repeated simulation -----------------------------------

def _run_scenario():
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock, auto_complete=False, queue_capacity=1)
    walk = make_walk(clock)
    agent.submit(walk)
    clock.advance(1.0)
    agent.complete(walk.request_id)
    return [e["status"] for e in agent.events]


def test_repeated_simulation_is_deterministic() -> None:
    first = _run_scenario()
    second = _run_scenario()
    assert first == second
