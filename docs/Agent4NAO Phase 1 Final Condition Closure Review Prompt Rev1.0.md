# Agent4NAO Phase 1 Final Condition Closure — GLM-5.2 Review Prompt Rev1.0

## 0. Reviewer role

Act as GLM-5.2 performing the final independent, read-only re-review of the
Agent4NAO Phase 1 condition-closure change.

The implementation was produced by OpenCode + DeepSeek. Do not modify source
files, tests, documentation, dependencies, generated artifacts, or repository
history. Do not commit. Do not repair findings during review.

The review must inspect the actual change set and verify the handoff claims
with source evidence and existing validation commands.

## 1. Review decision to make

Decide whether both conditions from the previous review are truly closed:

```text
Condition A: CLI --help and argv handling
Condition B: duration on terminal log events
```

If both are closed and no regression or boundary violation is found, approve
Phase 1 as accepted. Otherwise return `PASS WITH CONDITIONS` or `FAIL` with
precise findings.

## 2. Phase 1 scope constraints

Phase 1 is desktop-only local-model conversation. The permitted flow is:

```text
User
  -> ConversationSession
  -> bounded context/message assembly
  -> provider-neutral ModelProvider
  -> Ollama/Qwen model
  -> ModelResult
  -> assistant text response
```

The following remain forbidden:

- Agent-Kernel modification, copy, fork, or hidden dependency;
- `ModelAction` or model tool-calling path;
- ROS 2 or `rclpy`;
- NAOqi or Python 2.7;
- Gazebo;
- TLS bridge or robot transport;
- physical action capabilities;
- `Stand`, `Walk`, `Stop`, or `Observe` hardware implementations;
- gait, vision, navigation, SLAM, reinforcement learning, or diffusion.

## 3. Handoff claims to verify

OpenCode + DeepSeek reports these changed files:

1. `src/agent4nao/cli.py`
2. `src/agent4nao/conversation/session.py`
3. `tests/test_cli.py`
4. `tests/test_duration.py`
5. `docs/Agent4NAO Phase 1 Desktop Conversation Runbook.md`

Reported results:

- 51 tests pass, previously 42;
- compileall passes;
- `main(argv)` parses arguments with stdlib `argparse` before config/provider
  construction;
- `--help`/`-h` return 0 without contacting Ollama;
- unknown options return 2;
- `turn.end` includes a non-negative duration rounded to six decimals;
- duration is emitted on success, unavailable, protocol/malformed, timeout,
  cancellation, and other model failure paths;
- correlation fields remain present;
- logging failures cannot alter conversation outcomes;
- no Agent-Kernel, ModelAction, ROS 2, NAOqi, robot, secret, or cache changes;
- cancellation remains documented as stop-waiting only;
- Agent↔Runtime seam remains out of scope.

## 4. Repository inspection

Inspect:

- the full diff for the five reported files;
- all existing Phase 1 source and tests;
- `README.md`;
- `pyproject.toml`;
- the Phase 1 runbook;
- the Phase 1 implementation prompt;
- boundary tests;
- working-tree status and generated artifacts.

Confirm that:

- the claimed files are the actual implementation change set;
- no unrelated files were modified;
- no generated cache is included;
- Agent-Kernel remains unchanged;
- no hidden robot or tool path was added;
- no new third-party dependency was introduced.

Do not accept the handoff summary without checking the implementation.

## 5. Condition A review — CLI

Inspect `src/agent4nao/cli.py` and `tests/test_cli.py`.

Verify:

1. `main(argv)` consumes the supplied argument list.
2. `argparse` runs before:
   - config loading;
   - logging setup that depends on runtime config;
   - Ollama provider construction;
   - ConversationSession construction;
   - any network access.
3. `--help` and `-h`:
   - print useful usage;
   - return exit code 0;
   - do not contact Ollama;
   - do not require a model;
   - do not require a robot;
   - describe Phase 1 no-robot scope.
4. Unknown arguments return exit code 2 and an explicit parser error.
5. Existing `/exit`, `/quit`, `/q`, Ctrl-D, provider error, and KeyboardInterrupt
   behavior remains intact.
6. CLI parsing is thin and does not duplicate provider/session logic.
7. The behavior of `--help` showing the built-in model default rather than an
   environment override is either:
   - clearly documented and acceptable for Phase 1; or
   - identified as a correctness/documentation issue if the output falsely
     claims to display the active configuration.
8. Tests cover both success and failure argument paths without Ollama.

Do not require `--help` to load environment configuration if doing so would
violate the no-provider/no-network help requirement. Judge only whether the
documented behavior is honest and coherent.

## 6. Condition B review — duration

Inspect `src/agent4nao/conversation/session.py`, logging code, and
`tests/test_duration.py`.

Verify:

1. Start time uses `time.monotonic()`.
2. Duration is measured rather than constant or wall-clock based.
3. Duration is in documented seconds (or another explicitly documented unit).
4. Precision/rounding is documented and consistent.
5. Duration is non-negative.
6. `turn.end` contains duration for all terminal paths:
   - success;
   - provider unavailable;
   - protocol/malformed result;
   - timeout;
   - cancellation;
   - other model failure;
   - response truncation if it is a terminal success state.
7. `session_id`, `request_id`, `provider`, and `status` remain present.
8. A logging exception cannot change a successful or failed conversation
   result.
9. Duration is emitted exactly once per terminal turn, unless duplicate events
   are explicitly documented.
10. Tests do not pass merely because they inspect a fabricated event detached
    from the actual session lifecycle.
11. Tests cover at least success and multiple failure/cancellation paths.
12. The runbook matches actual emitted event shape.

Pay special attention to early returns and exception paths. A duration field
on only the happy path is not sufficient.

## 7. Regression review

Run the existing validation commands:

```bash
cd Agent4NAO
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
python3 -m compileall -q src tests
PYTHONPATH=src python3 -m agent4nao --help
PYTHONPATH=src python3 -m agent4nao --unknown-option
```

Expected baseline:

- all tests pass;
- test count is at least 51, or any difference is explained;
- compileall succeeds;
- help exits 0;
- unknown options exit 2;
- neither argument command contacts Ollama.

Also verify that default tests:

- do not require Ollama;
- do not require network;
- do not require GPU;
- still exercise the real session/provider boundaries through fake or injected
  transports;
- do not hide failures through plugin-autoload workarounds.

If the environment prevents a command from running, separate environment
failure from implementation failure and record exact evidence.

## 8. Boundary review

Search the complete Phase 1 project for:

```text
rclpy
ros2
naoqi
ALMotion
ModelAction
Stand
Walk
Stop
Observe
Agent-Kernel imports or copied source
```

A name in documentation explaining that a feature is out of scope is not a
violation. A runtime import, executable path, provider tool, or hardware
capability is a violation.

Confirm the implementation remains safe when:

- Ollama is stopped;
- no robot is connected;
- no Agent-Kernel checkout is installed;
- only the fake provider is used.

## 9. Findings standard

Report only evidence-backed findings:

- **BLOCKER** — Phase 1 cannot be accepted;
- **MAJOR** — important correctness, privacy, boundary, or reproducibility
  issue;
- **MINOR** — localized issue requiring correction or explicit acceptance;
- **NOTE** — non-blocking observation.

Every finding must include:

- severity;
- file and line(s), if available;
- observed behavior;
- evidence/test;
- impact;
- required action.

Do not report the unresolved Agent↔Runtime seam as a Phase 1 defect unless
Phase 1 imports or depends on it. It remains an explicitly deferred
milestone.

## 10. Required output

Return exactly these sections:

1. **Final verdict**
   - `PASS`, `PASS WITH CONDITIONS`, or `FAIL`;
   - concise rationale.

2. **Validation results**
   - commands;
   - test count/result;
   - compile result;
   - CLI help result;
   - unknown-option result;
   - environment limitations.

3. **Condition A result**
   - closed/not closed;
   - evidence.

4. **Condition B result**
   - closed/not closed;
   - evidence.

5. **Findings table**

   | # | Severity | File/Lines | Finding | Evidence | Required action |
   |---|---|---|---|---|---|

6. **Scope and boundary result**

7. **Documentation/reproducibility result**

8. **Acceptance decision**
   - If accepted, state “Phase 1 is accepted; Phase 2 remains unauthorized.”
   - If not accepted, list exact closure conditions.

9. **Final authorization statement**

If no stricter evidence requires otherwise, use:

```text
Phase 1 Status: ACCEPTED
Desktop Conversation: ACCEPTED
Phase 2: PLANNED, NOT AUTHORIZED
NAO Actuator Access: NOT AUTHORIZED
ROS 2 Integration: NOT AUTHORIZED
NAOqi Integration: NOT AUTHORIZED
Agent-Kernel Modification: NOT AUTHORIZED
```
