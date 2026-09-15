# Agent4NAO Project Initialization Decision Record Rev1.0

> **Revision Note (2026-09-14).** This decision record was missing from the
> original Rev1.0 initialization and is authored now. It also records a
> correction: the first-pass architecture draft inspected `agent-kernel_1`, a
> Python contract-only skeleton, instead of the authoritative C++20 / CMake
> Agent-Kernel at `../agent-kernel`
> (`git@github.com:hillrock2026/Agent-Kernel.git`). The decisions below are
> based on the corrected inspection.

Status: `DRAFT / PROPOSED`. These are initialization decisions, not an
implementation authorization.

## 1. Why Agent4NAO is a new project

Agent-Kernel is a general-purpose cognitive/runtime foundation. NAO
embodiment is a distinct application concern: robot capabilities, ROS 2
transport, Gazebo/Harmonic simulation, real-robot adapters, gait research, and
experiment infrastructure. Keeping these in a separate repository preserves a
single authoritative Kernel source and prevents robotics concerns from leaking
into the Kernel. Agent4NAO is therefore a new project and application layer,
not a Kernel fork or extension.

## 2. Why Agent-Kernel is not copied

A copied tree would create a second, divergent authority for Kernel behavior,
break the Kernel's owner/reviewer governance, and make Kernel fixes and
security updates ambiguous. The task requires a single authoritative
Agent-Kernel. Agent-Kernel is therefore consumed as an external dependency
only.

## 3. How Agent-Kernel will be consumed

The authoritative Agent-Kernel is C++20 built with CMake (>= 3.22), GCC 13,
and GTest; its verified baseline is 36/36 CTest tests. It has no Python
package and no package-index release. Therefore:

- No `pip` dependency and no `agent-kernel_1` checkout. The prior
  `pip install -e ../agent-kernel_1` instruction is withdrawn.
- Agent4NAO will consume an **immutable, pinned Git commit** of
  `https://github.com/hillrock2026/Agent-Kernel` through CMake.
- The mechanism (`FetchContent`/`ExternalProject`, a Git submodule, or
  installed/exported artifacts) is a Stage 0 decision. Note that
  `AK_ENABLE_INSTALL` currently exports only `agent_kernel` and
  `agent_kernel_foundation`; broader export would require a Kernel change and
  is not authorized now.
- If Agent4NAO is implemented in Python for ROS 2/NAOqi ergonomics, a thin
  Agent4NAO-owned C++ bridge must be the only component linking the Kernel and
  must expose a narrow interface to Python.
- Agent4NAO depends only on the Kernel's public interfaces. No source copy,
  vendoring, submodule modification, or Kernel source change is permitted.

## 4. Why ROS 2 is outside Agent-Kernel

ROS 2 is a robotics transport/middleware concern. Adding it to Agent-Kernel
would turn the Kernel into a robotics framework, add a heavy external
toolchain to a C++ project that deliberately has no such dependency, and
violate the established boundary that Agent4NAO owns robot integration. ROS 2
therefore belongs to Agent4NAO, below the application boundary:

```text
Agent-Kernel -> Agent4NAO -> ROS 2 -> Gazebo / real NAO
```

## 5. Why Gazebo is outside Agent-Kernel

Gazebo Harmonic is a simulator used to exercise NAO safely and repeatably. Its
worlds, robot descriptions, controllers, and transport are NAO- and
simulation-specific and have no place in a general Kernel. Gazebo stays behind
Agent4NAO's NAO capability boundary and is the first execution target.

## 6. Why Diffusion is outside Agent-Kernel

The diffusion gait model is research code for trajectory generation and
optimization specific to NAO locomotion. It is not a generic Kernel model,
planner, or runtime concern. It lives inside Agent4NAO behind the gait
capability boundary, uses the NAO capability/ROS 2 boundary for execution, and
must not bypass capability validation. End-to-end torque policy, full RL,
vision-based locomotion, online adaptive control, and sim-to-real training are
deferred.

## 7. What the first MVP is

The smallest useful embodied-agent loop:

```text
Agent (ModelAction)
  -> Agent4NAO NAO capability (Stand | Walk | Stop | Observe)
  -> ROS 2 command
  -> Gazebo Harmonic NAO
  -> ROS 2 state -> Agent4NAO observation
  -> Agent-Kernel Context / next Agent step
```

Success means: the Agent can request a NAO action, Agent4NAO translates it
into a capability invocation, ROS 2 carries it, Gazebo executes it, and the
resulting observation re-enters the Kernel loop. The model result is never
used directly as a ROS 2 command; the Agent owns the interpretation into a
typed action.

## 8. What is deliberately excluded

- Reimplementing or redesigning Agent-Kernel
- Adding ROS 2 or Gazebo to Agent-Kernel
- Copying the Kernel source tree
- A complete robotics platform or generic robot abstraction layer/gateway
- Real-NAO deployment before the Gazebo loop is demonstrated and reviewed
- Autonomous navigation, vision, SLAM, multi-agent behavior, complex planning
- Full reinforcement learning, end-to-end torque policies, sim-to-real,
  vision-based locomotion, online adaptive control
- Any direct `ModelResult -> ROS 2` path
- Implementation before an explicit authorization decision

## 9. Open decisions carried to Stage 0

### 9.1 Confirmed (owner-provided, 2026-09-14)

| Decision | Recorded answer |
|---|---|
| NAO generation / NAOqi | NAO V6 (NAO6), NAOqi OS 2.8 line, Python 2.7 on the robot |
| Desktop OS / Python | Ubuntu 24.04.5 LTS, system Python 3.14.6, ROS 2 Jazzy (Python 3.12) |
| NAOqi on desktop | Not installed / not available on desktop |
| NAO-side runtime | Python 2.7 + NAOqi; no ROS 2 runtime on NAO V6 |
| Local model runtime | Ollama |
| First model / quantization | Qwen2.5-Instruct 7B Q4_K_M |
| Transport | Versioned JSON command/event protocol over TLS-wrapped TCP |
| Authentication | TLS + pre-shared token |
| Emergency stop | NAO-side watchdog (heartbeat/deadline + connection-loss) triggers `ALMotion` stop / stiffness release; physical chest-button e-stop; documented operator procedure |

Consequence: real-NAO execution flows through a NAO-side Execution Agent
(Python 2.7 / NAOqi) over the network; the ROS 2 path is the Gazebo simulation
path. The two targets share the application-level capability contract, not the
transport.

### 9.2 Remaining Stage 0 decisions

1. Immutable Agent-Kernel commit to pin.
2. Consumption mechanism (`FetchContent` / submodule / installed artifacts).
3. Agent4NAO language and build split (C++ link vs. C++ bridge + Python
   adapters), and the ROS 2 client library / NAOqi binding that follows.
4. How to handle the unfinished Agent↔Runtime production seam: on `master`
   `RuntimeInteractionPort` is contract-only, no target links
   `agent_kernel_runtime` into the Agent/FWA, and Runtime is one-shot. The
   `RuntimePublicApiAdapter` and TASK 3.x compositions exist only on
   `agents/*` branches. Decide whether to depend on a Kernel branch or wait
   for Workstream R/C.
5. ROS 2 distribution (Jazzy observed) and Gazebo Harmonic release.
6. NAO simulation package and robot description (source, version, license).
7. ROS 2 topic/service/action names and observation schemas.
8. `Walk` safety limits and acceptance criteria.
9. Desktop-to-NAO bridge shape (standalone process vs. ROS 2-facing adapter).
10. Observation schema and message size / rate / timeout limits (proposal in
    Edge Plan §13.2).

## 10. Consequence and status

This record corrects the Kernel inspection and dependency strategy; it does
not close architecture or authorize implementation.

```text
Architecture Status: DRAFT / PROPOSED
Implementation Status: NOT AUTHORIZED
Agent-Kernel Modification: NOT AUTHORIZED
```
