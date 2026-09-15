"""Fake provider behaviors used by tests and demos."""

from agent4nao.config import OllamaConfig
from agent4nao.model.fake import FakeModelProvider
from agent4nao.model.request import ModelRequest
from agent4nao.model.result import ModelErrorCategory, ModelResult, ModelStatus

from agent4nao.model.messages import user_message


def _request() -> ModelRequest:
    return ModelRequest(
        model="fake",
        messages=(user_message("hi"),),
        request_id="r1",
        timeout_seconds=1.0,
    )


def test_fixed_response() -> None:
    provider = FakeModelProvider(fixed_response="fixed")
    result = provider.generate(_request())
    assert result.status is ModelStatus.SUCCESS
    assert result.payload == "fixed"


def test_scripted_sequence_then_fixed() -> None:
    provider = FakeModelProvider(responses=["a", "b"], fixed_response="c")
    assert provider.generate(_request()).payload == "a"
    assert provider.generate(_request()).payload == "b"
    assert provider.generate(_request()).payload == "c"
    assert provider.generate(_request()).payload == "c"


def test_injected_failure() -> None:
    provider = FakeModelProvider(fail=True)
    result = provider.generate(_request())
    assert result.status is ModelStatus.FAILURE
    assert result.category is ModelErrorCategory.PROVIDER_UNAVAILABLE


def test_request_capture() -> None:
    provider = FakeModelProvider()
    provider.generate(_request())
    provider.generate(_request())
    assert len(provider.requests) == 2
    assert provider.requests[0].request_id == "r1"


def test_ollama_config_unused_by_fake() -> None:
    provider = FakeModelProvider()
    # constructing a fake provider never requires an Ollama endpoint
    assert provider.name == "fake"
