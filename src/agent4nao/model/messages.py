"""Provider-neutral message representation."""

from __future__ import annotations

from dataclasses import dataclass

ROLE_SYSTEM = "system"
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"


@dataclass(frozen=True)
class Message:
    """One chat message with a role and text content."""

    role: str
    content: str

    def to_ollama(self) -> dict:
        return {"role": self.role, "content": self.content}


def system_message(content: str) -> Message:
    return Message(role=ROLE_SYSTEM, content=content)


def user_message(content: str) -> Message:
    return Message(role=ROLE_USER, content=content)


def assistant_message(content: str) -> Message:
    return Message(role=ROLE_ASSISTANT, content=content)
