"""Ollama provider adapter.

Talks to a local Ollama HTTP API (``POST /api/chat``) and returns a
provider-neutral :class:`ModelResult`. Ollama-specific JSON and transport
details never leave this module.
"""

from __future__ import annotations

import http.client
import json
import urllib.parse
from typing import Callable, Optional

from agent4nao.config.config import OllamaConfig
from agent4nao.model.provider import ModelProvider
from agent4nao.model.request import ModelRequest
from agent4nao.model.result import ModelErrorCategory, ModelResult


# TransportError kind values, used to map transport failures to categories.
KIND_CONNECT_TIMEOUT = "connect_timeout"
KIND_GENERATION_TIMEOUT = "generation_timeout"
KIND_UNAVAILABLE = "unavailable"
KIND_HTTP = "http"


class TransportError(Exception):
    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind


# Transport signature: (url, payload_bytes, connect_timeout, generation_timeout) -> bytes
Transport = Callable[[str, bytes, float, float], bytes]


def _default_transport(
    url: str,
    payload: bytes,
    connect_timeout: float,
    generation_timeout: float,
) -> bytes:
    parts = urllib.parse.urlsplit(url)
    host = parts.hostname
    port = parts.port or (443 if parts.scheme == "https" else 80)
    path = parts.path or "/"

    try:
        if parts.scheme == "https":
            conn = http.client.HTTPSConnection(host, port, timeout=connect_timeout)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=connect_timeout)
        # Establish the TCP connection now, bounded by connect_timeout.
        conn.connect()
    except OSError as exc:  # refused / unreachable / connect timeout
        raise TransportError(KIND_UNAVAILABLE, f"connection failed: {exc}") from exc

    try:
        headers = {"Content-Type": "application/json"}
        # Switch to the generation timeout once connected; this bounds the
        # time spent waiting for the model response.
        if conn.sock is not None:
            conn.sock.settimeout(generation_timeout)
        conn.request("POST", path, body=payload, headers=headers)
        response = conn.getresponse()
        body = response.read()
        if response.status >= 400:
            raise TransportError(
                KIND_HTTP, f"HTTP {response.status}: {body.decode('utf-8', 'replace')}")
        return body
    except OSError as exc:  # read/recv timeout after connect
        raise TransportError(KIND_GENERATION_TIMEOUT, f"generation failed: {exc}") from exc
    finally:
        conn.close()


class OllamaProvider(ModelProvider):
    name = "ollama"

    def __init__(
        self,
        config: OllamaConfig,
        transport: Optional[Transport] = None,
    ) -> None:
        self._config = config
        self._transport = transport or _default_transport

    def generate(self, request: ModelRequest) -> ModelResult:
        endpoint = self._config.endpoint.rstrip("/")
        url = f"{endpoint}/api/chat"
        payload = {
            "model": request.model,
            "messages": [m.to_ollama() for m in request.messages],
            "stream": False,
        }
        body = json.dumps(payload).encode("utf-8")

        try:
            raw = self._transport(
                url,
                body,
                self._config.connect_timeout_seconds,
                request.timeout_seconds,
            )
        except TransportError as exc:
            return self._map_transport_error(exc, request.request_id)
        except Exception as exc:  # unexpected transport failure
            return ModelResult.failure(
                f"transport error: {exc}",
                ModelErrorCategory.PROTOCOL_ERROR,
                request.request_id,
            )

        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            return ModelResult.invalid_result(
                f"malformed JSON response: {exc}", request.request_id)

        return self._parse_response(data, request.request_id)

    def cancel(self, request_id: str = "") -> None:
        # Ollama's synchronous /api/chat call cannot be hard-cancelled once
        # dispatched. Cancellation is therefore stop-waiting only; the session
        # documents this. No-op here by design.
        return None

    @staticmethod
    def _map_transport_error(exc: TransportError, request_id: str) -> ModelResult:
        if exc.kind in (KIND_CONNECT_TIMEOUT, KIND_GENERATION_TIMEOUT):
            return ModelResult.failure(
                f"provider timeout: {exc}", ModelErrorCategory.TIMEOUT, request_id)
        if exc.kind == KIND_UNAVAILABLE:
            return ModelResult.failure(
                f"provider unavailable: {exc}",
                ModelErrorCategory.PROVIDER_UNAVAILABLE,
                request_id,
            )
        return ModelResult.failure(
            f"provider error: {exc}", ModelErrorCategory.PROTOCOL_ERROR, request_id)

    @staticmethod
    def _parse_response(data: object, request_id: str) -> ModelResult:
        if not isinstance(data, dict):
            return ModelResult.invalid_result(
                "response is not a JSON object", request_id)

        if "error" in data:
            return ModelResult.failure(
                str(data["error"]),
                ModelErrorCategory.PROVIDER_UNAVAILABLE,
                request_id,
            )

        message = data.get("message")
        if not isinstance(message, dict):
            return ModelResult.invalid_result(
                "response missing 'message' object", request_id)

        content = message.get("content")
        if not isinstance(content, str):
            return ModelResult.invalid_result(
                "response missing 'message.content'", request_id)

        return ModelResult.success(content, request_id)
