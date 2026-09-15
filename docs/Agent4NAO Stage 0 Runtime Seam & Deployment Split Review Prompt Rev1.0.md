# Agent4NAO Stage 0 Runtime Seam & Deployment Split Review Prompt Rev1.0

## Reviewer role

Act as an independent architecture and repository reviewer for Agent4NAO.
Do not modify files, create code, switch branches, install dependencies, or
silently repair findings. Produce an evidence-based review only.

The implementation/technical inventory was prepared by OpenCode + DeepSeek.
The independent review is assigned to TRAE + GLM-5.2.

## Decision context

Agent4NAO will run on a desktop and use a local model for user conversation.
NAO V6 will run only a constrained NAO-side Execution Agent:

```text
Desktop:
Agent4NAO + Agent-Kernel + Ollama + Qwen2.5-Instruct 7B Q4_K_M

Network:
versioned JSON over TLS-wrapped TCP
authentication: TLS + pre-shared token

NAO V6:
Python 2.7 + NAOqi OS 2.8
no ROS 2
no NAOqi installation on desktop
watchdog + heartbeat/deadline + connection-loss stop/stiffness release
physical chest button + operator procedure
```

Desktop environment:

- Ubuntu 24.04.5
- system Python 3.14.6
- ROS 2 Jazzy with `rclpy` on Python 3.12
- ROS 2 is for the Gazebo simulation path only

The real NAO path is:

```text
Desktop Agent4NAO
  -> versioned command/event bridge
  -> NAO-side Execution Agent
  -> NAOqi
  -> NAO sensors/actuators
```

The existing Agent4NAO boundary document states that Agent-Kernel is an
external stable foundation and must not be copied or modified.

## Primary review question

Determine whether the current Agent-Kernel repository state is technically
usable as the desktop dependency for Agent4NAO, with special focus on:

1. the Agent↔Runtime seam;
2. the exact status of `RuntimePublicApiAdapter`;
3. Task-D production-agent composition and build integration;
4. the desktop Python/ROS 2/local-model split;
5. the Python 2.7 NAO-side bridge constraint;
6. whether the proposed deployment split preserves existing architecture
   boundaries.

## Required repository inspection

Inspect actual repository evidence, not only documentation:

1. `master` and all relevant `agents/*` branches/worktrees;
2. the source and headers for `RuntimePublicApiAdapter`;
3. `RuntimeInteractionPort`, runtime public API, runtime observation/result
   types, and Agent composition;
4. Task-D production-agent source, build targets, tests, and install/export
   behavior;
5. branch ancestry and commit IDs for every claimed implementation;
6. Agent-Kernel language/build/toolchain requirements;
7. existing provider/model boundaries relevant to desktop Ollama integration;
8. any current bridge, gateway, transport, or serialization precedent.

At minimum compare:

```text
master
agents/agent-development-feedback
agents/agent-kernel-ollama-minimal-experiment
agents/project-documentation-review
agents/task-d-local-model-integration
agents/task-e-preconditions-setup-commands
```

If a branch does not contain the claimed symbol, record that as evidence
instead of inferring that it is implemented elsewhere.

## Specific questions to answer

### A. Agent↔Runtime seam

- Is the seam contract-only on `master`, or is there a usable implementation?
- On which exact commit/ref does `RuntimePublicApiAdapter` exist?
- Is it production code, test-only code, a mock, or an incomplete prototype?
- What headers/libraries does it require?
- Does it expose stable public interfaces suitable for Agent4NAO?
- Does it require C++/CMake even though the current Agent-Kernel checkout also
  contains Python interface work?
- What is the smallest safe dependency boundary for desktop Agent4NAO?
- Should Agent4NAO wait for a Kernel merge, pin a reviewed branch commit, or
  isolate the seam behind a desktop adapter?

### B. Task-D production Agent

- Is Task-D present and buildable on a branch?
- Which files and targets compose Agent, Runtime, Model, Planner, Prompt, and
  Tool/Capability?
- Is the composition compatible with the established
  `ModelResult -> Agent-owned ModelAction -> capability` direction?
- Are there hidden direct model-to-runtime or model-to-robot shortcuts?
- What tests prove the composition?
- What is missing before it can be a desktop dependency?

### C. Language/build split

- Can desktop Agent4NAO be Python 3.12/3.14 while consuming Agent-Kernel
  components that may be C++/CMake?
- Is a Python binding required, or is a process boundary safer for Stage A?
- Can the local model adapter remain Python-only?
- Which components must not be imported into the Python 2.7 NAO process?
- Is the NAO bridge protocol independent of Python versions?

### D. Desktop local-model milestone

- Is Ollama + Qwen2.5-Instruct 7B Q4_K_M appropriate as a provider behind a
  provider-neutral adapter?
- What minimum desktop-only chat path can be implemented without resolving the
  Runtime seam?
- Which model outputs must remain non-executable until Agent authorization?
- What timeout, context-size, cancellation, and error behavior is required?

### E. NAO bridge

- Is versioned JSON over TLS-wrapped TCP viable for Python 2.7 + desktop
  clients?
- Which protocol fields are mandatory for idempotency, TTL, cancellation,
  heartbeat, and audit correlation?
- Is the watchdog behavior sufficient and where are gaps?
- What command size, event rate, timeout, reconnect, and backpressure limits
  must be decided in Stage 0?
- Can `Stop` remain available during degraded connectivity?

### F. Simulation boundary

- Does the proposed split keep ROS 2 confined to Gazebo simulation?
- What is the correct desktop ROS 2 package/process boundary?
- Which observations should be common between Gazebo and real NAO, and which
  are target-specific?

## Required output format

Return a review report with these sections:

1. **Executive verdict**
   - `GO`, `GO WITH CONDITIONS`, or `NO-GO`
   - one-paragraph rationale

2. **Repository evidence table**
   - ref/branch
   - commit
   - relevant file/symbol
   - status
   - confidence

3. **Agent↔Runtime seam findings**

4. **Task-D production-agent findings**

5. **Recommended language/build split**
   - desktop Agent4NAO
   - Agent-Kernel
   - ROS 2/Gazebo
   - NAO Execution Agent
   - bridge protocol

6. **Stage 0 decisions**
   - decided
   - blocked
   - owner
   - evidence required

7. **Architecture violations or risks**
   - severity: blocker, major, minor, note
   - exact file/line or commit where possible
   - consequence
   - recommended containment

8. **Recommended next sequence**
   - desktop-only chat
   - Runtime seam inventory/decision
   - typed action simulator
   - read-only NAO bridge
   - supervised actuator access

9. **Explicit non-recommendations**
   - no Kernel copy to NAO
   - no ROS 2 on NAO V6
   - no NAOqi on desktop
   - no direct model-to-NAOqi path
   - no real actuator access before safety gate

10. **Final authorization statement**

Use this exact conclusion unless evidence justifies a stricter status:

```text
Architecture Status: DRAFT / PROPOSED
Implementation Status: STAGE A PLANNING ONLY
NAO Actuator Access: NOT AUTHORIZED
Agent-Kernel Modification: NOT AUTHORIZED
```

## Review standard

Do not accept documentation claims without source, build, test, or commit
evidence. Distinguish clearly between:

- implemented and tested;
- implemented but unverified;
- documented but absent from source;
- present only on a non-authoritative branch;
- proposed future work.

Do not implement fixes during this review.
