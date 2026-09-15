"""Logging redaction and no-content-leak guarantees."""

import logging

from agent4nao.log import log_event, redact
from agent4nao.model.fake import FakeModelProvider
from agent4nao.conversation import ConversationSession


def test_redact_masks_credentials() -> None:
    assert "sk-abcdef123456" not in redact("token=sk-abcdef123456")
    assert "[REDACTED]" in redact("token=sk-abcdef123456")


def test_redact_masks_key_value_credentials() -> None:
    out = redact("api_key=supersecretvalue")
    assert "supersecretvalue" not in out
    assert "[REDACTED]" in out


def test_redact_leaves_plain_text() -> None:
    text = "the robot is not connected"
    assert redact(text) == text


def _capture(logger: logging.Logger):
    records: list = []
    handler = logging.Handler()
    handler.emit = lambda record: records.append(record.getMessage())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return records


def test_session_does_not_log_content_by_default() -> None:
    logger = logging.getLogger("test.no-content")
    logger.handlers.clear()
    records = _capture(logger)

    session = ConversationSession(FakeModelProvider(), logger=logger)
    session.send("my secret user message")

    combined = "\n".join(records)
    assert "my secret user message" not in combined


def test_log_event_redacts_inline_secrets() -> None:
    logger = logging.getLogger("test.redact")
    logger.handlers.clear()
    records = _capture(logger)

    log_event(logger, {"event": "x", "token": "sk-abcdef123456"})

    assert "[REDACTED]" in records[0]
    assert "sk-abcdef123456" not in records[0]
