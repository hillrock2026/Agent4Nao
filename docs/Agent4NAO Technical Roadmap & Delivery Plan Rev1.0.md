# Agent4NAO Technical Roadmap & Delivery Plan Rev1.0

## 1. Role and delivery model

The project lead owns scope, sequencing, architecture decisions, risk
acceptance, and release gates. The project lead does not write implementation
code.

| Role | Owner | Responsibility |
|---|---|---|
| Implementation | OpenCode + DeepSeek | Write code, tests, launch/configuration files, and implementation documentation |
| Independent review | TRAE + GLM-5.2 | Review code, documentation, architecture conformance, tests, and evidence |
| Project lead | Project owner | Decompose work, assign gates, resolve conflicts, and authorize stage transitions |

Implementation and review must be performed in separate working copies or
branches. Reviewers must not silently rewrite the implementation they review.

## 2. Fixed architectural constraints

The following constraints are inherited from
[`Agent4NAO Architecture & Project Boundary Rev1.0.md`](./Agent4NAO%20Architecture%20%26%20Project%20Boundary%20Rev1.0.md):

1. Agent-Kernel is an external, single-authority dependency.
2. Agent4NAO owns NAO capabilities, ROS 2, Gazebo, real-robot adapters, gait,
   and experiments.
3. ROS 2 is not added to Agent-Kernel.
4. `ModelResult` is not a robot command; `ModelAction` remains Agent-owned.
5. Gazebo Harmonic is implemented before real NAO integration.
6. The MVP is limited to `Stand`, `Walk`, `Stop`, and `Observe`.
7. Diffusion starts as trajectory generation/optimization, not end-to-end
   torque control or reinforcement learning.

Any proposed change to these constraints is an architecture change request,
not an implementation detail. It requires independent review and explicit
project-lead approval.

## 3. Technical target architecture

```text
Agent-Kernel public interfaces
          |
Agent4NAO Agent-owned action/capability boundary
          |
ROS 2 command/state boundary
          |
Gazebo Harmonic NAO target
          |
normalized observation
          |
Agent4NAO -> Agent-Kernel context/event/next step
```

The first implementation should use the smallest concrete ROS 2 mapping that
supports the MVP. Do not introduce a generic robot runtime, gateway, or
abstraction layer unless a reviewed requirement proves it necessary.

The authoritative Agent-Kernel is a **C++20 / CMake** project (GCC 13 + GTest,
36/36 CTest baseline), not a Python package. Agent4NAO therefore consumes a
pinned Kernel Git commit through CMake. The Agent4NAO language/build split
(direct C++ integration, or a thin C++ bridge plus Python ROS 2/NAO adapters)
is a Stage 0 decision. The `pyproject.toml` scaffold is not yet an authorized
build layout.

## 4. Stage plan and gates

### Stage 0 — Authorization and reproducibility baseline

**Owner:** Project lead assigns; DeepSeek prepares evidence; GLM-5.2 reviews.

**Deliverables**

- Select the Agent-Kernel commit or immutable artifact to consume.
- Select the Agent4NAO language/build split and the CMake consumption
  mechanism (`FetchContent`, submodule, or installed artifacts).
- Record C++, Python (if used), ROS 2, Gazebo Harmonic, and operating-system
  versions.
- Decide the repository/branch naming and review artifact convention.
- Confirm the NAO Gazebo model/package and its license/availability.
- Convert the current local-only dependency workflow into a reproducible
  dependency declaration.

**Exit gate**

- A clean checkout can install the declared dependencies without copying
  Agent-Kernel source.
- GLM-5.2 confirms no dependency or toolchain ambiguity blocks Stage 1.
- Project lead changes implementation status from `NOT AUTHORIZED` only after
  this gate passes.

### Stage 1 — Contract and message design

**Owner:** OpenCode + DeepSeek; TRAE + GLM-5.2 review.

**Deliverables**

- Define NAO capability request/action/result/observation schemas.
- Define `Stand`, `Walk`, `Stop`, and `Observe` input validation and failure
  semantics.
- Define the Agent4NAO-to-Agent-Kernel integration point using existing public
  Kernel interfaces.
- Define ROS 2 topic/service/action names, QoS expectations, timeout,
  cancellation, and error mapping.
- Document which data is transient command data versus observation/context
  data.

**Exit gate**

- Schemas are versioned and unambiguous.
- A reviewer can trace one request from Agent-owned action to ROS 2 and back to
  observation without inventing a missing layer.
- No ROS 2 type or dependency appears in Agent-Kernel.

### Stage 2 — Deterministic capability adapter

**Owner:** OpenCode + DeepSeek; TRAE + GLM-5.2 review.

**Deliverables**

- Implement capability contracts and deterministic validation.
- Implement target-independent NAO command translation.
- Implement cancellation, timeout, duplicate request, and unavailable-target
  behavior.
- Add unit tests for valid, invalid, incomplete, stale, and conflicting
  commands.
- Keep model/provider integration out of this stage.

**Exit gate**

- Unit tests cover every MVP capability and failure path.
- The adapter can be tested without Gazebo or a real robot.
- Reviewer verifies action ownership and no direct `ModelResult -> ROS 2`
  shortcut.

### Stage 3 — ROS 2 transport and Gazebo bring-up

**Owner:** OpenCode + DeepSeek; TRAE + GLM-5.2 review.

**Deliverables**

- Create the minimum ROS 2 package(s) and launch configuration.
- Bring up the selected NAO model in Gazebo Harmonic.
- Connect command transport to the deterministic capability adapter.
- Connect state transport to the observation mapper.
- Add repeatable smoke tests and a recorded evidence procedure.

**Exit gate**

- From a clean environment, `Stand`, `Walk`, `Stop`, and `Observe` can be
  exercised in Gazebo.
- Stop/cancel and transport failure behavior is observable.
- Evidence includes commands, logs, versions, and pass/fail results.

### Stage 4 — Minimal embodied-agent loop

**Owner:** OpenCode + DeepSeek; TRAE + GLM-5.2 review.

**Deliverables**

- Connect an Agent-owned action request to the Agent4NAO capability boundary.
- Re-enter Gazebo observations into the Agent-Kernel loop.
- Add end-to-end tests for one safe action and one stop/failure path.
- Document the complete data flow and operational runbook.

**Exit gate: MVP complete**

1. Agent requests a capability.
2. Agent4NAO validates and invokes it.
3. ROS 2 transports the command.
4. Gazebo executes it.
5. State returns as an observation.
6. The observation re-enters the Kernel loop.

No autonomous navigation, vision, SLAM, multi-agent behavior, or complex
planning is accepted into the MVP.

### Stage 5 — Gait trajectory baseline

**Owner:** OpenCode + DeepSeek; TRAE + GLM-5.2 review.

**Deliverables**

- Define a joint trajectory representation and safety limits.
- Implement a deterministic baseline trajectory generator.
- Implement Gazebo gait evaluation metrics: stability, completion, duration,
  energy proxy, and failure conditions.
- Store experiment configuration and results reproducibly.

**Exit gate**

- Baseline trajectories are validated before any diffusion model is added.
- Unsafe, malformed, or out-of-range trajectories are rejected before ROS 2.
- Evaluation can reproduce a prior result from recorded configuration.

### Stage 6 — Diffusion gait research capability

**Owner:** OpenCode + DeepSeek; TRAE + GLM-5.2 review.

**Deliverables**

- Add diffusion only behind the established gait capability boundary.
- Start with offline trajectory generation/optimization.
- Compare diffusion output against the deterministic baseline.
- Preserve deterministic safety validation and Gazebo evaluation.
- Record datasets, seeds, model versions, metrics, and failed trials.

**Exit gate**

- Diffusion cannot bypass capability validation or directly publish unsafe
  commands.
- Any claimed improvement is supported by repeatable evaluation.
- No torque policy, online adaptation, vision locomotion, or sim-to-real
  scope is introduced without a new approved change request.

### Stage 7 — Real NAO adapter (future)

**Owner:** OpenCode + DeepSeek; TRAE + GLM-5.2 review.

This stage starts only after the Gazebo loop and safety review pass. It adds a
real-robot target behind the same application-level capability contract,
including hardware watchdogs, connection loss behavior, physical stop
procedures, rate limits, and supervised testing. Simulation remains the
reference target for regression tests.

## 5. Review protocol

For every implementation batch:

1. DeepSeek provides changed files, rationale, test command, and evidence.
2. TRAE + GLM-5.2 receive the exact commit/diff and the applicable gate.
3. Reviewers report findings by severity: blocker, major, minor, or note.
4. DeepSeek resolves findings in a new commit; reviewers re-check only after
   the full evidence package is updated.
5. The project lead accepts the gate only when all blockers/majors are closed
   or explicitly waived with rationale.

Review must include both code and documentation. A passing unit test is not
evidence that the architecture boundary is preserved.

## 6. Required evidence package

Each stage submission must include:

- immutable base commit and implementation commit
- changed-file list
- architecture impact statement
- dependency/toolchain versions
- exact test and launch commands
- test logs and simulator evidence where applicable
- known limitations and deferred risks
- reviewer report and resolution status

No “works locally” approval is sufficient without reproducible commands.

## 7. Branch and artifact discipline

Recommended branch sequence:

```text
main
  └── stage/<stage-id>-<short-name>       # DeepSeek implementation
        └── review/<stage-id>-<short-name> # TRAE/GLM review copy if needed
```

One stage should produce one coherent reviewable change set. Do not mix
dependency migration, ROS 2 bring-up, and gait research in a single batch.

Architecture changes use an ADR or change-request document. Experiment
results use versioned configuration plus a result record. Generated build
directories and local simulator caches are never review artifacts.

## 8. Risk register and controls

| Risk | Control | Stop condition |
|---|---|---|
| Agent-Kernel API drift | Pin immutable dependency and add contract tests | Public interface changes without review |
| Model bypasses Agent ownership | Require explicit ModelResult/ModelAction trace | Direct model output becomes ROS 2 command |
| ROS 2/Gazebo environment mismatch | Record versions and use clean bring-up script | Reproduction differs by undocumented environment |
| Unsafe walk command | Validate limits, timeout, cancellation, and stop path | Stop cannot interrupt command safely |
| Scope expansion | Enforce stage gates and non-goals | Vision/navigation/RL enters MVP without approval |
| Diffusion result not reproducible | Record seed, dataset, model, config, and metrics | Improvement cannot be independently reproduced |
| Real-robot incident | Gazebo-first and supervised hardware gate | Hardware testing begins before safety review |

## 9. Immediate next actions

The next authorized planning actions, in order, are:

1. Project lead selects the Stage 0 owners and review window.
2. DeepSeek inventories the Agent-Kernel commit, public imports, and local
   environment without changing Agent-Kernel.
3. DeepSeek identifies candidate NAO Gazebo packages and records source,
   version, license, and build prerequisites.
4. TRAE + GLM-5.2 independently review the dependency and target selection.
5. Project lead approves or rejects Stage 0.
6. Only after approval does DeepSeek draft Stage 1 schemas and ROS 2 boundary
   documents.

## 10. Current authorization

This roadmap is a management and delivery plan. It does not itself authorize
implementation. Until Stage 0 passes:

```text
Architecture Status: DRAFT / PROPOSED
Implementation Status: NOT AUTHORIZED
Agent-Kernel Modification: NOT AUTHORIZED
```
