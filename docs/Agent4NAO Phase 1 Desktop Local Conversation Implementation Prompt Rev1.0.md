# Agent4NAO Phase 1 Desktop Local Conversation — Implementation Prompt Rev1.0

## 0. Assignment

You are OpenCode + DeepSeek, responsible for implementing **Agent4NAO Phase 1:
Desktop Local-Model Conversation**.

The project lead owns architecture, scope, and authorization. TRAE + GLM-5.2
will independently review your code and documentation after implementation.

Implement only the desktop conversation milestone. Do not implement NAO
hardware control, gait optimization, ROS 2 integration, NAOqi integration, or
the full Agent↔Runtime seam in this task.

## 1. Authoritative context

Read these documents before changing anything:

1. `docs/Agent4NAO Architecture & Project Boundary Rev1.0.md`
2. `docs/Agent4NAO Desktop Local Model & NAO Edge Plan Rev1.0.md`
3. `docs/Agent4NAO Product Definition & Capability Roadmap Rev1.0.md`
4. `docs/Agent4NAO Stage 0 Runtime Seam & Deployment Split Review Report Rev1.0.md`
5. `README.md`
6. `pyproject.toml`

The current Agent4NAO product direction is:

```text
First milestone: desktop local-model conversation
Second milestone: Gazebo-first gait baseline and optimization
Real NAO: later, through Python 2.7 + NAOqi Execution Agent
```

## 2. Fixed environment and dependency decisions

Desktop:

- Ubuntu 24.04.5
- system Python 3.14.6
- ROS 2 Jazzy uses Python 3.12
- ROS 2 is not part of this Phase 1 implementation

Local model:

- Ollama
- Qwen2.5-Instruct 7B Q4_K_M

Agent-Kernel:

- external dependency only;
- do not copy, fork, or modify Agent-Kernel;
- do not solve the unfinished `RuntimePublicApiAdapter` seam here;
- do not assume the current Agent-Kernel C++ targets are installable Python
  dependencies;
- do not add ROS 2 or NAOqi to Agent-Kernel.

NAO:

- NAO V6;
- NAOqi 2.8;
- Python 2.7 on the robot;
- no NAO code in Phase 1;
- no actuator access in Phase 1.

## 3. Phase 1 product objective

When Ollama is available, a user must be able to run a desktop conversation
with Qwen2.5-Instruct 7B Q4_K_M through Agent4NAO.

When Ollama or the robot is unavailable:

- conversation must fail explicitly and readably;
- no fake success response may be returned;
- the absence of a robot must not prevent desktop-only conversation;
- no model output may cause a physical action.

The Phase 1 flow is:

```text
User message
  -> conversation session
  -> bounded message/context assembly
  -> provider-neutral local model adapter
  -> ModelResult
  -> assistant response
  -> conversation event/history
```

Do not add this flow yet:

```text
ModelResult -> tool call -> NAO -> actuator
```

Tools and physical actions must remain disabled in Phase 1.

## 4. Required implementation scope

Implement the smallest coherent desktop-only conversation slice.

### 4.1 Conversation session

Provide a typed session abstraction supporting:

- create session;
- accept user message;
- produce assistant response;
- retrieve bounded history;
- close session;
- clear or reset conversation state.

The implementation must define behavior for:

- empty or whitespace-only input;
- oversized input;
- closed session;
- concurrent/in-flight request;
- model timeout;
- model unavailable;
- provider protocol error;
- cancellation.

Use explicit domain errors or result types. Do not silently convert provider
errors into successful assistant messages.

### 4.2 Provider-neutral model boundary

Define an Agent4NAO-owned provider interface that does not expose Ollama types
outside the provider adapter.

The boundary must separate:

```text
conversation/session
  -> model request
  -> provider adapter
  -> model result
```

The provider interface must support, as practical for the selected runtime:

- model name/configuration;
- bounded messages;
- timeout;
- cancellation;
- normalized response;
- normalized provider error;
- request correlation id.

Do not let the session depend directly on HTTP, Ollama JSON, or socket details.

### 4.3 Ollama adapter

Implement an Ollama adapter for the configured local model:

```text
qwen2.5:7b-instruct-q4_K_M
```

If the exact local tag differs, make it explicit in configuration and
documentation rather than silently selecting another model.

The adapter must define:

- endpoint configuration;
- model configuration;
- connect timeout;
- generation timeout;
- response parsing;
- malformed-response handling;
- provider-unavailable handling;
- cancellation limitations, if the Ollama API cannot provide hard
  cancellation in the selected mode.

Do not claim cancellation works if the underlying implementation only stops
waiting locally. Document the actual semantics.

### 4.4 Fake model

Provide a deterministic fake provider for tests. It must support:

- fixed response;
- scripted response sequence;
- injected timeout;
- injected provider failure;
- cancellation behavior;
- request capture for assertions.

Tests must not require Ollama, a network connection, or a GPU.

### 4.5 Bounded context

Implement explicit limits for at least:

- maximum user message size;
- maximum history message count;
- maximum approximate context size;
- maximum response size;
- maximum concurrent generation per session.

The limit policy must be documented and tested. Reject or truncate only with
an explicit, documented behavior; never silently grow unbounded history.

### 4.6 Logging and redaction

Provide structured logs sufficient to correlate:

- session id;
- request id;
- model/provider;
- start/end time;
- duration;
- success/failure category;
- cancellation/timeout state.

Do not log:

- TLS secrets;
- tokens;
- raw provider credentials;
- unrestricted full conversation content by default.

If message content is logged for development, make it an explicit opt-in
configuration and document the privacy implication.

## 5. Configuration requirements

Configuration must be explicit and overridable without code edits.

At minimum support:

- Ollama endpoint;
- model tag;
- request timeout;
- maximum response size;
- maximum history/context limit;
- logging level;
- content logging opt-in.

Configuration precedence must be documented. Environment variables are
acceptable for local development; do not commit secrets or machine-specific
credentials.

Provide a safe default configuration that points to localhost and does not
enable robot tools.

## 6. API and package boundary

Keep the implementation under the Agent4NAO package in `src/agent4nao`.
Use clear subpackages only when they represent actual boundaries, such as:

```text
agent4nao/
  conversation/
  model/
  config/
```

Do not create generic `runtime`, `gateway`, `robot`, `ros2`, `naoqi`, or
`kernel-lite` implementation packages for this Phase 1 task.

Do not import ROS 2, `rclpy`, NAOqi, or Agent-Kernel C++ internals.

Do not create a parallel `ModelAction` namespace in this task. No action
execution is implemented yet.

## 7. CLI or minimal user entry point

Provide one minimal, documented desktop entry point for interactive use.

Requirements:

- reads user messages;
- prints assistant responses;
- supports a clear exit command;
- reports provider/session errors visibly;
- does not hang indefinitely;
- does not invoke tools or hardware;
- supports configuration through documented environment variables or options.

Keep the entry point thin. Conversation/session/provider logic must remain
testable without the CLI.

## 8. Required tests

Add focused tests using the existing pytest setup.

At minimum cover:

1. session creation and close;
2. normal fake-provider conversation;
3. multi-turn bounded history;
4. empty input rejection;
5. oversized input behavior;
6. oversized history/context behavior;
7. provider unavailable;
8. provider malformed response;
9. timeout;
10. cancellation;
11. closed-session behavior;
12. concurrent generation behavior;
13. configuration defaults and overrides;
14. logging redaction;
15. guarantee that Phase 1 does not import ROS 2, NAOqi, or robot execution
    modules;
16. Ollama adapter parsing using recorded HTTP/provider fixtures without
    requiring a live Ollama process.

Tests must be deterministic and must pass with Ollama stopped.

If a live Ollama smoke test is useful, make it opt-in, clearly marked, and
never required for the default test command.

## 9. Documentation deliverables

Update or add only documentation directly required for this milestone:

- desktop setup instructions;
- Ollama installation and model pull command;
- exact model tag/configuration;
- interactive run command;
- environment variables/configuration;
- test command;
- timeout/cancellation semantics;
- privacy/logging behavior;
- explicit statement that no NAO action is enabled;
- known limitation that Agent↔Runtime seam remains unresolved and is outside
  Phase 1.

Do not claim that the local model is an Agent-Kernel production provider unless
the repository evidence supports that claim.

## 10. Non-goals and forbidden changes

Do not:

- modify Agent-Kernel;
- copy Agent-Kernel source into Agent4NAO;
- implement RuntimePublicApiAdapter fixes;
- implement Task-D production-agent composition;
- add ROS 2 packages;
- add NAOqi code;
- add Python 2.7 code;
- add TLS bridge code;
- add `Stand`, `Walk`, `Stop`, or `Observe` hardware tools;
- enable model tool calling;
- implement gait generation or optimization;
- implement vision, speech hardware, navigation, SLAM, RL, or diffusion;
- add a second Kernel;
- introduce broad catches that hide provider failures;
- commit credentials or local model secrets.

## 11. Completion criteria

The implementation is complete only when all conditions hold:

- desktop conversation works with a configured local Ollama model;
- fake-provider tests pass without Ollama;
- provider failures are explicit and typed;
- input/history/context/response limits are enforced;
- timeout and cancellation semantics are documented and tested;
- logs are correlated and redacted by default;
- interactive entry point is usable;
- no ROS 2, NAOqi, robot, or actuator code was added;
- Agent-Kernel was not modified;
- documentation contains exact setup and test commands;
- a clean checkout can reproduce the default test run.

## 12. Required handoff to independent review

Before requesting TRAE + GLM-5.2 review, provide:

1. commit id;
2. changed-file list;
3. architecture impact statement;
4. exact setup command;
5. exact default test command;
6. optional live Ollama smoke-test command;
7. test output;
8. configuration example with secrets removed;
9. known limitations;
10. explicit confirmation that no hardware action path exists.

The review request must ask reviewers to check:

- bounded context and response behavior;
- provider error propagation;
- actual cancellation semantics;
- logging redaction;
- absence of hidden tool/action execution;
- absence of ROS 2/NAOqi imports;
- reproducibility;
- documentation/code consistency.

## 13. Authorization

This prompt authorizes only the desktop local-model conversation milestone.
It does not authorize NAO actuator access or Agent-Kernel modification.

```text
Authorized scope: Desktop local-model conversation only
NAO actuator access: NOT AUTHORIZED
ROS 2 integration: NOT AUTHORIZED
NAOqi integration: NOT AUTHORIZED
Agent-Kernel modification: NOT AUTHORIZED
```
