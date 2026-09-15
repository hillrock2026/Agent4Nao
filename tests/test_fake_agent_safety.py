"""Fake Execution Agent: safety semantics (Stop, TTL, cancel, conflict, queue)."""

from uuid import uuid4

from agent4nao.action import (
    ActionStatus,
    Capability,
    ErrorCategory,
    ObserveParameters,
    WalkParameters,
    build_request,
    request_to_dict,
)
from agent4nao.execution import FakeClock, FakeNAOExecutionAgent


def sid():
    return {"session_id": str(uuid4()), "turn_id": str(uuid4())}


def make_request(clock, capability, parameters, **overrides):
    kwargs = sid()
    kwargs.update(overrides)
    return build_request(
        capability=capability,
        parameters=parameters,
        created_at=clock.now(),
        **kwargs,
    )


def make_walk(clock, **overrides):
    return make_request(clock, Capability.WALK, WalkParameters(distance_m=0.3, speed=0.2), **overrides)


# 5. Observe result -------------------------------------------------------

def test_observe_full_summary() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock)
    req = make_request(clock, Capability.OBSERVE, ObserveParameters())
    result = agent.submit(req)
    assert result.status is ActionStatus.COMPLETED
    assert result.observation.summary == {
        "battery_pct": 87, "posture": "standing", "fall_state": "none"}


def test_observe_subset_summary_preserves_canonical_order() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock)
    req = make_request(
        clock, Capability.OBSERVE, ObserveParameters(fields=["fall_state", "battery_pct"]))
    result = agent.submit(req)
    assert list(result.observation.summary.keys()) == ["battery_pct", "fall_state"]


# 6. Stop priority over motion --------------------------------------------

def test_stop_preempts_running_motion() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock, auto_complete=False)
    walk = make_walk(clock)
    agent.submit(walk)
    assert agent.running_motion_id == walk.request_id

    stop = make_request(clock, Capability.STOP, {})
    result = agent.submit(stop)
    assert result.status is ActionStatus.COMPLETED
    assert result.payload["stopped"] is True
    assert walk.request_id in result.payload["preempted"]

    walk_result = agent.result_for(walk.request_id)
    assert walk_result.status is ActionStatus.CANCELLED
    assert walk_result.error_category is ErrorCategory.CANCELLED


def test_stop_clears_waiting_queue() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock, auto_complete=False, queue_capacity=2)
    first = make_walk(clock)
    second = make_walk(clock)
    agent.submit(first)   # running
    agent.submit(second)  # waiting

    stop = make_request(clock, Capability.STOP, {})
    result = agent.submit(stop)
    assert set(result.payload["preempted"]) == {first.request_id, second.request_id}
    assert agent.result_for(second.request_id).status is ActionStatus.CANCELLED
    assert agent.waiting_count == 0
    assert agent.running_motion_id is None


# 7. stale / expired request ----------------------------------------------

def test_expired_request_rejected_at_submit() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock)
    req = make_walk(clock, ttl_seconds=5.0)
    clock.advance(10.0)
    result = agent.submit(req)
    assert result.status is ActionStatus.EXPIRED
    assert result.error_category is ErrorCategory.STALE


def test_not_expired_before_deadline() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock)
    req = make_walk(clock, ttl_seconds=5.0)
    clock.advance(4.0)  # now < created_at + ttl
    result = agent.submit(req)
    assert result.status is ActionStatus.COMPLETED


def test_not_expired_at_exact_deadline() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock)
    req = make_walk(clock, ttl_seconds=5.0)
    clock.advance(5.0)  # now == created_at + ttl (strict '>' => still valid)
    result = agent.submit(req)
    assert result.status is ActionStatus.COMPLETED


def test_expired_after_deadline() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock)
    req = make_walk(clock, ttl_seconds=5.0)
    clock.advance(5.001)  # now > created_at + ttl
    result = agent.submit(req)
    assert result.status is ActionStatus.EXPIRED
    assert result.error_category is ErrorCategory.STALE


def test_expired_request_rejected_while_waiting() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock, auto_complete=False, queue_capacity=2)
    first = make_walk(clock, ttl_seconds=60.0)    # running, stays valid
    second = make_walk(clock, ttl_seconds=1.0)    # waiting, becomes stale
    agent.submit(first)
    agent.submit(second)
    clock.advance(2.0)    # second now stale
    agent.complete(first.request_id)  # promote -> second should expire
    assert agent.result_for(second.request_id).status is ActionStatus.EXPIRED


# 9. cancellation ---------------------------------------------------------

def test_cancel_running_motion() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock, auto_complete=False)
    req = make_walk(clock)
    agent.submit(req)
    result = agent.cancel(req.request_id)
    assert result.status is ActionStatus.CANCELLED
    assert agent.status(req.request_id) is ActionStatus.CANCELLED
    assert agent.running_motion_id is None


def test_cancel_waiting_motion() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock, auto_complete=False, queue_capacity=2)
    first = make_walk(clock)
    second = make_walk(clock)
    agent.submit(first)
    agent.submit(second)
    result = agent.cancel(second.request_id)
    assert result.status is ActionStatus.CANCELLED
    assert agent.waiting_count == 0


def test_cancel_unknown_request_explicit_result() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock)
    result = agent.cancel(str(uuid4()))
    assert result.status is ActionStatus.REJECTED
    assert result.error_category is ErrorCategory.UNKNOWN_REQUEST


# 10. resource conflict (queueing disabled) --------------------------------

def test_resource_conflict_when_queueing_disabled() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock, auto_complete=False, queue_capacity=0)
    first = make_walk(clock)
    second = make_walk(clock)
    agent.submit(first)
    result = agent.submit(second)
    assert result.status is ActionStatus.REJECTED
    assert result.error_category is ErrorCategory.RESOURCE_CONFLICT


# 12. bounded queue -------------------------------------------------------

def test_bounded_queue_accepts_then_rejects() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock, auto_complete=False, queue_capacity=1)
    first = make_walk(clock)
    second = make_walk(clock)
    third = make_walk(clock)

    agent.submit(first)                      # running
    queued = agent.submit(second)            # waiting
    assert queued.status is ActionStatus.ACCEPTED
    assert agent.waiting_count == 1

    overflow = agent.submit(third)           # queue full
    assert overflow.status is ActionStatus.REJECTED
    assert overflow.error_category is ErrorCategory.QUEUE_FULL


def test_queued_motion_promotes_on_completion() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock, auto_complete=False, queue_capacity=2)
    first = make_walk(clock)
    second = make_walk(clock)
    agent.submit(first)
    agent.submit(second)

    agent.complete(first.request_id)
    assert agent.status(second.request_id) is ActionStatus.RUNNING
    assert agent.running_motion_id == second.request_id


# 11. target unavailable --------------------------------------------------

def test_target_unavailable_rejects_all() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock, target_available=False)
    req = make_walk(clock)
    result = agent.submit(req)
    assert result.status is ActionStatus.REJECTED
    assert result.error_category is ErrorCategory.TARGET_UNAVAILABLE


# schema version rejection via submit ------------------------------------

def test_submit_schema_incompatible_dict_rejected() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock)
    req = make_walk(clock)
    data = request_to_dict(req)
    data["schema_version"] = "9.9"
    result = agent.submit(data)
    assert result.status is ActionStatus.REJECTED
    assert result.error_category is ErrorCategory.SCHEMA_INCOMPATIBLE


def test_submit_invalid_parameters_dict_rejected() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock)
    req = make_walk(clock)
    data = request_to_dict(req)
    data["parameters"] = {"distance_m": 99.0, "speed": 0.2}
    result = agent.submit(data)
    assert result.status is ActionStatus.REJECTED
    assert result.error_category is ErrorCategory.INVALID_PARAMETERS


# failure ----------------------------------------------------------------

def test_injected_failure() -> None:
    clock = FakeClock()
    agent = FakeNAOExecutionAgent(clock=clock, auto_complete=False)
    req = make_walk(clock)
    agent.submit(req)
    result = agent.fail(req.request_id, category=ErrorCategory.INTERNAL, reason="boom")
    assert result.status is ActionStatus.FAILED
    assert result.error_category is ErrorCategory.INTERNAL
