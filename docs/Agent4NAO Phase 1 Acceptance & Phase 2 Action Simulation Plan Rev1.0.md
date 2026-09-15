# Agent4NAO Phase 1 Acceptance & Phase 2 Action Simulation Plan Rev1.0

## 1. Review decision

The GLM-5.2 review result is accepted:

```text
Phase 1 Status: PASS WITH CONDITIONS
```

The implementation is functionally complete and the architecture boundary is
correct. It must not be declared finally accepted until the two minor
conditions are corrected and independently re-verified.

The conditions are valid against the implementation prompt:

1. `cli.main(argv)` currently ignores `argv`, so `--help` is not implemented.
2. The implementation prompt requires correlated structured logging with a
   `duration` field, while the logging path does not currently guarantee that
   field.

The runbook mentioning duration is not sufficient evidence that emitted log
events contain it.

## 2. Phase 1 closure task

### Owner

OpenCode + DeepSeek implement; TRAE + GLM-5.2 independently re-review.

### Scope

Only correct the two review conditions:

#### A. CLI help

- Make `main(argv)` consume the supplied argument list.
- Add a minimal `--help`/`-h` response.
- Help must describe the entry point, configuration, model default, and
  explicit no-robot scope.
- Help must exit successfully without contacting Ollama.
- Preserve the thin CLI boundary.
- Add tests for `main(["--help"])` and unknown option behavior.

#### B. Event duration

- Add measured duration to emitted lifecycle events that represent an
  operation, at minimum model request/response/failure/timeout/cancellation
  events.
- Use a monotonic clock for elapsed duration.
- Define units and precision in documentation.
- Ensure duration is emitted for success and all terminal failure paths.
- Ensure an exception while logging cannot change conversation behavior.
- Add tests asserting the field exists and is non-negative.

Do not use a constant, wall-clock subtraction, or a success-only duration.

### Closure acceptance

The implementation handoff must include:

- changed-file list;
- exact tests added;
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q` output;
- `compileall` output;
- `python3 -m agent4nao --help` output;
- one representative structured event showing `duration`;
- confirmation that no Phase 1 scope boundary changed.

### Closure gate

TRAE + GLM-5.2 must verify:

- CLI help works without Ollama;
- unknown arguments fail explicitly;
- duration is present on all required terminal events;
- duration semantics are documented and correct;
- all prior 42 tests still pass;
- no ROS 2/NAOqi/ModelAction/robot path was introduced.

Only then may the project status change to:

```text
Phase 1 Status: ACCEPTED
Desktop Conversation: ACCEPTED
```

## 3. Phase 2 objective

After Phase 1 acceptance, begin **Typed Action and Observation Simulation**.
This phase does not connect to NAO hardware, NAOqi, ROS 2, Gazebo, or a
network bridge.

The objective is to prove that a desktop conversation can produce an explicit,
validated, Agent-owned action request without allowing free-form model text to
become a physical command.

```text
User message
  -> ModelResult
  -> Agent authorization boundary
  -> typed action request
  -> Fake NAO Execution Agent
  -> typed result/observation
  -> desktop conversation/event state
```

## 4. Phase 2 scope

### 4.1 Typed capability contracts

Define desktop-only schemas for:

- `Observe`
- `Stop`
- `Stand`
- constrained `Walk`

At this stage these are simulated capabilities. They are not NAOqi calls and
must not be presented as real hardware control.

Each request must include:

- protocol/schema version;
- request id;
- session id;
- originating turn/action id;
- capability name;
- typed parameters;
- creation time;
- deadline/TTL;
- priority;
- idempotency key.

Each result must include:

- request id;
- status;
- error category/reason;
- timestamps and duration;
- result payload;
- observation summary where applicable.

### 4.2 Agent authorization boundary

Introduce only the minimum desktop abstraction needed to distinguish:

```text
ModelResult
  !=
Agent-owned typed action
```

Do not create an unreviewed parallel Kernel `ModelAction` namespace. The
implementation must either:

- use a clearly Agent4NAO-owned, temporary Phase 2 action contract; or
- wait for an approved Agent-Kernel public action contract.

The choice must be documented before implementation.

Free-form model text must never be interpreted as a hardware operation without
explicit parsing, schema validation, authorization, and simulation dispatch.

### 4.3 Fake NAO Execution Agent

Implement an in-process fake execution target with deterministic behavior for:

- accepted;
- running;
- completed;
- rejected;
- expired;
- cancelled;
- failed;
- duplicate/idempotent request.

It must expose no NAOqi, ROS 2, socket, or hardware dependencies.

### 4.4 Safety and validation simulation

Simulate, but do not implement hardware:

- TTL/stale request rejection;
- invalid parameter rejection;
- duplicate request handling;
- cancellation;
- resource conflict;
- emergency stop priority;
- unavailable target;
- bounded queue/backpressure behavior.

`Stop` must have higher simulated priority than motion requests.

## 5. Phase 2 non-goals

Do not implement:

- NAO V6 connection;
- Python 2.7;
- NAOqi;
- ROS 2;
- Gazebo;
- TLS;
- real watchdog;
- real actuator access;
- speech hardware;
- camera or sonar processing;
- gait generation or optimization.

## 6. Phase 2 tests

Required tests include:

1. valid action schema;
2. invalid action schema;
3. free-form text does not execute;
4. explicit authorization is required;
5. `Observe` result;
6. `Stop` priority over motion;
7. stale/expired request;
8. duplicate/idempotent request;
9. cancellation;
10. resource conflict;
11. target unavailable;
12. bounded queue;
13. result/observation correlation;
14. schema version rejection;
15. no ROS 2/NAOqi/network imports;
16. conversation remains usable when simulation target is absent.

## 7. Phase 2 review gate

OpenCode + DeepSeek must provide:

- typed schema documentation;
- implementation and test diff;
- threat/safety assumptions;
- explicit model-to-action path;
- exact test output;
- proof that no real execution path exists.

TRAE + GLM-5.2 must review:

- action ownership;
- schema invariants;
- absence of direct ModelResult-to-command conversion;
- stale/duplicate/cancel behavior;
- priority and resource semantics;
- future compatibility with the NAO Execution Agent protocol;
- absence of hardware and transport code.

## 8. Subsequent roadmap

Only after Phase 2 passes:

### Phase 3 — Read-only real NAO bridge

- TLS/token session;
- heartbeat/reconnect;
- health and observation events;
- battery, posture, fall, and contact summaries;
- no actuator commands.

### Phase 4 — Safety motion primitives

```text
Stop -> stiffness release -> Stand -> constrained Walk
```

Each primitive requires separate safety evidence and approval.

### Phase 5 — Gait baseline

- common trajectory contract;
- deterministic gait;
- Gazebo evaluation;
- metrics;
- repeatable experiment records.

### Phase 6 — Diffusion gait

Diffusion is introduced only behind the gait capability and trajectory
validation boundary.

## 9. Current authorization

```text
Phase 1 Status: PASS WITH CONDITIONS
Next Immediate Task: Close CLI help and duration conditions
Phase 2: PLANNED, NOT AUTHORIZED
NAO Actuator Access: NOT AUTHORIZED
ROS 2 Integration: NOT AUTHORIZED
NAOqi Integration: NOT AUTHORIZED
Agent-Kernel Modification: NOT AUTHORIZED
```
