# Agent4NAO Phase 1 Accepted & Phase 2 Execution Plan Rev1.0

## 1. Acceptance decision

The final independent review by TRAE + GLM-5.2 is accepted.

```text
Phase 1 Status: ACCEPTED
Desktop Conversation: ACCEPTED
```

The acceptance is supported by:

- 51/51 tests passing with no regression;
- compileall passing;
- CLI help and unknown-option behavior verified;
- terminal duration events verified on all model-operation paths;
- no Ollama contact required for the default test suite;
- no Agent-Kernel, ROS 2, NAOqi, ModelAction, or hardware path introduced;
- no new third-party dependency.

The `--help` behavior intentionally displays the built-in model default and
directs users to `AGENT4NAO_*` environment variables. It does not claim to
display the active environment override.

## 2. Product meaning of Phase 1

Agent4NAO now has a usable first product slice:

```text
Desktop user
  -> Agent4NAO conversation session
  -> provider-neutral local model boundary
  -> Ollama/Qwen model when available
  -> explicit assistant response or explicit provider error
```

This slice is usable without:

- a connected NAO;
- NAOqi;
- ROS 2;
- Gazebo;
- Agent-Kernel installation;
- GPU or network during default tests.

It is not yet an embodied-agent action system. No model output can execute a
robot action.

## 3. Phase 2 objective

The next milestone is **Typed Action and Observation Simulation**. It will
prove the Agent-owned authorization boundary before any real transport,
NAOqi, ROS 2, or actuator integration is introduced.

```text
User message
  -> ModelResult
  -> explicit Agent authorization
  -> typed Agent4NAO action
  -> Fake NAO Execution Agent
  -> typed result/observation
  -> desktop session/event state
```

Phase 2 is a desktop-only simulation milestone.

```text
Phase 2 implementation: PLANNED, NOT AUTHORIZED
NAO actuator access: NOT AUTHORIZED
```

## 4. Phase 2 design decisions

### 4.1 Temporary Agent4NAO action contract

The project must not create a parallel `ak::agent::ModelAction` or imply that
the unfinished Agent-Kernel Runtime seam has been solved.

Until an approved Kernel public action contract exists, define a clearly
Agent4NAO-owned temporary typed action contract. Its name and package must
make the ownership explicit, for example:

```text
agent4nao.action
```

The contract is a simulation boundary, not a replacement Kernel object.

### 4.2 Initial simulated capabilities

Define only:

- `Observe`;
- `Stop`;
- `Stand`;
- constrained `Walk`.

These are typed simulated capabilities. They do not call NAOqi and must not be
described as real hardware support.

### 4.3 Fake execution target

Implement an in-process deterministic Fake NAO Execution Agent. It must not
import or depend on:

- NAOqi;
- ROS 2;
- sockets/TLS;
- Python 2.7 compatibility;
- Agent-Kernel C++ internals;
- hardware drivers.

## 5. Phase 2 work packages

### WP2-1 — Action/result schema

Define immutable or validation-protected request/result types.

Request fields:

- schema/protocol version;
- request id;
- session id;
- originating turn/action id;
- capability name;
- typed parameters;
- creation timestamp;
- deadline/TTL;
- priority;
- idempotency key.

Result fields:

- request id;
- status;
- error category/reason;
- start/completion timestamps;
- duration;
- result payload;
- observation summary.

Define allowed statuses:

```text
accepted | running | completed | rejected | expired
cancelled | failed
```

### WP2-2 — Agent authorization boundary

Add the minimum orchestration required to ensure:

```text
ModelResult != typed action
typed action = explicit Agent-authorized value
```

Free-form assistant text must never be treated as an executable action.
Action creation must require explicit parsing, schema validation, and
authorization.

The first Phase 2 implementation may use an explicit test/programmatic
authorization path. It must not pretend that unrestricted natural-language
tool calling is safe or complete.

### WP2-3 — Fake execution lifecycle

Implement deterministic lifecycle handling for:

- accepted;
- running;
- completed;
- rejected;
- expired;
- cancelled;
- failed;
- duplicate/idempotent request.

The fake target must return correlated results and observations without any
external service.

### WP2-4 — Safety semantics simulation

Simulate the future NAO-side rules:

- invalid parameter rejection;
- stale/expired command rejection;
- duplicate request handling;
- cancellation;
- resource conflict;
- emergency stop priority;
- unavailable target;
- bounded queue/backpressure.

`Stop` must have higher simulated priority than motion requests.

### WP2-5 — Conversation integration

Connect Phase 1 conversation only to the simulated action path. Preserve the
ability to run pure text conversation with the fake target absent.

The conversation must distinguish:

- assistant text;
- proposed action;
- authorized action;
- fake execution result;
- observation;
- rejection/failure explanation.

No physical side effect may exist.

### WP2-6 — Documentation and evidence

Document:

- temporary action contract ownership;
- lifecycle/status semantics;
- authorization rules;
- fake target behavior;
- explicit absence of real execution;
- exact test commands;
- known limitations;
- future compatibility assumptions for the NAO bridge.

## 6. Phase 2 test plan

Required tests:

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
16. text conversation remains usable with target absent;
17. action duration and terminal event correlation;
18. deterministic repeated simulation result.

All tests must run without Ollama, NAO, ROS 2, network, or GPU.

## 7. Implementation sequence

1. OpenCode + DeepSeek write the Phase 2 implementation specification and
   schema examples.
2. TRAE + GLM-5.2 review the specification before code authorization.
3. OpenCode + DeepSeek implement WP2-1 and WP2-3 first.
4. Add WP2-2 authorization and prove that free-form text cannot execute.
5. Add WP2-4 safety simulation.
6. Add WP2-5 conversation integration.
7. Add documentation and the complete deterministic test suite.
8. TRAE + GLM-5.2 perform independent implementation review.
9. Project lead accepts or rejects Phase 2.

Do not combine Phase 2 with the real NAO bridge or gait work.

## 8. Phase 2 gate

Phase 2 may pass only when:

- action/result schemas are versioned and validated;
- action ownership is explicitly Agent4NAO-side;
- no free-form text path executes an action;
- Fake Execution Agent is deterministic;
- Stop priority and cancellation are tested;
- stale/duplicate/resource conflict behavior is tested;
- result/observation correlation is complete;
- no hardware, network, ROS 2, NAOqi, or Kernel dependency is present;
- all tests pass from a clean checkout;
- documentation matches actual behavior.

After Phase 2 passes, the next milestone is Phase 3 read-only NAO bridge, not
real motion.

## 9. Later milestones

### Phase 3 — Read-only NAO bridge

- TLS/token session;
- heartbeat/reconnect;
- health and observation events;
- battery, posture, fall, and contact summaries;
- no actuator commands.

### Phase 4 — Supervised motion

```text
Stop -> stiffness release -> Stand -> constrained Walk
```

Each capability requires separate safety evidence.

### Phase 5 — Gait baseline

- trajectory contract;
- deterministic baseline;
- Gazebo evaluation;
- metrics and experiment records.

### Phase 6 — Diffusion gait

Diffusion is added only behind trajectory validation and gait capability
boundaries, not as a direct unreviewed actuator policy.

## 10. Current authorization

```text
Phase 1 Status: ACCEPTED
Phase 2 Status: PLANNED, NOT AUTHORIZED
Phase 3 Read-only NAO Bridge: NOT AUTHORIZED
NAO Actuator Access: NOT AUTHORIZED
ROS 2 Integration: NOT AUTHORIZED
NAOqi Integration: NOT AUTHORIZED
Agent-Kernel Modification: NOT AUTHORIZED
```
