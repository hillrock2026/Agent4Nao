"""Deterministic fake model provider for tests.

Supports fixed responses, scripted sequences, injected delay (timeout),
injected provider failure, cancellation, and request capture. Requires no
Ollama, no network, and no GPU.
"""

from __future__ import annotations

import threading
import time
from typing import List, Optional, Sequence

from agent4nao.model.provider import ModelProvider
from agent4nao.model.request import ModelRequest
from agent4nao.model.result import ModelErrorCategory, ModelResult


class FakeModelProvider(ModelProvider):
    name = "fake"

    def __init__(
        self,
        *,
        fixed_response: str = "ok",
        responses: Optional[Sequence[str]] = None,
        delay_seconds: float = 0.0,
        fail: bool = False,
        fail_category: ModelErrorCategory = ModelErrorCategory.PROVIDER_UNAVAILABLE,
        fail_diagnostic: str = "fake provider unavailable",
        cancel_event: Optional[threading.Event] = None,
        started_event: Optional[threading.Event] = None,
    ) -> None:
        self._fixed_response = fixed_response
        self._script = list(responses) if responses is not None else None
        self._delay_seconds = delay_seconds
        self._fail = fail
        self._fail_category = fail_category
        self._fail_diagnostic = fail_diagnostic
        self._cancel_event = (
            cancel_event if cancel_event is not None else threading.Event())
        self._started_event = started_event

        self.requests: List[ModelRequest] = []

    def generate(self, request: ModelRequest) -> ModelResult:
        self.requests.append(request)
        if self._started_event is not None:
            self._started_event.set()

        if self._delay_seconds > 0 and self._wait(self._delay_seconds):
            return ModelResult.failure(
                "cancelled", ModelErrorCategory.CANCELLED, request.request_id)

        if self._fail:
            return ModelResult.failure(
                self._fail_diagnostic, self._fail_category, request.request_id)

        return ModelResult.success(self._next_content(), request.request_id)

    def cancel(self, request_id: str = "") -> None:
        self._cancel_event.set()

    def _next_content(self) -> str:
        if self._script is None:
            return self._fixed_response
        if self._script:
            return self._script.pop(0)
        return self._fixed_response

    def _wait(self, seconds: float) -> bool:
        """Interruptible sleep; returns True if cancelled before the deadline."""
        deadline = time.monotonic() + seconds
        while True:
            if self._cancel_event.is_set():
                return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            time.sleep(min(remaining, 0.01))
