# Agent4NAO Phase 1 Desktop Conversation — Independent Review Prompt Rev1.0

## 0. Reviewer assignment

You are TRAE + GLM-5.2, performing an independent, read-only review of the
Agent4NAO Phase 1 desktop local-model conversation implementation.

Do not modify source files, tests, documentation, dependencies, generated
artifacts, or repository history. Do not commit. Do not silently repair
findings. The implementation was produced by OpenCode + DeepSeek and must be
reviewed as an external change set.

The review must inspect the actual files and execute only existing validation
commands where needed. Treat the implementation summary below as a claim to
verify, not as evidence by itself.

## 1. Review objective

Determine whether Phase 1 is complete, safe, reproducible, and ready to pass
the desktop-conversation milestone gate.

Phase 1 is intentionally desktop-only:

```text
User
  -> ConversationSession
  -> bounded context/message assembly
  -> provider-neutral ModelProvider
  -> Ollama/Qwen2.5-Instruct
  -> ModelResult
  -> assistant response
```

No physical robot or robot control path is allowed in this phase.

## 2. Authoritative scope constraints

Phase 1 must not:

- modify, copy, fork, or depend on Agent-Kernel source;
- solve the Agent↔Runtime seam;
- add ROS 2 or `rclpy`;
- add NAOqi or Python 2.7 code;
- add Gazebo integration;
- add TLS bridge or network robot transport;
- expose `Stand`, `Walk`, `Stop`, or `Observe` hardware tools;
- implement ModelAction or tool calling;
- implement gait, vision, navigation, SLAM, reinforcement learning, or
  diffusion;
- return fake success when Ollama is unavailable;
- swallow provider failures in broad exception handlers.

The implementation must remain an independent desktop conversation package.

## 3. Implementation claims to verify

OpenCode + DeepSeek reports:

- Phase 1 is complete;
- 42/42 tests pass;
- `src/agent4nao` contains:
  - `config/`: frozen configuration dataclasses and explicit precedence;
  - `model/`: provider-neutral types, abstract provider, fake provider, and
    Ollama provider;
  - `conversation/`: session, turn results/status, typed domain errors;
  - `log.py`: JSON structured logging and secret redaction;
  - `cli.py` / `__main__.py`: interactive CLI;
- tests cover sessions, fake provider, Ollama parsing, timeout/cancellation,
  concurrency, config precedence, logging redaction, and boundary guarantees;
- no Ollama/network/GPU is required for the default test suite;
- with Ollama down, the CLI reports an explicit provider-unavailable error;
- model default is `qwen2.5:7b-instruct-q4_K_M`;
- the implementation supports `pip install -e .` or `PYTHONPATH=src`;
- generated caches are gitignored;
- no commit was made;
- the Agent-Kernel seam is documented as untouched and out of scope.

Verify each claim against source, tests, documentation, and command output.

## 4. Required repository inspection

Inspect at minimum:

1. `Agent4NAO/src/agent4nao/`
2. `Agent4NAO/tests/`
3. `Agent4NAO/README.md`
4. `Agent4NAO/pyproject.toml`
5. `Agent4NAO/docs/Agent4NAO Phase 1 Desktop Conversation Runbook.md`
6. `Agent4NAO/.gitignore`
7. the Phase 1 implementation prompt
8. existing architecture and product-boundary documents

Check the actual change set and working-tree state. Confirm whether:

- the claimed files are tracked or merely untracked;
- generated caches are ignored and absent from the deliverable;
- unrelated files were modified;
- Agent-Kernel files remain unchanged;
- no hidden implementation exists outside the stated package.

Do not infer completeness from filenames. Read the implementation and tests.

## 5. Functional review

### 5.1 Configuration

Verify:

- `Agent4NAOConfig`, `OllamaConfig`, and `ConversationLimits` are genuinely
  immutable or safely protected from mutation;
- explicit > environment > defaults precedence is implemented exactly as
  documented;
- malformed values fail explicitly with useful errors;
- defaults point to localhost and do not enable robot tools;
- model tag is configurable;
- endpoint, timeouts, history/context limits, response limits, logging level,
  and content logging are configurable;
- no credentials or secrets are committed.

### 5.2 Provider-neutral model boundary

Verify:

- conversation code depends on the provider abstraction rather than Ollama
  transport details;
- `Message`, request, result, success, invalid-result, and failure types have
  coherent invariants;
- provider errors remain distinguishable from model-generated content;
- malformed provider output cannot become successful content;
- request correlation ids are preserved where promised;
- the API does not accidentally introduce a future tool/action path.

### 5.3 Fake provider

Verify that the fake provider is deterministic and testable for:

- fixed response;
- scripted responses;
- delay/timeout;
- provider failure;
- cancellation;
- request capture.

Check that tests do not accidentally depend on timing races.

### 5.4 Ollama provider

Verify:

- endpoint construction and HTTP method/path;
- request body shape for `/api/chat`;
- model tag default and override;
- message role/content mapping;
- response parsing;
- malformed JSON/schema behavior;
- connect timeout versus generation timeout;
- connection refused/provider unavailable behavior;
- non-success HTTP status behavior;
- cancellation behavior is honestly documented;
- response-size limits are enforced;
- transport resources are closed correctly.

Do not require a live Ollama service for the default suite, but inspect
fixtures and injectable transport tests for realistic coverage.

### 5.5 Conversation session

Verify:

- create, message, response, close, reset, and history semantics;
- empty/whitespace input handling;
- oversized input behavior;
- bounded message count;
- bounded approximate context size;
- oldest-first truncation behavior;
- no mid-message corruption;
- response truncation behavior;
- closed-session errors;
- concurrent/in-flight request rejection;
- timeout and cancellation state transitions;
- provider failure propagation;
- no unbounded memory growth through history or results.

Pay special attention to race conditions between timeout, cancellation,
provider completion, session close, and concurrent requests.

### 5.6 Logging and privacy

Verify:

- events are structured JSON as documented;
- session/request correlation is present;
- durations and failure categories are useful;
- tokens, authorization values, endpoint credentials, and sensitive config are
  redacted;
- conversation content is not logged by default;
- opt-in content logging is explicit;
- exception strings cannot accidentally bypass redaction;
- logging failures do not hide the original provider/session error.

### 5.7 CLI

Verify:

- documented entry points work;
- `/exit` and Ctrl-D terminate cleanly;
- provider errors are visible and accurately categorized;
- the CLI does not hang indefinitely;
- keyboard interruption is handled appropriately;
- the CLI does not import or invoke robot tools;
- CLI logic remains thin and does not duplicate session/provider behavior.

## 6. Boundary and architecture review

Search the complete Agent4NAO project for:

- `rclpy`, `ros2`, `launch`, `naoqi`, `ALMotion`;
- Python 2 compatibility code;
- `ModelAction`;
- `Stand`, `Walk`, `Stop`, `Observe` hardware capability implementations;
- direct socket/robot command code;
- Agent-Kernel source copies or imports;
- tool registry or model tool-calling paths;
- broad `except Exception` handlers that create success-shaped fallbacks.

Confirm the implementation contains none of the forbidden paths.

Check that:

- the Agent-Kernel Runtime seam is only documented as out of scope;
- no hidden dependency on Agent-Kernel was added;
- Phase 1 remains runnable with the robot disconnected;
- Phase 1 does not claim to be a production Agent-Kernel provider;
- future action integration can be added without coupling conversation code
  directly to hardware.

## 7. Test and reproducibility review

Run the smallest existing validation command that covers the full Phase 1
implementation:

```bash
cd Agent4NAO
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
```

Verify the reported result is exactly 42 passing tests, or explain any
difference. Do not install new tools or dependencies during review.

Also verify, where supported by the repository:

```bash
python3 -m compileall -q src tests
python3 -m agent4nao --help
```

Check that:

- tests pass with Ollama stopped;
- tests do not require network/GPU;
- live Ollama checks are opt-in and not accidentally collected by default;
- setup instructions work from a clean checkout;
- `pip install -e .` does not silently install forbidden dependencies;
- `PYTHONPATH=src python3 -m agent4nao` works as documented;
- the ROS Jazzy pytest plugin workaround is documented accurately and does not
  hide project test failures.

If the default command fails due to the environment, separate environment
failure from implementation failure and provide the exact evidence.

## 8. Documentation review

Compare source behavior with:

- README;
- desktop conversation runbook;
- architecture boundary document;
- product roadmap;
- Phase 1 implementation prompt.

Check that documentation accurately states:

- model tag and override;
- install/run/test commands;
- timeout and cancellation semantics;
- provider-unavailable behavior;
- logging/privacy behavior;
- no-NAO and no-action status;
- Agent-Kernel seam limitation;
- live Ollama smoke test is optional;
- known limitations are not presented as completed features.

## 9. Findings standard

Report only evidence-backed findings. Classify each as:

- **BLOCKER** — cannot accept Phase 1;
- **MAJOR** — important correctness, safety, boundary, or reproducibility
  defect requiring correction before acceptance;
- **MINOR** — localized issue that should be corrected but does not invalidate
  the milestone;
- **NOTE** — non-blocking observation or future consideration.

For every finding include:

- severity;
- file and line(s), when available;
- concrete behavior;
- why it violates the Phase 1 requirements;
- reproducibility/evidence;
- recommended correction or containment.

Do not report hypothetical issues without a plausible execution path.

## 10. Required output format

Return a report with exactly these sections:

1. **Verdict**
   - `PASS`, `PASS WITH CONDITIONS`, or `FAIL`
   - one-paragraph rationale

2. **Verification summary**
   - test command and result;
   - compile/CLI checks;
   - environment limitations;
   - claim verification table

3. **Findings table**

   | # | Severity | File/Lines | Finding | Evidence | Required action |
   |---|---|---|---|---|---|

4. **Functional review**
   - configuration;
   - provider boundary;
   - Ollama adapter;
   - session limits/state;
   - logging/privacy;
   - CLI.

5. **Architecture boundary review**
   - forbidden imports/paths;
   - Agent-Kernel isolation;
   - no hardware action path;
   - future extensibility.

6. **Documentation and reproducibility review**

7. **Acceptance conditions**
   - list any conditions required before approval;
   - if none, state “No blocking conditions”.

8. **Final authorization statement**

Use this exact status unless the evidence justifies a stricter status:

```text
Phase 1 Status: [PASS / PASS WITH CONDITIONS / FAIL]
Desktop Conversation: [ACCEPTED / CONDITIONALLY ACCEPTED / NOT ACCEPTED]
NAO Actuator Access: NOT AUTHORIZED
ROS 2 Integration: NOT AUTHORIZED
NAOqi Integration: NOT AUTHORIZED
Agent-Kernel Modification: NOT AUTHORIZED
```

## 11. Review limitations

This is an independent review of Phase 1 only. Do not expand the review into
gait, NAOqi, ROS 2, bridge, or Agent-Kernel Runtime implementation except to
confirm that those boundaries were not violated.
