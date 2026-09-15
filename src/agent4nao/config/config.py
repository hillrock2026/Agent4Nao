"""Agent4NAO configuration.

Configuration is explicit and overridable without code edits. Precedence
(highest wins):

    1. explicit constructor overrides passed to :func:`load_config`
    2. environment variables (``AGENT4NAO_*``)
    3. built-in defaults
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping, Optional

DEFAULT_MODEL = "qwen2.5:7b-instruct-q4_K_M"
DEFAULT_ENDPOINT = "http://127.0.0.1:11434"

DEFAULT_SYSTEM_PROMPT = (
    "You are Agent4NAO, a desktop assistant for a NAO robot. "
    "Be helpful and concise. In this phase you cannot control the robot "
    "and cannot perform any physical action."
)


@dataclass(frozen=True)
class ConversationLimits:
    """Hard bounds applied by the conversation session."""

    max_message_chars: int = 4096
    max_history_messages: int = 20
    max_context_chars: int = 8192
    max_response_chars: int = 8192
    max_concurrent_generations: int = 1

    def __post_init__(self) -> None:
        if self.max_message_chars <= 0:
            raise ValueError("max_message_chars must be positive")
        if self.max_history_messages < 0:
            raise ValueError("max_history_messages must be >= 0")
        if self.max_context_chars <= 0:
            raise ValueError("max_context_chars must be positive")
        if self.max_response_chars <= 0:
            raise ValueError("max_response_chars must be positive")
        if self.max_concurrent_generations < 1:
            raise ValueError("max_concurrent_generations must be >= 1")
        if self.max_message_chars > self.max_context_chars:
            raise ValueError(
                "max_message_chars must not exceed max_context_chars")


@dataclass(frozen=True)
class OllamaConfig:
    endpoint: str = DEFAULT_ENDPOINT
    model: str = DEFAULT_MODEL
    connect_timeout_seconds: float = 5.0
    generation_timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.endpoint:
            raise ValueError("Ollama endpoint must not be empty")
        if not self.model:
            raise ValueError("Ollama model tag must not be empty")
        if self.connect_timeout_seconds <= 0:
            raise ValueError("connect_timeout_seconds must be positive")
        if self.generation_timeout_seconds <= 0:
            raise ValueError("generation_timeout_seconds must be positive")


@dataclass(frozen=True)
class Agent4NAOConfig:
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    limits: ConversationLimits = field(default_factory=ConversationLimits)
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    log_level: str = "INFO"
    log_content: bool = False


def _as_int(value: str, name: str) -> int:
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"{name} must be an integer, got {value!r}") from None


def _as_float(value: str, name: str) -> float:
    try:
        return float(value)
    except ValueError:
        raise ValueError(f"{name} must be a number, got {value!r}") from None


def _as_bool(value: str, name: str) -> bool:
    lowered = value.strip().lower()
    if lowered in ("1", "true", "yes", "on"):
        return True
    if lowered in ("0", "false", "no", "off", ""):
        return False
    raise ValueError(f"{name} must be a boolean, got {value!r}")


def load_config(
    environ: Optional[Mapping[str, str]] = None,
    *,
    ollama: Optional[OllamaConfig] = None,
    limits: Optional[ConversationLimits] = None,
    system_prompt: Optional[str] = None,
    log_level: Optional[str] = None,
    log_content: Optional[bool] = None,
) -> Agent4NAOConfig:
    """Build a configuration from defaults, then environment, then overrides."""
    env = dict(os.environ if environ is None else environ)

    # 1) defaults, then environment variables
    ollama_cfg = OllamaConfig(
        endpoint=env.get("AGENT4NAO_OLLAMA_ENDPOINT", DEFAULT_ENDPOINT),
        model=env.get("AGENT4NAO_MODEL", DEFAULT_MODEL),
        connect_timeout_seconds=(
            _as_float(env["AGENT4NAO_CONNECT_TIMEOUT"], "AGENT4NAO_CONNECT_TIMEOUT")
            if "AGENT4NAO_CONNECT_TIMEOUT" in env else 5.0),
        generation_timeout_seconds=(
            _as_float(env["AGENT4NAO_GENERATION_TIMEOUT"], "AGENT4NAO_GENERATION_TIMEOUT")
            if "AGENT4NAO_GENERATION_TIMEOUT" in env else 60.0),
    )

    limits_cfg = ConversationLimits(
        max_message_chars=(
            _as_int(env["AGENT4NAO_MAX_MESSAGE_CHARS"], "AGENT4NAO_MAX_MESSAGE_CHARS")
            if "AGENT4NAO_MAX_MESSAGE_CHARS" in env else 4096),
        max_history_messages=(
            _as_int(env["AGENT4NAO_MAX_HISTORY_MESSAGES"], "AGENT4NAO_MAX_HISTORY_MESSAGES")
            if "AGENT4NAO_MAX_HISTORY_MESSAGES" in env else 20),
        max_context_chars=(
            _as_int(env["AGENT4NAO_MAX_CONTEXT_CHARS"], "AGENT4NAO_MAX_CONTEXT_CHARS")
            if "AGENT4NAO_MAX_CONTEXT_CHARS" in env else 8192),
        max_response_chars=(
            _as_int(env["AGENT4NAO_MAX_RESPONSE_CHARS"], "AGENT4NAO_MAX_RESPONSE_CHARS")
            if "AGENT4NAO_MAX_RESPONSE_CHARS" in env else 8192),
        max_concurrent_generations=(
            _as_int(env["AGENT4NAO_MAX_CONCURRENT"], "AGENT4NAO_MAX_CONCURRENT")
            if "AGENT4NAO_MAX_CONCURRENT" in env else 1),
    )

    # 2) explicit constructor overrides (highest precedence)
    if ollama is not None:
        ollama_cfg = ollama
    if limits is not None:
        limits_cfg = limits

    system_prompt = (
        system_prompt
        if system_prompt is not None
        else env.get("AGENT4NAO_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT)
    )
    log_level = (
        log_level if log_level is not None else env.get("AGENT4NAO_LOG_LEVEL", "INFO")
    )
    log_content = (
        log_content
        if log_content is not None
        else (_as_bool(env["AGENT4NAO_LOG_CONTENT"], "AGENT4NAO_LOG_CONTENT")
              if "AGENT4NAO_LOG_CONTENT" in env else False)
    )

    return Agent4NAOConfig(
        ollama=ollama_cfg,
        limits=limits_cfg,
        system_prompt=system_prompt,
        log_level=log_level,
        log_content=log_content,
    )
