# Agent4NAO Desktop Local Model & NAO Edge Plan Rev1.0

## 1. Decision

The next milestone is not gait optimization. It is a split deployment in
which the desktop runs Agent4NAO, the local model, conversation state, and
high-level agent decisions, while the NAO runs only a small deterministic
execution agent beside native NAOqi.

```text
User
  |
  v
Desktop Agent4NAO
  ├── Conversation / prompt assembly
  ├── Local model adapter
  ├── Agent decision and ModelAction ownership
  ├── Task/context lifecycle for long-running work
  └── Event bridge client
          |
          | authenticated, versioned command/event protocol
          v
NAO Execution Agent
  ├── short-cycle local task lifecycle
  ├── emergency and safety tasks
  ├── resource arbitration
  ├── event bridge endpoint
  └── native NAOqi integration
       ├── sensors
       ├── actuators
       └── balance/control
```

The desktop is the cognitive authority. The NAO is the physical safety and
execution authority. A local model never sends a raw NAOqi or actuator command
directly.

## 2. Why this is the next task

NAO CPU and memory are constrained, while local-model inference, prompt
assembly, conversation history, logging, and future planning require desktop
resources. Moving these workloads to the desktop allows the project to
demonstrate a useful user-facing loop before gait research is complete.

The first objective is:

```text
User <-> desktop local model conversation
```

The second objective is:

```text
Desktop Agent4NAO action -> NAO Execution Agent -> NAOqi -> observation/event
```

The model and conversation loop must work without a connected robot. Robot
execution is an additional capability, not a prerequisite for chat.

## 3. Boundary with Agent-Kernel

The existing
[Agent4NAO architecture baseline](./Agent4NAO%20Architecture%20%26%20Project%20Boundary%20Rev1.0.md)
remains authoritative:

- Agent-Kernel stays on the desktop as an external dependency.
- Agent4NAO uses Agent-Kernel public contracts and does not copy or modify it.
- Runtime remains deterministic.
- Model performs inference only.
- `ModelResult` is not an executable robot command.
- Agent owns the interpretation that produces `ModelAction`.
- Capability describes what can be done; the execution agent performs the
  physically constrained operation.

The authoritative Agent-Kernel is a **C++20 / CMake** project, not a Python
package; on the desktop it is consumed as a pinned, immutable Git commit. Where
desktop Agent4NAO code uses Python (ROS 2 / NAOqi / local-model ergonomics), a
thin Agent4NAO-owned C++ bridge must be the only component that links
Agent-Kernel.

The NAO-side Execution Agent is not a second full Agent-Kernel. It is a
bounded safety/execution component with a deliberately smaller contract.
“Kernel-lite” may be used as an implementation nickname, but the public
architecture should call it `NAO Execution Agent` to avoid implying a second
general-purpose Kernel.

## 4. Responsibilities

### 4.1 Desktop Agent4NAO

Owns:

- user session and conversation state
- prompt/information assembly
- local model provider adapter
- model result normalization
- Agent decision and ModelAction creation
- high-level tasks and goals
- capability discovery and command intent
- desktop-side event history and observability
- connection/session management with NAO
- simulation and test doubles

Does not own:

- direct hardware writes
- emergency stop authority
- final joint/resource arbitration
- unsafe command execution
- NAOqi internals

### 4.2 NAO Execution Agent

Owns:

- short-cycle task acceptance, execution, completion, and cancellation
- emergency stop and safety-priority handling
- local resource locks for joints, motion, sensors, and other exclusive
  resources
- command validation against hard limits
- freshness, deadline, sequence, and idempotency checks
- event bridge endpoint and connection-loss behavior
- translation to native NAOqi calls
- compact observations and execution results

Does not own:

- LLM inference
- user conversation
- open-ended planning
- prompt construction
- long-term memory
- gait research
- generic Agent-Kernel scheduling semantics

### 4.3 Native NAOqi

NAOqi remains the authority for low-level sensor, actuator, balance, and robot
hardware behavior. Agent4NAO must not bypass NAOqi to manipulate hardware.

## 5. Local model conversation milestone

The first implementation milestone is desktop-only:

```text
User input
  -> conversation session
  -> Prompt/information assembly
  -> local model adapter
  -> ModelResult
  -> Agent response
  -> conversation event/history
```

The model adapter must be provider-neutral. The first provider may be a local
runtime such as Ollama, llama.cpp, or another approved local inference
service, but provider-specific APIs must stay behind one Agent4NAO adapter.
The selected runtime is a Stage 0 decision and must be recorded with model
name, quantization, context limit, endpoint, and hardware requirements.

The first chat milestone must support:

- session creation and termination
- user/assistant messages
- model timeout and unavailable-provider errors
- bounded conversation history
- cancellation of an in-flight generation
- structured logging without leaking secrets
- a deterministic fake model for tests

Robot actions must not be enabled merely because free-form model text contains
an imperative. Action requests require an explicit, validated Agent-owned
action path.

## 6. Action path after chat

The intended path is:

```text
User request
  -> local model ModelResult
  -> Agent interpretation/authorization
  -> typed ModelAction
  -> Agent4NAO capability request
  -> desktop event bridge client
  -> NAO Execution Agent validation
  -> local resource arbitration
  -> NAOqi operation
  -> execution result / observation event
  -> desktop Agent context and conversation
```

The desktop may request an operation; the NAO Execution Agent may reject,
delay, cancel, or stop it. A successful model response is never evidence that a
physical operation succeeded.

## 7. Desktop-to-NAO protocol

Use a small explicit command/event protocol rather than exposing internal
Python objects or Kernel objects over the network.

### 7.1 Command envelope

Every command should contain:

- protocol version
- message id
- session id
- originating task/action id
- capability/action name
- typed parameters
- creation time
- deadline/TTL
- monotonic sequence number
- cancellation or priority metadata

### 7.2 Result envelope

Every result should contain:

- protocol version
- original message id
- status: accepted, running, completed, rejected, cancelled, expired, failed
- reason/error category
- start and completion timestamps
- compact result payload
- safety or limit information where relevant

### 7.3 Event envelope

Events should distinguish at least:

- connection/session lifecycle
- command acceptance/rejection
- execution state
- safety stop
- resource conflict
- sensor/observation update
- NAOqi fault
- heartbeat/health

Schemas must be versioned independently of model prompts and must be
serializable without importing Agent-Kernel internals on the NAO.

## 8. Connection and safety behavior

The initial transport may use a reliable authenticated local-network channel,
but the transport choice is a Stage 0 decision. The protocol must define:

- mutual endpoint identity or equivalent authentication
- encryption when traffic leaves a trusted host
- heartbeat and health timeout
- command TTL and stale-command rejection
- reconnect and session resynchronization
- duplicate delivery and idempotency
- bounded queues and backpressure
- audit correlation ids

Safety rules:

1. NAO-side emergency stop has priority over desktop commands.
2. Loss of desktop connection must not leave an unbounded command running.
3. Motion commands require deadlines and explicit cancellation behavior.
4. Resource ownership is decided on NAO, close to the hardware.
5. The NAO Execution Agent must fail closed for malformed or unknown commands.
6. A stop command must remain available during degraded connectivity.
7. Hardware-specific hard limits cannot be relaxed by model output.

Physical testing is not authorized until these rules are implemented and
reviewed.

## 9. Resource arbitration

The first resource model should be concrete and small:

```text
motion-control
head-joints
arm-joints
leg-joints
camera
microphone
speaker
```

The NAO Execution Agent arbitrates ownership and conflicts locally. Desktop
task priority is advisory; emergency and safety priorities are authoritative
on NAO. The first implementation should avoid a generic distributed
scheduler. Add resource classes only when a concrete NAO capability requires
them.

## 10. Observation strategy

Do not stream all raw sensor data to the desktop initially. Define compact
typed observations:

- execution status
- robot health and connectivity
- joint/actuator safety state
- balance/fall/emergency state
- capability result
- selected sensor summaries

Raw streams, video, and high-frequency telemetry are separate future
interfaces. The desktop conversation loop should operate on bounded,
timestamped summaries.

## 11. Recommended implementation stages

### Stage A — Desktop chat without robot

Deliver:

- conversation session
- local model adapter
- fake model
- timeout/cancellation/error handling
- bounded history
- desktop tests and runbook

Gate: user can complete a local conversation with the robot disconnected.

### Stage B — Typed action simulation

Deliver:

- Agent-owned ModelAction
- four initial NAO capability schemas
- fake NAO Execution Agent
- command/result/event protocol
- malformed, stale, duplicate, and cancelled command tests

Gate: chat can produce an explicit typed action, but only the fake execution
agent executes it.

### Stage C — Real desktop-to-NAO bridge without motion

Deliver:

- authenticated session
- heartbeat/reconnect
- health and observation events
- NAO-side command validation
- read-only `Observe`

Gate: desktop can connect to NAO and receive health/observation data without
actuator commands.

### Stage D — Supervised safe execution

Deliver:

- `Stop` first
- then `Stand`
- then constrained `Walk`
- local resource arbitration
- emergency and disconnect behavior
- operator runbook and physical safety checklist

Gate: TRAE + GLM-5.2 approve safety evidence before each motion capability is
enabled.

### Stage E — Agent conversation plus supervised robot action

Deliver:

- explicit user confirmation policy for motion
- action/result conversation updates
- event-to-context integration
- complete audit trail

Gate: model cannot directly invoke hardware; every physical effect is visible
as a typed capability action and NAO-side result.

### Stage F — Gait research preparation

Only after the split architecture and supervised execution are stable:

- define gait trajectory interface
- add deterministic baseline
- add Gazebo evaluation
- later add diffusion optimization

This stage remains independent from the first local-model conversation
milestone.

## 12. Review responsibilities

OpenCode + DeepSeek must provide for each stage:

- implementation and documentation diff
- protocol/schema examples
- exact local setup and run commands
- unit/integration test output
- failure-mode evidence
- security and safety assumptions
- known limitations

TRAE + GLM-5.2 must independently verify:

- no Agent-Kernel duplication on NAO
- no direct model-to-hardware path
- correct ModelResult/ModelAction ownership
- fail-closed malformed/stale command handling
- stop and disconnect behavior
- resource arbitration locality
- protocol versioning and compatibility
- documentation matches actual behavior

The project lead authorizes only stage transitions, not individual hidden
implementation shortcuts.

## 13. Stage 0 decisions

Before implementation begins, decide:

1. NAO hardware/software generation and NAOqi version.
2. Desktop operating system and Python version.
3. Local model runtime and first model/quantization.
4. Desktop-to-NAO transport and authentication mechanism.
5. Whether the initial bridge is a standalone process or a ROS 2-facing
   adapter on the desktop.
6. Minimal NAO-side runtime language/toolchain compatible with NAO.
7. Exact safety stop mechanism and operator procedure.
8. First observation schema and message size/rate limits.

### 13.1 Confirmed (owner-provided, 2026-09-14)

| # | Decision | Recorded answer |
|---|---|---|
| 1 | NAO generation / NAOqi | **NAO V6 (NAO6)**; NAOqi OS 2.8 line, Python 2.7 on the robot (exact NAOqi patch to be read on device) |
| 2 | Desktop OS / Python | **Ubuntu 24.04.5 LTS**; system Python 3.14.6, ROS 2 Jazzy (rclpy under Python 3.12) |
| — | NAOqi on desktop | **Not installed.** NAOqi SDK is not installed/available on the desktop; the desktop does not run NAOqi |
| 3 | Local model runtime | **Ollama** (binary installed on this host; the Kernel `master` already contains an Ollama + Qwen experiment) |
| 3 | First model / quantization | **Qwen2.5-Instruct 7B Q4_K_M** (verify available VRAM/RAM before Stage A) |
| 4 | Transport | **Versioned JSON command/event protocol over TLS-wrapped TCP** (Python 2.7 `ssl` stdlib) |
| 4 | Authentication | **TLS + pre-shared token** first; mutual TLS later if required |
| 6 | NAO-side language/toolchain | **Python 2.7 + NAOqi API.** NAO V6 has no ROS 2 runtime; the NAO-side Execution Agent must be NAOqi-native |
| 7 | Emergency stop | **NAO-side watchdog**: heartbeat/deadline timeout and connection loss trigger `ALMotion` stop / stiffness release; plus the physical chest-button stop and a documented operator procedure |

Consequence: the real-NAO path necessarily goes through a NAO-side Execution
Agent (Python 2.7 / NAOqi) reached over the network; the ROS 2 path is the
Gazebo simulation path. The two targets share the application-level capability
contract but not the transport.

### 13.2 Proposed (pending owner confirmation)

| # | Decision | Proposal |
|---|---|---|
| 5 | Bridge shape | Desktop-side bridge as a standalone process with an optional ROS 2-facing adapter; decide exact shape at Stage B |
| 8 | Observation schema | Compact typed JSON (execution status, health, joint/balance/fall state, capability result, selected sensor summaries); no raw video/high-frequency telemetry initially |
| 8 | Limits | Max message ~64 KB; command TTL ~5 s; heartbeat 1–2 Hz; observation 1–10 Hz; these are initial bounds to be verified against the robot |

These decisions should be recorded by OpenCode + DeepSeek and independently
reviewed by TRAE + GLM-5.2 before Stage A implementation.

## 14. Non-goals for this milestone

- diffusion gait optimization
- full Kernel deployment on NAO
- autonomous navigation
- vision-based locomotion
- reinforcement learning
- raw sensor/video streaming
- unrestricted natural-language hardware control
- distributed general-purpose scheduling
- real-robot testing without a reviewed safety gate

## 15. Authorization status

This document is a technical direction and staging proposal. It does not
authorize implementation or physical robot operation.

```text
Architecture Status: DRAFT / PROPOSED
Implementation Status: STAGE A PLANNING ONLY
NAO Actuator Access: NOT AUTHORIZED
Agent-Kernel Modification: NOT AUTHORIZED
```
