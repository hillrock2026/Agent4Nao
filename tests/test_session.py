"""Conversation session behavior with a deterministic fake provider."""

from agent4nao.config import Agent4NAOConfig, ConversationLimits, OllamaConfig
from agent4nao.conversation import ConversationSession, TurnStatus
from agent4nao.model.fake import FakeModelProvider
from agent4nao.model.request import ModelRequest


def make_config(**limits) -> Agent4NAOConfig:
    return Agent4NAOConfig(
        ollama=OllamaConfig(),
        limits=ConversationLimits(**limits),
    )


def test_create_and_close() -> None:
    session = ConversationSession(FakeModelProvider())
    assert not session.closed
    session.close()
    assert session.closed
    session.close()  # idempotent


def test_normal_conversation() -> None:
    provider = FakeModelProvider(fixed_response="hello there")
    session = ConversationSession(provider)
    result = session.send("hi")
    assert result.ok
    assert result.status is TurnStatus.OK
    assert result.message == "hello there"


def test_multi_turn_history() -> None:
    provider = FakeModelProvider(responses=["first", "second"])
    session = ConversationSession(provider)
    session.send("q1")
    session.send("q2")
    history = session.history()
    assert len(history) == 4
    assert history[0].role == "user"
    assert history[0].content == "q1"
    assert history[1].content == "first"
    assert history[2].content == "q2"
    assert history[3].content == "second"


def test_empty_input_rejected() -> None:
    session = ConversationSession(FakeModelProvider())
    for text in ("", "   ", "\t\n"):
        result = session.send(text)
        assert result.status is TurnStatus.EMPTY_INPUT


def test_oversized_input_rejected() -> None:
    session = ConversationSession(FakeModelProvider(), make_config(max_message_chars=10))
    result = session.send("x" * 11)
    assert result.status is TurnStatus.INPUT_TOO_LARGE
    ok = session.send("x" * 10)
    assert ok.ok


def test_oversized_history_trimmed() -> None:
    provider = FakeModelProvider(fixed_response="r")
    session = ConversationSession(provider, make_config(max_history_messages=2))
    session.send("a")
    session.send("b")
    session.send("c")
    history = session.history()
    assert len(history) == 2
    assert history[0].content == "c"
    assert history[1].content == "r"


def test_context_bounded_in_request() -> None:
    provider = FakeModelProvider(fixed_response="r")
    config = Agent4NAOConfig(
        ollama=OllamaConfig(),
        limits=ConversationLimits(
            max_message_chars=8,
            max_context_chars=18,
            max_history_messages=100,
            max_response_chars=100,
        ),
        system_prompt="sys",
    )
    session = ConversationSession(provider, config)
    session.send("aaaaaaaa")  # 8 chars
    session.send("bbbbbbbb")  # 8 chars

    request = provider.requests[-1]
    assert isinstance(request, ModelRequest)
    total = sum(len(m.content) for m in request.messages)
    assert total <= config.limits.max_context_chars
    contents = [m.content for m in request.messages]
    assert "bbbbbbbb" in contents
    # the oldest user message was dropped by context trimming
    assert "aaaaaaaa" not in contents


def test_closed_session_rejects_send() -> None:
    session = ConversationSession(FakeModelProvider())
    session.close()
    result = session.send("hi")
    assert result.status is TurnStatus.SESSION_CLOSED


def test_clear_resets_history() -> None:
    session = ConversationSession(FakeModelProvider(fixed_response="r"))
    session.send("a")
    assert len(session.history()) == 2
    session.clear()
    assert session.history() == []
