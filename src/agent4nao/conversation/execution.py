"""Conversation -> simulated action integration (Phase 2 Step 5).

:class:`ActionSession` composes the Phase 1 :class:`ConversationSession` with an
optional :class:`~agent4nao.execution.FakeNAOExecutionAgent` without modifying
the conversation session. Pure text conversation behaves exactly as before, and
no action is ever executed implicitly: a model output is only turned into a
typed action through an explicit :meth:`ActionSession.authorize` call.

The outcome distinguishes, for each turn:

- assistant text (always present on a successful text turn);
- proposed action (parsed strictly from the assistant text, or ``None``);
- authorized action (only after explicit authorization);
- fake execution result;
- observation (when the result carries one);
- rejection/failure explanation (``result.error_category`` / ``result.reason``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
from uuid import uuid4

from agent4nao.action import (
    ActionError,
    ActionResult,
    ActionRequest,
    ActionStatus,
    ErrorCategory,
    ProposedAction,
    authorize as authorize_action,
    build_request_from_authorized,
    parse_proposal,
)
from agent4nao.config.config import Agent4NAOConfig
from agent4nao.conversation.session import ConversationSession, TurnStatus
from agent4nao.execution.clock import Clock
from agent4nao.model.provider import ModelProvider


@dataclass(frozen=True)
class ActionTurn:
    """The typed outcome of one conversation turn plus optional action state."""

    status: TurnStatus
    assistant_text: str = ""
    detail: str = ""
    turn_id: str = ""
    proposal: Optional[ProposedAction] = None
    action: Optional[ActionRequest] = None
    result: Optional[ActionResult] = None

    @property
    def ok(self) -> bool:
        return self.status is TurnStatus.OK

    @property
    def observation(self) -> Optional[object]:
        return self.result.observation if self.result is not None else None

    @property
    def executed(self) -> bool:
        return self.action is not None

    @property
    def rejection(self) -> str:
        if self.result is not None and self.result.error_category is not ErrorCategory.NONE:
            return f"{self.result.error_category.value}: {self.result.reason}"
        return self.detail


def _rejected(request_id: str, category: ErrorCategory, reason: str, clock: Clock) -> ActionResult:
    now = clock.now()
    return ActionResult(
        request_id=request_id,
        status=ActionStatus.REJECTED,
        error_category=category,
        reason=reason,
        started_at=now,
        completed_at=now,
        duration_seconds=0.0,
    )


class ActionSession:
    """Compose text conversation with an optional simulated execution target."""

    def __init__(
        self,
        provider: ModelProvider,
        config: Optional[Agent4NAOConfig] = None,
        *,
        execution_agent=None,
        clock: Optional[Clock] = None,
        logger=None,
    ) -> None:
        self._conversation = ConversationSession(provider, config, logger=logger)
        self._agent = execution_agent
        self._clock = clock if clock is not None else Clock()

    # -- delegation -----------------------------------------------------

    @property
    def session_id(self) -> str:
        return self._conversation.session_id

    @property
    def closed(self) -> bool:
        return self._conversation.closed

    def history(self) -> List:
        return self._conversation.history()

    def clear(self) -> None:
        self._conversation.clear()

    def close(self) -> None:
        self._conversation.close()

    # -- conversation + proposal ---------------------------------------

    def send(self, text: str) -> ActionTurn:
        """Run one text turn and parse a proposal (never execute it)."""
        turn = self._conversation.send(text)
        turn_id = str(uuid4())
        if not turn.ok:
            return ActionTurn(status=turn.status, detail=turn.detail, turn_id=turn_id)
        proposal = parse_proposal(turn.message)
        return ActionTurn(
            status=turn.status,
            assistant_text=turn.message,
            turn_id=turn_id,
            proposal=proposal,
        )

    # -- explicit authorization ----------------------------------------

    def authorize(self, proposal: ProposedAction, *, turn_id: Optional[str] = None) -> ActionTurn:
        """Explicitly authorize a proposal into a typed, executed action.

        When no execution agent is configured, the typed action is still built
        but the result is an explicit ``target unavailable`` rejection (no fake
        success and no hardware access).
        """
        turn_id = turn_id or str(uuid4())
        if not isinstance(proposal, ProposedAction):
            return ActionTurn(
                status=TurnStatus.OK,
                turn_id=turn_id,
                detail="authorize requires a ProposedAction",
                result=_rejected(
                    turn_id, ErrorCategory.INVALID_PARAMETERS,
                    "authorize requires a ProposedAction", self._clock),
            )
        try:
            authorized = authorize_action(proposal, clock=self._clock)
        except ActionError as exc:
            return ActionTurn(
                status=TurnStatus.OK,
                turn_id=turn_id,
                proposal=proposal,
                detail=str(exc),
                result=_rejected(
                    turn_id, ErrorCategory.INVALID_PARAMETERS, str(exc), self._clock),
            )
        request = build_request_from_authorized(
            authorized, session_id=self.session_id, turn_id=turn_id, clock=self._clock)
        if self._agent is None:
            result = _rejected(
                request.request_id, ErrorCategory.TARGET_UNAVAILABLE,
                "no execution target configured", self._clock)
            return ActionTurn(
                status=TurnStatus.OK,
                turn_id=turn_id,
                proposal=proposal,
                action=request,
                result=result,
            )
        result = self._agent.submit(request)
        return ActionTurn(
            status=TurnStatus.OK,
            turn_id=turn_id,
            proposal=proposal,
            action=request,
            result=result,
        )
