"""Configuration defaults, environment overrides, and precedence."""

import pytest

from agent4nao.config import (
    ConversationLimits,
    OllamaConfig,
    DEFAULT_ENDPOINT,
    DEFAULT_MODEL,
    load_config,
)


def test_defaults() -> None:
    cfg = load_config(environ={})
    assert cfg.ollama.model == DEFAULT_MODEL
    assert cfg.ollama.endpoint == DEFAULT_ENDPOINT
    assert cfg.ollama.connect_timeout_seconds == 5.0
    assert cfg.ollama.generation_timeout_seconds == 60.0
    assert cfg.limits.max_message_chars == 4096
    assert cfg.limits.max_history_messages == 20
    assert cfg.log_level == "INFO"
    assert cfg.log_content is False


def test_environment_overrides_defaults() -> None:
    cfg = load_config(environ={
        "AGENT4NAO_MODEL": "qwen2.5:3b",
        "AGENT4NAO_MAX_MESSAGE_CHARS": "100",
        "AGENT4NAO_LOG_CONTENT": "1",
    })
    assert cfg.ollama.model == "qwen2.5:3b"
    assert cfg.limits.max_message_chars == 100
    assert cfg.log_content is True


def test_explicit_overrides_beat_environment() -> None:
    cfg = load_config(
        environ={"AGENT4NAO_MODEL": "env-model"},
        ollama=OllamaConfig(model="explicit-model"),
        limits=ConversationLimits(max_message_chars=50),
    )
    assert cfg.ollama.model == "explicit-model"
    assert cfg.limits.max_message_chars == 50


def test_invalid_environment_value_raises() -> None:
    with pytest.raises(ValueError):
        load_config(environ={"AGENT4NAO_MAX_MESSAGE_CHARS": "not-an-int"})
    with pytest.raises(ValueError):
        load_config(environ={"AGENT4NAO_LOG_CONTENT": "maybe"})


def test_invalid_limits_rejected() -> None:
    with pytest.raises(ValueError):
        ConversationLimits(max_message_chars=0)
    with pytest.raises(ValueError):
        ConversationLimits(max_message_chars=100, max_context_chars=50)
