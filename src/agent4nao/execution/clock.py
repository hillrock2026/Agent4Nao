"""Injectable clocks for the Fake NAO Execution Agent.

The fake agent uses two clocks with distinct meanings:

- ``now()``: wall-clock UTC epoch seconds for ``created_at``/``started_at``/
  ``completed_at`` and for TTL/staleness comparison;
- ``monotonic()``: monotonic seconds for ``duration_seconds``.

:class:`FakeClock` advances both together so tests can deterministically drive
TTL expiry and duration without sleeping.
"""

from __future__ import annotations

import time


class Clock:
    """Real clock (wall-clock epoch + monotonic)."""

    def now(self) -> float:
        return time.time()

    def monotonic(self) -> float:
        return time.monotonic()


class FakeClock(Clock):
    """Deterministic clock advanced manually in tests."""

    def __init__(self, start: float = 1_700_000_000.0) -> None:
        self._wall = start
        self._mono = 0.0

    def now(self) -> float:
        return self._wall

    def monotonic(self) -> float:
        return self._mono

    def advance(self, seconds: float) -> None:
        self._wall += seconds
        self._mono += seconds
