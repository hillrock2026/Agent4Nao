"""In-process, deterministic Fake NAO Execution Agent.

Simulates the future NAO Execution Agent's safety and lifecycle semantics
without any hardware, transport, ROS 2, NAOqi, or Agent-Kernel dependency. It
handles acceptance, execution, completion, rejection, expiry, cancellation,
failure, duplicate/idempotent submission, resource conflict, an unavailable
target, and a bounded motion queue.

Safety invariant enforced: ``Stop`` (EMERGENCY) always preempts ``Stand`` and
``Walk`` motion requests; a preempted running or queued motion request produces
an explicit ``cancelled`` result.

This is a *simulation*, not a claim of real NAO safety.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, List, Optional, Union

from agent4nao.action.errors import SchemaValidationError, SchemaVersionError
from agent4nao.action.request import ActionRequest
from agent4nao.action.result import ActionResult, Observation
from agent4nao.action.schema import (
    DEFAULT_QUEUE_CAPACITY,
    SCHEMA_VERSION,
    ActionStatus,
    Capability,
    ErrorCategory,
)
from agent4nao.action.validation import request_from_dict
from agent4nao.execution.clock import Clock

_OBSERVE_FULL = {"battery_pct": 87, "posture": "standing", "fall_state": "none"}
_OBSERVE_ORDER = ("battery_pct", "posture", "fall_state")

_MOTION_CAPABILITIES = frozenset({Capability.STAND, Capability.WALK})


@dataclass
class _Record:
    request: ActionRequest
    status: ActionStatus
    result: Optional[ActionResult]
    started_at: float = 0.0
    started_mono: float = 0.0


class FakeNAOExecutionAgent:
    """Deterministic in-process action execution simulation."""

    def __init__(
        self,
        *,
        target_available: bool = True,
        queue_capacity: int = DEFAULT_QUEUE_CAPACITY,
        clock: Optional[Clock] = None,
        auto_complete: bool = True,
        logger=None,
    ) -> None:
        if queue_capacity < 0:
            raise ValueError("queue_capacity must be >= 0")
        self._target_available = target_available
        self._queue_capacity = queue_capacity
        self._clock = clock if clock is not None else Clock()
        self._auto_complete = auto_complete
        self._logger = logger

        self._records: Dict[str, _Record] = {}
        self._idempotency: Dict[tuple, str] = {}
        self._running_motion: Optional[str] = None
        self._waiting: List[str] = []
        self.events: List[dict] = []

    # -- queries --------------------------------------------------------

    def result_for(self, request_id: str) -> Optional[ActionResult]:
        rec = self._records.get(request_id)
        return rec.result if rec is not None else None

    def status(self, request_id: str) -> Optional[ActionStatus]:
        rec = self._records.get(request_id)
        return rec.status if rec is not None else None

    @property
    def waiting_count(self) -> int:
        return len(self._waiting)

    @property
    def running_motion_id(self) -> Optional[str]:
        return self._running_motion

    # -- public mutations ----------------------------------------------

    def submit(self, request: Union[ActionRequest, dict]) -> ActionResult:
        """Submit an action request and return its (possibly terminal) result.

        A raw dict is parsed with strict validation; schema and parameter
        violations produce explicit ``rejected`` results rather than raising.
        """
        if isinstance(request, dict):
            raw_id = request.get("request_id", "")
            request_id = raw_id if isinstance(raw_id, str) else ""
            try:
                request = request_from_dict(request)
            except SchemaVersionError as exc:
                return self._rejected_result(
                    request_id, ErrorCategory.SCHEMA_INCOMPATIBLE, str(exc))
            except SchemaValidationError as exc:
                return self._rejected_result(
                    request_id, ErrorCategory.INVALID_PARAMETERS, str(exc))

        duplicate = self._check_duplicate(request)
        if duplicate is not None:
            return duplicate

        if not self._target_available:
            return self._immediate(
                request, ActionStatus.REJECTED, ErrorCategory.TARGET_UNAVAILABLE,
                "target unavailable")

        if self._is_stale(request):
            return self._immediate(
                request, ActionStatus.EXPIRED, ErrorCategory.STALE,
                "request expired before execution")

        if request.capability is Capability.OBSERVE:
            observation = self._observe(request)
            return self._immediate(
                request, ActionStatus.COMPLETED, ErrorCategory.NONE, "",
                observation=observation)

        if request.capability is Capability.STOP:
            preempted = self._preempt()
            return self._immediate(
                request, ActionStatus.COMPLETED, ErrorCategory.NONE, "",
                payload={"stopped": True, "preempted": preempted})

        return self._admit_motion(request)

    def complete(self, request_id: str) -> ActionResult:
        """Complete a running motion request; promotes the next queued motion."""
        rec = self._records.get(request_id)
        if rec is None:
            return self._rejected_result(
                request_id, ErrorCategory.UNKNOWN_REQUEST, "unknown request")
        if rec.status is not ActionStatus.RUNNING:
            return self._rejected_result(
                request_id, ErrorCategory.INVALID_PARAMETERS, "request is not running")
        return self._finish(rec.request, payload=self._motion_payload(rec.request))

    def fail(
        self,
        request_id: str,
        category: ErrorCategory = ErrorCategory.INTERNAL,
        reason: str = "injected failure",
    ) -> ActionResult:
        """Fail a running motion request; promotes the next queued motion."""
        rec = self._records.get(request_id)
        if rec is None:
            return self._rejected_result(
                request_id, ErrorCategory.UNKNOWN_REQUEST, "unknown request")
        if rec.status is not ActionStatus.RUNNING:
            return self._rejected_result(
                request_id, ErrorCategory.INVALID_PARAMETERS, "request is not running")
        return self._finish(
            rec.request, status=ActionStatus.FAILED, category=category, reason=reason)

    def cancel(self, request_id: str) -> ActionResult:
        """Cancel a running or queued motion request; terminal requests are a no-op."""
        rec = self._records.get(request_id)
        if rec is None:
            return self._rejected_result(
                request_id, ErrorCategory.UNKNOWN_REQUEST, "unknown request")
        if rec.status is ActionStatus.RUNNING:
            return self._finish(
                rec.request, status=ActionStatus.CANCELLED,
                category=ErrorCategory.CANCELLED, reason="cancelled")
        if rec.status is ActionStatus.ACCEPTED and request_id in self._waiting:
            self._waiting.remove(request_id)
            return self._update(
                rec, ActionStatus.CANCELLED,
                self._no_duration_result(
                    rec.request, ActionStatus.CANCELLED, ErrorCategory.CANCELLED,
                    "cancelled while waiting"))
        return rec.result

    # -- internals ------------------------------------------------------

    def _check_duplicate(self, request: ActionRequest) -> Optional[ActionResult]:
        rec = self._records.get(request.request_id)
        if rec is not None:
            if rec.request == request:
                return self._duplicate(rec)
            return self._rejected_result(
                request.request_id, ErrorCategory.IDEMPOTENCY_CONFLICT,
                "request_id reused with different content")
        key = (request.session_id, request.idempotency_key)
        if key in self._idempotency:
            return self._rejected_result(
                request.request_id, ErrorCategory.IDEMPOTENCY_CONFLICT,
                "idempotency_key reused with a different request")
        return None

    def _duplicate(self, rec: _Record) -> ActionResult:
        cached = rec.result
        if cached is None:
            cached = ActionResult(request_id=rec.request.request_id, status=rec.status)
        return replace(
            cached,
            error_category=ErrorCategory.DUPLICATE,
            reason="duplicate request; returning cached result",
        )

    def _is_stale(self, request: ActionRequest) -> bool:
        return self._clock.now() > request.created_at + request.ttl_seconds

    def _admit_motion(self, request: ActionRequest) -> ActionResult:
        if self._running_motion is None and not self._waiting:
            return self._start_running(request)

        if len(self._waiting) >= self._queue_capacity:
            if self._queue_capacity == 0:
                return self._immediate(
                    request, ActionStatus.REJECTED, ErrorCategory.RESOURCE_CONFLICT,
                    "motion resource busy and queueing disabled")
            return self._immediate(
                request, ActionStatus.REJECTED, ErrorCategory.QUEUE_FULL,
                "motion queue is full")

        self._waiting.append(request.request_id)
        rec = self._record_of(request)
        return self._update(
            rec, ActionStatus.ACCEPTED,
            ActionResult(request_id=request.request_id, status=ActionStatus.ACCEPTED))

    def _start_running(self, request: ActionRequest) -> ActionResult:
        self._running_motion = request.request_id
        rec = self._record_of(request)
        rec.started_at = self._clock.now()
        rec.started_mono = self._clock.monotonic()
        result = ActionResult(
            request_id=request.request_id,
            status=ActionStatus.RUNNING,
            started_at=rec.started_at,
        )
        self._update(rec, ActionStatus.RUNNING, result)
        if self._auto_complete:
            return self._finish(request, payload=self._motion_payload(request))
        return result

    def _finish(
        self,
        request: ActionRequest,
        *,
        status: ActionStatus = ActionStatus.COMPLETED,
        category: ErrorCategory = ErrorCategory.NONE,
        reason: str = "",
        payload: Optional[Dict[str, Any]] = None,
        observation: Optional[Observation] = None,
        promote: bool = True,
    ) -> ActionResult:
        rec = self._records[request.request_id]
        completed_at = self._clock.now()
        duration = round(max(0.0, self._clock.monotonic() - rec.started_mono), 6)
        result = ActionResult(
            request_id=request.request_id,
            status=status,
            error_category=category,
            reason=reason,
            started_at=rec.started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            payload=payload,
            observation=observation,
        )
        self._update(rec, status, result)
        if promote and request.capability in _MOTION_CAPABILITIES:
            self._running_motion = None
            self._promote_next()
        return result

    def _promote_next(self) -> None:
        while self._waiting:
            request_id = self._waiting.pop(0)
            rec = self._records[request_id]
            if self._is_stale(rec.request):
                self._update(
                    rec, ActionStatus.EXPIRED,
                    self._no_duration_result(
                        rec.request, ActionStatus.EXPIRED, ErrorCategory.STALE,
                        "request expired while waiting"))
                continue
            self._start_running(rec.request)
            break

    def _preempt(self) -> List[str]:
        preempted: List[str] = []
        running_id = self._running_motion
        if running_id is not None:
            self._running_motion = None
            rec = self._records[running_id]
            preempted.append(running_id)
            self._finish(
                rec.request,
                status=ActionStatus.CANCELLED,
                category=ErrorCategory.CANCELLED,
                reason="preempted by emergency stop",
                promote=False,
            )
        for request_id in list(self._waiting):
            self._waiting.remove(request_id)
            rec = self._records[request_id]
            preempted.append(request_id)
            self._update(
                rec, ActionStatus.CANCELLED,
                self._no_duration_result(
                    rec.request, ActionStatus.CANCELLED, ErrorCategory.CANCELLED,
                    "preempted by emergency stop"))
        return preempted

    def _observe(self, request: ActionRequest) -> Observation:
        params = request.parameters
        if params.fields is None or len(params.fields) == 0:
            summary = dict(_OBSERVE_FULL)
        else:
            summary = {f: _OBSERVE_FULL[f] for f in _OBSERVE_ORDER if f in params.fields}
        return Observation(
            request_id=request.request_id,
            observed_at=self._clock.now(),
            capability=Capability.OBSERVE,
            summary=summary,
        )

    def _motion_payload(self, request: ActionRequest) -> Dict[str, Any]:
        if request.capability is Capability.WALK:
            params = request.parameters
            return {"distance_m": params.distance_m, "speed": params.speed}
        return {}

    # -- record/result helpers -----------------------------------------

    def _record_of(self, request: ActionRequest) -> _Record:
        rec = self._records.get(request.request_id)
        if rec is None:
            rec = _Record(request=request, status=ActionStatus.ACCEPTED, result=None)
            self._records[request.request_id] = rec
            self._idempotency[(request.session_id, request.idempotency_key)] = (
                request.request_id)
        return rec

    def _update(self, rec: _Record, status: ActionStatus, result: ActionResult) -> ActionResult:
        rec.status = status
        rec.result = result
        self._emit(rec.request, result)
        return result

    def _immediate(
        self,
        request: ActionRequest,
        status: ActionStatus,
        category: ErrorCategory,
        reason: str,
        *,
        payload: Optional[Dict[str, Any]] = None,
        observation: Optional[Observation] = None,
    ) -> ActionResult:
        result = self._no_duration_result(
            request, status, category, reason, payload=payload, observation=observation)
        rec = self._record_of(request)
        return self._update(rec, status, result)

    def _no_duration_result(
        self,
        request: ActionRequest,
        status: ActionStatus,
        category: ErrorCategory,
        reason: str,
        *,
        payload: Optional[Dict[str, Any]] = None,
        observation: Optional[Observation] = None,
    ) -> ActionResult:
        now = self._clock.now()
        return ActionResult(
            request_id=request.request_id,
            status=status,
            error_category=category,
            reason=reason,
            started_at=now,
            completed_at=now,
            duration_seconds=0.0,
            payload=payload,
            observation=observation,
        )

    def _rejected_result(
        self, request_id: str, category: ErrorCategory, reason: str
    ) -> ActionResult:
        now = self._clock.now()
        return ActionResult(
            request_id=request_id,
            status=ActionStatus.REJECTED,
            error_category=category,
            reason=reason,
            started_at=now,
            completed_at=now,
            duration_seconds=0.0,
        )

    def _emit(self, request: ActionRequest, result: ActionResult) -> None:
        event = {
            "event": "execution.result",
            "request_id": result.request_id,
            "session_id": request.session_id,
            "capability": request.capability.value,
            "status": result.status.value,
            "error_category": result.error_category.value,
            "duration_seconds": result.duration_seconds,
        }
        self.events.append(event)
        if self._logger is not None:
            try:
                from agent4nao.log import log_event

                log_event(self._logger, event)
            except Exception:
                pass
