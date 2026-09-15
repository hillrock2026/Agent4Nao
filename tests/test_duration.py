"""Duration field on terminal operation log events."""

import json
import logging
import threading

from agent4nao.config import Agent4NAOConfig, ConversationLimits, OllamaConfig
from agent4nao.conversation import ConversationSession, TurnStatus
from agent4nao.model.fake import FakeModelProvider


def _make_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def _capture_events(logger: logging.Logger) -> list:
    events: list = []
    handler = logging.Handler()
    handler.emit = lambda record: events.append(json.loads(record.getMessage()))
    logger.addHandler(handler)
    return events


def _terminal(events) -> list:
    return [e for e in events if e.get("event") == "turn.end"]


def test_success_terminal_event_has_duration() -> None:
    logger = _make_logger("test.duration.success")
    events = _capture_events(logger)
    session = ConversationSession(FakeModelProvider(), logger=logger)
    result = session.send("hi")
    assert result.ok

    terminal = _terminal(events)
    assert terminal
    for event in terminal:
        assert "duration" in event
        assert isinstance(event["duration"], (int, float))
        assert event["duration"] >= 0
        assert event["request_id"]
        assert event["session_id"]


def test_timeout_terminal_event_has_duration() -> None:
    logger = _make_logger("test.duration.timeout")
    events = _capture_events(logger)
    config = Agent4NAOConfig(
        ollama=OllamaConfig(generation_timeout_seconds=0.2),
        limits=ConversationLimits(),
    )
    session = ConversationSession(
        FakeModelProvider(delay_seconds=5.0), config, logger=logger)
    result = session.send("hi")
    assert result.status is TurnStatus.TIMEOUT

    terminal = _terminal(events)
    assert terminal
    assert terminal[-1]["status"] == "timeout"
    assert terminal[-1]["duration"] >= 0


def test_cancellation_terminal_event_has_duration() -> None:
    logger = _make_logger("test.duration.cancel")
    events = _capture_events(logger)
    started = threading.Event()
    provider = FakeModelProvider(delay_seconds=10.0, started_event=started)
    session = ConversationSession(provider, logger=logger)

    outcome: dict = {}
    thread = threading.Thread(
        target=lambda: outcome.setdefault("result", session.send("slow")))
    thread.start()
    assert started.wait(timeout=2.0)

    session.cancel()
    thread.join(timeout=2.0)

    assert outcome["result"].status is TurnStatus.CANCELLED
    terminal = _terminal(events)
    assert terminal
    assert terminal[-1]["status"] == "cancelled"
    assert terminal[-1]["duration"] >= 0


def test_provider_unavailable_terminal_event_has_duration() -> None:
    logger = _make_logger("test.duration.unavailable")
    events = _capture_events(logger)
    session = ConversationSession(FakeModelProvider(fail=True), logger=logger)
    result = session.send("hi")
    assert result.status is TurnStatus.PROVIDER_UNAVAILABLE

    terminal = _terminal(events)
    assert terminal
    assert terminal[-1]["status"] == "provider_unavailable"
    assert terminal[-1]["duration"] >= 0


def test_terminal_event_does_not_include_message_content() -> None:
    logger = _make_logger("test.duration.nocontent")
    messages: list = []
    handler = logging.Handler()
    handler.emit = lambda record: messages.append(record.getMessage())
    logger.addHandler(handler)

    session = ConversationSession(FakeModelProvider(), logger=logger)
    session.send("super secret user message")

    assert all("super secret user message" not in m for m in messages)


def test_logging_failure_does_not_change_result() -> None:
    class ExplodingLogger:
        def log(self, *args, **kwargs):
            raise RuntimeError("logging exploded")

    session = ConversationSession(FakeModelProvider(), logger=ExplodingLogger())
    result = session.send("hi")
    assert result.ok
    assert result.message
