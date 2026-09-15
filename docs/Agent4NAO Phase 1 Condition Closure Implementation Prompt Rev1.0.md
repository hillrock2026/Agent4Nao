# Agent4NAO Phase 1 Condition Closure — Implementation Prompt Rev1.0

## 0. Assignment

You are OpenCode + DeepSeek. Close the two minor conditions identified by the
independent TRAE + GLM-5.2 review of Agent4NAO Phase 1.

This is a narrowly scoped correction task. Do not expand the feature set.
TRAE + GLM-5.2 will perform a read-only re-review after your changes.

Read before editing:

1. `docs/Agent4NAO Phase 1 Desktop Local Conversation Implementation Prompt Rev1.0.md`
2. `docs/Agent4NAO Phase 1 Desktop Conversation Runbook.md`
3. `docs/Agent4NAO Phase 1 Acceptance & Phase 2 Action Simulation Plan Rev1.0.md`
4. the GLM-5.2 review report supplied by the project lead

## 1. Current review status

Current status:

```text
Phase 1 Status: PASS WITH CONDITIONS
```

The reviewer verified 42/42 tests, compileall, CLI startup, functional
boundaries, and the absence of ROS 2/NAOqi/robot code. Only these two
conditions remain:

1. `cli.main(argv)` ignores `argv`; `--help` is unsupported.
2. Operation log events do not guarantee a `duration` field, although the
   Phase 1 implementation prompt requires it.

## 2. Condition A — implement CLI help

Modify the thin CLI only as necessary to make argument handling explicit.

Requirements:

- `main(argv)` must consume the supplied argument list rather than ignore it;
- support `--help` and `-h`;
- help must exit successfully;
- help must not instantiate Ollama, connect to the network, or create a
  conversation session;
- help text must state:
  - this is Agent4NAO Phase 1 desktop local conversation;
  - the default model tag;
  - supported configuration mechanism;
  - no robot tools or physical actions are enabled;
- unknown options must fail explicitly with a non-zero result or the standard
  parser error behavior;
- preserve `/exit`, `/quit`, `/q`, and Ctrl-D behavior;
- keep CLI parsing thin and keep conversation/provider logic outside CLI.

Add focused tests for:

- `main(["--help"])`;
- `main(["-h"])`;
- help output and successful exit;
- help does not instantiate or contact Ollama;
- unknown option behavior.

Use the repository’s existing style and standard library where practical.
Do not add a CLI framework dependency for this small feature.

## 3. Condition B — add operation duration to logs

Ensure operation lifecycle events include a measured `duration` field.

Requirements:

- measure elapsed time with `time.monotonic()`;
- use a documented unit, preferably seconds;
- use a documented precision, preferably a bounded decimal or float format;
- include duration for:
  - successful model response;
  - provider unavailable;
  - protocol/malformed response;
  - timeout;
  - cancellation;
  - other terminal model failure;
- include duration on the event emitted at the end of the operation;
- ensure the field is non-negative;
- preserve request/session/provider correlation fields;
- do not use wall-clock subtraction;
- do not use a constant or placeholder duration;
- do not make logging failure change conversation behavior;
- do not log secrets or message content by default.

Add focused tests that:

- capture structured log events;
- assert required terminal events contain `duration`;
- assert duration is non-negative;
- cover success and at least one failure/timeout/cancellation path;
- verify redaction remains intact;
- verify logging failure does not turn a successful conversation into failure.

Update the runbook to state the exact duration unit and precision.

## 4. Scope restrictions

Do not:

- modify Agent-Kernel;
- add Agent-Kernel dependencies;
- resolve `RuntimePublicApiAdapter`;
- add `ModelAction`;
- add tool calling;
- add ROS 2 or `rclpy`;
- add NAOqi or Python 2.7;
- add Gazebo;
- add TLS or robot bridge;
- add `Stand`, `Walk`, `Stop`, or `Observe` hardware behavior;
- change Ollama provider semantics unrelated to these conditions;
- change the Phase 1 product scope;
- add new third-party dependencies;
- commit generated caches or credentials.

The implementation must remain desktop-only and robot-disconnected safe.

## 5. Validation requirements

Run:

```bash
cd Agent4NAO
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
python3 -m compileall -q src tests
PYTHONPATH=src python3 -m agent4nao --help
```

Also verify:

```bash
PYTHONPATH=src python3 -m agent4nao --unknown-option
```

The unknown-option command must fail explicitly without contacting Ollama.

The default test command must pass all previous tests plus the new tests.
Report the exact final count; do not claim 42 if the count changed.

Capture one representative structured terminal event showing:

- event name;
- session id;
- request id;
- provider;
- status;
- non-negative duration;
- no unredacted token/credential/message content.

## 6. Required handoff

Before requesting re-review, provide:

1. changed-file list;
2. concise explanation of each condition closure;
3. exact test commands and outputs;
4. help output;
5. unknown-option output and exit result;
6. representative duration-bearing event;
7. updated documentation location;
8. confirmation that no forbidden scope was added;
9. known limitations.

## 7. Re-review request

Ask TRAE + GLM-5.2 to verify only:

- CLI argument handling and help;
- no provider/network initialization during help;
- unknown option behavior;
- duration measurement and terminal-event coverage;
- monotonic-clock semantics;
- duration documentation;
- preservation of all prior Phase 1 boundaries;
- complete test and compile results.

## 8. Acceptance target

After successful re-review, the project lead may change the status to:

```text
Phase 1 Status: ACCEPTED
Desktop Conversation: ACCEPTED
Phase 2: PLANNED, NOT AUTHORIZED
NAO Actuator Access: NOT AUTHORIZED
ROS 2 Integration: NOT AUTHORIZED
NAOqi Integration: NOT AUTHORIZED
Agent-Kernel Modification: NOT AUTHORIZED
```
