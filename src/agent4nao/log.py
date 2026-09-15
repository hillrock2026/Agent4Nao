"""Structured logging with secret redaction.

Messages are emitted as JSON event lines and passed through :func:`redact`
so that token-like and credential-like values are masked. By default the
conversation layer does not include message content in log events at all;
content logging is an explicit opt-in (``AGENT4NAO_LOG_CONTENT``).
"""

from __future__ import annotations

import json
import logging
import re

_TOKEN_RE = re.compile(r"(?i)\b(sk-[a-zA-Z0-9_-]{6,})\b")
_CRED_RE = re.compile(
    r"(?i)(\b(?:bearer|token|api[_-]?key|secret|password|authorization)\b\s*[:=]\s*)(\S+)"
)


def redact(text: str) -> str:
    """Mask token-like and credential-like substrings in *text*."""
    out = _CRED_RE.sub(r"\1[REDACTED]", text)
    out = _TOKEN_RE.sub("[REDACTED]", out)
    return out


def configure_logging(level: str = "INFO") -> None:
    logger = logging.getLogger("agent4nao")
    logger.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level.upper())
    logger.propagate = False


def get_logger(name: str = "agent4nao") -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, event: dict, level: int = logging.INFO) -> None:
    text = json.dumps(event, ensure_ascii=False, default=str)
    logger.log(level, redact(text))
