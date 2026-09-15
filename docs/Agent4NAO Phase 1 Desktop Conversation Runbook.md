# Agent4NAO Phase 1 — Desktop Local Conversation Runbook

Phase 1 scope: desktop-only local-model conversation. No robot, ROS 2, NAOqi,
or actuator code is involved. See the implementation prompt for the full scope.

## 1. Desktop setup

| Requirement | Value (this host) |
|---|---|
| OS | Ubuntu 24.04.5 LTS |
| Python | >= 3.11 (system Python 3.14.6 works; no ROS dependency in Phase 1) |
| Local model runtime | Ollama |
| Model | Qwen2.5-Instruct 7B Q4_K_M |

Install the package (editable) so the `agent4nao-chat` entry point is available:

```bash
python3 -m pip install -e .
```

For an uninstalled checkout, the same entry point is available as:

```bash
PYTHONPATH=src python3 -m agent4nao
```

## 2. Ollama install and model pull

```bash
# start the Ollama server (in another terminal, or as a service)
ollama serve

# pull the exact model tag
ollama pull qwen2.5:7b-instruct-q4_K_M
```

The exact model tag is configurable via `AGENT4NAO_MODEL`. The default is:

```text
qwen2.5:7b-instruct-q4_K_M
```

If the locally available tag differs, set `AGENT4NAO_MODEL` explicitly rather
than relying on a silently different model.

## 3. Interactive run

```bash
agent4nao-chat
```

or, without installing:

```bash
PYTHONPATH=src python3 -m agent4nao
```

Type a message and press Enter; the assistant replies. Exit with `/exit`,
`/quit`, `/q`, or Ctrl-D. If Ollama is not running, the CLI reports an explicit
`provider_unavailable` error instead of a fake answer.

The CLI supports `--help` / `-h` (prints usage and exits successfully without
contacting Ollama) and fails explicitly on unknown options.

## 4. Configuration

Configuration is read from environment variables and is overridable without
code edits. Precedence (highest wins): explicit constructor overrides >
`AGENT4NAO_*` environment variables > built-in defaults.

| Environment variable | Default | Meaning |
|---|---|---|
| `AGENT4NAO_OLLAMA_ENDPOINT` | `http://127.0.0.1:11434` | Ollama HTTP endpoint |
| `AGENT4NAO_MODEL` | `qwen2.5:7b-instruct-q4_K_M` | Model tag |
| `AGENT4NAO_CONNECT_TIMEOUT` | `5` | Connect timeout (seconds) |
| `AGENT4NAO_GENERATION_TIMEOUT` | `60` | Generation timeout (seconds) |
| `AGENT4NAO_MAX_MESSAGE_CHARS` | `4096` | Max user message length |
| `AGENT4NAO_MAX_HISTORY_MESSAGES` | `20` | Max stored history messages |
| `AGENT4NAO_MAX_CONTEXT_CHARS` | `8192` | Max approximate context size |
| `AGENT4NAO_MAX_RESPONSE_CHARS` | `8192` | Max assistant response length |
| `AGENT4NAO_MAX_CONCURRENT` | `1` | Max concurrent generations per session |
| `AGENT4NAO_LOG_LEVEL` | `INFO` | Logging level |
| `AGENT4NAO_LOG_CONTENT` | `0` | Opt-in: log message content |

Limits are enforced explicitly: empty/whitespace input is rejected, oversized
input is rejected, history is dropped oldest-first at `MAX_HISTORY_MESSAGES`,
the request context is trimmed oldest-first at `MAX_CONTEXT_CHARS` (never
mid-message), and responses are truncated at `MAX_RESPONSE_CHARS` (the
`truncated` flag is set and recorded).

## 5. Tests

Default test command (no Ollama, no network, no GPU required):

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
```

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` is required on this host because the ROS 2
Jazzy `launch_testing` pytest plugin is auto-discovered and fails to import
without `lark`. Phase 1 tests never import ROS 2.

Optional live Ollama smoke test (explicitly not part of the default run):

```bash
# with the Ollama server running and the model pulled:
PYTHONPATH=src python3 -c \
  "from agent4nao.config import load_config; from agent4nao.model.ollama import OllamaProvider; from agent4nao.conversation import ConversationSession; s=ConversationSession(OllamaProvider(load_config().ollama)); print(s.send('hello').message)"
```

## 6. Timeout and cancellation semantics

- **Connect timeout**: bounds establishing the TCP connection to Ollama.
- **Generation timeout**: bounds the total wait for a model response. On
  expiry the session returns a `timeout` result and abandons the in-flight
  request.
- **Cancellation**: `session.cancel()` (or closing the session) signals the
  in-flight generation to stop and returns a `cancelled` result. The Ollama
  `/api/chat` call cannot be hard-cancelled once dispatched, so cancellation
  is "stop waiting locally"; the server-side generation may continue and is
  discarded. This is the honest, documented semantic — it is not claimed to be
  hard cancellation.
- **Concurrency**: at most `MAX_CONCURRENT` generations may run per session.
  A second `send()` while one is in flight returns `concurrent_request`.

## 7. Privacy and logging

- Logs are structured JSON event lines carrying `session_id`, `request_id`,
  `provider`, `status`, and `duration` — enough to correlate a turn.
- **Duration** is emitted on the terminal `turn.end` event for every terminal
  outcome (success, provider unavailable, protocol/malformed response,
  timeout, cancellation, and other model failure). Unit is **seconds**, measured
  with `time.monotonic()`, rounded to **6 decimal places** (microsecond
  precision), and always non-negative.
- Message content is **not** logged by default.
- When content logging is enabled (`AGENT4NAO_LOG_CONTENT=1`), token-like and
  credential-like values are still masked by the redactor before emission.
- TLS secrets, tokens, and raw provider credentials are never logged.

## 8. Explicit scope statement

Phase 1 enables **no NAO action**. There is no tool-calling, no `ModelAction`,
no ROS 2, no NAOqi import, and no path from model output to any actuator. A
successful model response is a text reply only.

## 9. Known limitation

The Agent-Kernel `Agent↔Runtime` production seam (`RuntimePublicApiAdapter`,
runtime-backed composition) remains unresolved and is intentionally outside
Phase 1. Agent4NAO Phase 1 does not depend on Agent-Kernel source and does not
modify it. Binding Agent4NAO to Agent-Kernel is a later, separately-reviewed
milestone.
