"""Typed conversation session.

A session owns a bounded message history and drives one model provider through
a provider-neutral boundary. It defines explicit behavior for empty/oversized
input, closed sessions, concurrent requests, timeouts, provider failures, and
cancellation.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from agent4nao.config.config import Agent4NAOConfig, ConversationLimits
from agent4nao.model.messages import (
    Message,
    ROLE_SYSTEM,
    assistant_message,
    system_message,
    user_message,
)
from agent4nao.model.provider import ModelProvider
from agent4nao.model.request import ModelRequest
from agent4nao.model.result import ModelErrorCategory, ModelResult, ModelStatus
from agent4nao.conversation import errors


class TurnStatus(str, Enum):
    OK = "ok"
    EMPTY_INPUT = "empty_input"
    INPUT_TOO_LARGE = "input_too_large"
    SESSION_CLOSED = "session_closed"
    CONCURRENT_REQUEST = "concurrent_request"
    TIMEOUT = "timeout"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PROTOCOL_ERROR = "protocol_error"
    INVALID_RESPONSE = "invalid_response"
    CANCELLED = "cancelled"
    MODEL_FAILURE = "model_failure"


@dataclass(frozen=True)
class TurnResult:
    """The typed outcome of one ``send`` call."""

    status: TurnStatus
    message: str = ""
    detail: str = ""
    request_id: str = ""
    truncated: bool = False

    @property
    def ok(self) -> bool:
        return self.status is TurnStatus.OK

    @classmethod
    def failure(cls, status: TurnStatus, detail: str, request_id: str = "") -> "TurnResult":
        return cls(status=status, detail=detail, request_id=request_id)


def _status_for_error(error: errors.ConversationError) -> TurnStatus:
    if isinstance(error, errors.EmptyInputError):
        return TurnStatus.EMPTY_INPUT
    if isinstance(error, errors.InputTooLargeError):
        return TurnStatus.INPUT_TOO_LARGE
    if isinstance(error, errors.SessionClosedError):
        return TurnStatus.SESSION_CLOSED
    if isinstance(error, errors.ConcurrentRequestError):
        return TurnStatus.CONCURRENT_REQUEST
    if isinstance(error, errors.ModelTimeoutError):
        return TurnStatus.TIMEOUT
    if isinstance(error, errors.ModelUnavailableError):
        return TurnStatus.PROVIDER_UNAVAILABLE
    if isinstance(error, errors.ProviderProtocolError):
        return TurnStatus.PROTOCOL_ERROR
    if isinstance(error, errors.InvalidModelResponseError):
        return TurnStatus.INVALID_RESPONSE
    if isinstance(error, errors.CancelledError):
        return TurnStatus.CANCELLED
    if isinstance(error, errors.ModelFailureError):
        return TurnStatus.MODEL_FAILURE
    return TurnStatus.MODEL_FAILURE


class ConversationSession:
    def __init__(
        self,
        provider: ModelProvider,
        config: Optional[Agent4NAOConfig] = None,
        *,
        logger=None,
    ) -> None:
        self._config = config if config is not None else Agent4NAOConfig()
        self._provider = provider
        self._logger = logger

        self._session_id = str(uuid4())
        self._messages: List[Message] = []
        self._closed = False
        self._in_flight = False
        self._lock = threading.Lock()
        self._cancel_event = threading.Event()

    # -- properties -----------------------------------------------------

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def closed(self) -> bool:
        with self._lock:
            return self._closed

    @property
    def in_flight(self) -> bool:
        with self._lock:
            return self._in_flight

    # -- lifecycle ------------------------------------------------------

    def history(self) -> List[Message]:
        with self._lock:
            return list(self._messages)

    def clear(self) -> None:
        with self._lock:
            self._messages = []

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._cancel_event.set()
            in_flight = self._in_flight
        if in_flight:
            self._provider.cancel()

    # -- conversation ---------------------------------------------------

    def cancel(self) -> None:
        """Signal cancellation of the in-flight generation (if any)."""
        self._cancel_event.set()
        if self._in_flight:
            self._provider.cancel()

    def send(self, text: str) -> TurnResult:
        limits = self._config.limits

        with self._lock:
            if self._closed:
                return TurnResult.failure(
                    TurnStatus.SESSION_CLOSED, str(errors.SessionClosedError()))
            if self._in_flight:
                return TurnResult.failure(
                    TurnStatus.CONCURRENT_REQUEST,
                    str(errors.ConcurrentRequestError()),
                )
            validation_error = self._validate_input(text, limits)
            if validation_error is not None:
                return TurnResult.failure(
                    _status_for_error(validation_error), str(validation_error))
            self._in_flight = True
            self._cancel_event.clear()

        request_id = str(uuid4())
        request = self._build_request(request_id, text, limits)
        started = time.monotonic()
        self._log("turn.start", request_id=request_id)

        holder = self._submit(request)
        result = self._await(holder, request_id)

        with self._lock:
            self._in_flight = False

        duration = self._elapsed_seconds(started)
        return self._finalize(result, request_id, text, duration)

    # -- internals ------------------------------------------------------

    @staticmethod
    def _validate_input(text: str, limits: ConversationLimits) -> Optional[errors.ConversationError]:
        if text is None or not text.strip():
            return errors.EmptyInputError()
        if len(text) > limits.max_message_chars:
            return errors.InputTooLargeError(len(text), limits.max_message_chars)
        return None

    def _build_request(
        self, request_id: str, text: str, limits: ConversationLimits
    ) -> ModelRequest:
        messages: List[Message] = [system_message(self._config.system_prompt)]
        with self._lock:
            messages.extend(self._messages)
        messages.append(user_message(text))

        # Enforce the approximate context bound by dropping the oldest
        # non-system messages; never truncates a message mid-text.
        total = sum(len(m.content) for m in messages)
        while total > limits.max_context_chars and len(messages) > 2:
            total -= len(messages[1].content)
            messages.pop(1)

        return ModelRequest(
            model=self._config.ollama.model,
            messages=tuple(messages),
            request_id=request_id,
            timeout_seconds=self._config.ollama.generation_timeout_seconds,
        )

    def _submit(self, request: ModelRequest):
        holder: dict = {"result": None, "exc": None, "done": threading.Event()}

        def run() -> None:
            try:
                holder["result"] = self._provider.generate(request)
            except Exception as exc:  # normalize an unexpected provider raise
                holder["exc"] = exc
            finally:
                holder["done"].set()

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return holder

    def _await(self, holder, request_id: str) -> ModelResult:
        # The session-level generation timeout bounds the total wait.
        timeout = self._config.ollama.generation_timeout_seconds
        deadline = time.monotonic() + timeout
        while True:
            if holder["done"].is_set():
                if holder["exc"] is not None:
                    return ModelResult.failure(
                        f"provider raised: {holder['exc']}",
                        ModelErrorCategory.MODEL_FAILURE,
                        request_id,
                    )
                return holder["result"]

            if self._cancel_event.is_set():
                self._provider.cancel(request_id)
                return ModelResult.failure(
                    "cancelled by caller", ModelErrorCategory.CANCELLED, request_id)

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._provider.cancel(request_id)
                return ModelResult.failure(
                    "generation timed out", ModelErrorCategory.TIMEOUT, request_id)

            holder["done"].wait(min(remaining, 0.05))

    @staticmethod
    def _elapsed_seconds(started: float) -> float:
        """Elapsed seconds since *started* (time.monotonic), non-negative.

        Rounded to 6 decimal places (microsecond precision).
        """
        return round(max(0.0, time.monotonic() - started), 6)

    def _finalize(self, result: ModelResult, request_id: str, text: str, duration: float) -> TurnResult:
        limits = self._config.limits

        if result.is_success:
            content = result.payload or ""
            truncated = len(content) > limits.max_response_chars
            if truncated:
                content = content[:limits.max_response_chars]
            self._record_turn(text, content, limits)
            self._log(
                "turn.end",
                request_id=request_id,
                status=TurnStatus.OK.value,
                truncated=truncated,
                duration=duration,
            )
            return TurnResult(
                status=TurnStatus.OK,
                message=content,
                request_id=request_id,
                truncated=truncated,
            )

        turn = self._map_failure(result)
        self._log(
            "turn.end",
            request_id=request_id,
            status=turn.status.value,
            duration=duration,
        )
        return turn

    def _record_turn(
        self, user_text: str, assistant_text: str, limits: ConversationLimits
    ) -> None:
        with self._lock:
            self._messages.append(user_message(user_text))
            self._messages.append(assistant_message(assistant_text))
            if len(self._messages) > limits.max_history_messages:
                del self._messages[: len(self._messages) - limits.max_history_messages]

    @staticmethod
    def _map_failure(result: ModelResult) -> TurnResult:
        if result.is_invalid_result:
            return TurnResult.failure(
                TurnStatus.INVALID_RESPONSE,
                str(errors.InvalidModelResponseError(result.diagnostic)),
                result.request_id,
            )

        category = result.category
        detail = result.diagnostic or "model failure"
        if category is ModelErrorCategory.TIMEOUT:
            error = errors.ModelTimeoutError(detail)
        elif category is ModelErrorCategory.CANCELLED:
            error = errors.CancelledError(detail)
        elif category is ModelErrorCategory.PROVIDER_UNAVAILABLE:
            error = errors.ModelUnavailableError(detail)
        elif category is ModelErrorCategory.PROTOCOL_ERROR:
            error = errors.ProviderProtocolError(detail)
        else:
            error = errors.ModelFailureError(detail)
        return TurnResult.failure(
            _status_for_error(error), str(error), result.request_id)

    def _log(self, event: str, **fields) -> None:
        if self._logger is None:
            return
        try:
            from agent4nao.log import log_event

            payload = {
                "event": event,
                "session_id": self._session_id,
                "provider": self._provider.name,
            }
            payload.update(fields)
            log_event(self._logger, payload)
        except Exception:
            # Logging must never change conversation behavior.
            pass
