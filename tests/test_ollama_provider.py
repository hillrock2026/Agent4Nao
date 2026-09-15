"""Ollama adapter response parsing using recorded fixtures.

No live Ollama process, network, or GPU is required: the HTTP transport is
injected and returns recorded bytes (or raises) for each case.
"""

import json
import socket
from pathlib import Path

import pytest

from agent4nao.config import OllamaConfig
from agent4nao.model.messages import user_message
from agent4nao.model.ollama import (
    KIND_GENERATION_TIMEOUT,
    KIND_UNAVAILABLE,
    OllamaProvider,
    TransportError,
    _default_transport,
)
from agent4nao.model.request import ModelRequest
from agent4nao.model.result import ModelErrorCategory, ModelStatus

FIXTURES = Path(__file__).parent / "fixtures" / "ollama"


def _provider(transport) -> OllamaProvider:
    return OllamaProvider(OllamaConfig(), transport=transport)


def _request() -> ModelRequest:
    return ModelRequest(
        model="qwen2.5:7b-instruct-q4_K_M",
        messages=(user_message("hello"),),
        request_id="req-1",
        timeout_seconds=30.0,
    )


def _transport_returning(raw: bytes):
    def transport(url, payload, connect_timeout, generation_timeout):
        return raw
    return transport


def _transport_raising(exc: Exception):
    def transport(url, payload, connect_timeout, generation_timeout):
        raise exc
    return transport


def test_success_response_parsed() -> None:
    raw = (FIXTURES / "chat_success.json").read_bytes()
    provider = _provider(_transport_returning(raw))
    result = provider.generate(_request())
    assert result.status is ModelStatus.SUCCESS
    assert result.payload == "Hello! I am Agent4NAO."


def test_error_response_maps_to_unavailable() -> None:
    raw = (FIXTURES / "chat_error.json").read_bytes()
    provider = _provider(_transport_returning(raw))
    result = provider.generate(_request())
    assert result.status is ModelStatus.FAILURE
    assert result.category is ModelErrorCategory.PROVIDER_UNAVAILABLE


def test_missing_content_is_invalid_result() -> None:
    raw = (FIXTURES / "chat_missing_content.json").read_bytes()
    provider = _provider(_transport_returning(raw))
    result = provider.generate(_request())
    assert result.status is ModelStatus.INVALID_RESULT


def test_malformed_object_is_invalid_result() -> None:
    raw = (FIXTURES / "chat_malformed.json").read_bytes()
    provider = _provider(_transport_returning(raw))
    result = provider.generate(_request())
    assert result.status is ModelStatus.INVALID_RESULT


def test_non_json_is_invalid_result() -> None:
    provider = _provider(_transport_returning(b"not json at all"))
    result = provider.generate(_request())
    assert result.status is ModelStatus.INVALID_RESULT


def test_provider_unavailable_maps() -> None:
    provider = _provider(_transport_raising(TransportError(KIND_UNAVAILABLE, "refused")))
    result = provider.generate(_request())
    assert result.status is ModelStatus.FAILURE
    assert result.category is ModelErrorCategory.PROVIDER_UNAVAILABLE


def test_generation_timeout_maps() -> None:
    provider = _provider(
        _transport_raising(TransportError(KIND_GENERATION_TIMEOUT, "read timeout")))
    result = provider.generate(_request())
    assert result.status is ModelStatus.FAILURE
    assert result.category is ModelErrorCategory.TIMEOUT


def test_ollama_request_payload_shape() -> None:
    captured: dict = {}

    def transport(url, payload, connect_timeout, generation_timeout):
        captured["url"] = url
        captured["body"] = json.loads(payload.decode("utf-8"))
        return (FIXTURES / "chat_success.json").read_bytes()

    provider = _provider(transport)
    provider.generate(_request())

    assert captured["url"].endswith("/api/chat")
    assert captured["body"]["model"] == "qwen2.5:7b-instruct-q4_K_M"
    assert captured["body"]["stream"] is False
    assert captured["body"]["messages"] == [{"role": "user", "content": "hello"}]


def test_default_transport_connection_refused_is_unavailable() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    with pytest.raises(TransportError) as excinfo:
        _default_transport(f"http://127.0.0.1:{port}/api/chat", b"{}", 1.0, 1.0)
    assert excinfo.value.kind == KIND_UNAVAILABLE
