"""Timeout and cancellation behavior."""

import threading
import time

from agent4nao.config import Agent4NAOConfig, ConversationLimits, OllamaConfig
from agent4nao.conversation import ConversationSession, TurnStatus
from agent4nao.model.fake import FakeModelProvider


def make_config(generation_timeout: float = 60.0) -> Agent4NAOConfig:
    return Agent4NAOConfig(
        ollama=OllamaConfig(generation_timeout_seconds=generation_timeout),
        limits=ConversationLimits(),
    )


def test_timeout() -> None:
    provider = FakeModelProvider(delay_seconds=5.0)
    session = ConversationSession(provider, make_config(generation_timeout=0.2))
    start = time.monotonic()
    result = session.send("hi")
    elapsed = time.monotonic() - start
    assert result.status is TurnStatus.TIMEOUT
    assert elapsed < 2.0


def test_cancellation() -> None:
    started = threading.Event()
    provider = FakeModelProvider(delay_seconds=10.0, started_event=started)
    session = ConversationSession(provider, make_config(generation_timeout=60.0))

    outcome: dict = {}

    def run() -> None:
        outcome["result"] = session.send("slow")

    thread = threading.Thread(target=run)
    thread.start()
    assert started.wait(timeout=2.0)

    session.cancel()
    thread.join(timeout=2.0)

    assert not thread.is_alive()
    assert outcome["result"].status is TurnStatus.CANCELLED


def test_concurrent_request_rejected() -> None:
    started = threading.Event()
    provider = FakeModelProvider(delay_seconds=0.5, started_event=started)
    session = ConversationSession(provider, make_config())

    first: dict = {}

    def run() -> None:
        first["result"] = session.send("first")

    thread = threading.Thread(target=run)
    thread.start()
    assert started.wait(timeout=2.0)

    second = session.send("second")
    assert second.status is TurnStatus.CONCURRENT_REQUEST

    thread.join(timeout=2.0)
    assert first["result"].ok


def test_provider_failure_propagates() -> None:
    provider = FakeModelProvider(fail=True)
    session = ConversationSession(provider)
    result = session.send("hi")
    assert result.status is TurnStatus.PROVIDER_UNAVAILABLE
    assert result.message == ""
