# Agent4NAO Architecture & Project Boundary Rev1.0

> **Revision Note (Rev1.0 corrected, 2026-09-14).** The original Rev1.0 text
> inspected the wrong local tree. It described Agent-Kernel as a Python 3.11+
> package and proposed a `pip` dependency on a sibling `agent-kernel_1`
> checkout. `agent-kernel_1` is a contract-only Python skeleton with no git
> remote and no implemented logic; it is *not* the authoritative project.
> The authoritative Agent-Kernel is the C++20 / CMake project at
> `../agent-kernel`, whose git remote is
> `git@github.com:hillrock2026/Agent-Kernel.git` and whose baseline is 36/36
> passing CTest tests. Sections 3, 4, 9, 12, and 15 are corrected below. This
> document remains a DRAFT / PROPOSED baseline and is not an implementation
> authorization.

## 1. Executive Decision

Agent4NAO is a NAO embodiment/application layer over the existing Agent-Kernel.
Agent-Kernel remains the single authoritative cognitive/runtime foundation.
Agent4NAO owns NAO capabilities, ROS 2 integration, Gazebo Harmonic
integration, real-robot adapters, gait experiments, and experiment
infrastructure. No Agent-Kernel source is copied, forked, or modified by this
initialization.

The first execution target is Gazebo Harmonic. The first useful loop is
`Agent-Kernel -> Agent4NAO capability -> ROS 2 -> Gazebo NAO -> observation`.

The Agent4NAO implementation language and the precise Agent-Kernel consumption
mechanism are Stage 0 decisions (Section 19), constrained by the fact that the
authoritative Agent-Kernel is a C++20 / CMake project (Section 3).

## 2. Project Objective

Demonstrate a minimal embodied-agent loop in which an Agent requests a NAO
action, Agent4NAO invokes a NAO capability, ROS 2 transports the command,
Gazebo executes it, and the resulting observation can re-enter the
Agent-Kernel loop. Gait trajectory generation and evaluation follow only after
this loop is demonstrated.

## 3. Relationship to Agent-Kernel

Agent4NAO is not a replacement for Agent-Kernel and must not absorb generic
Kernel responsibilities. The established separation is preserved:

```text
Runtime = deterministic execution
Agent = intelligent execution owner
Planner = planning
Prompt = information assembly
Model = inference only
ModelResult != ModelAction
ModelAction = Agent-owned
Tool = capability
```

### 3.1 Inspected Agent-Kernel (authoritative)

Repository: `../agent-kernel` (git remote
`git@github.com:hillrock2026/Agent-Kernel.git`, branch `master`, plus
`agents/*` worktrees). Verified on 2026-09-14.

| Aspect | Evidence |
|---|---|
| Language / standard | C++20 (`CMakeLists.txt:9-11`) |
| Build system | CMake >= 3.22 (`CMakeLists.txt:1`) |
| Baseline toolchain | Ubuntu 24.04 + GCC 13.3.0 + CMake 3.28.3 + GTest 1.14.0 (`README.md:19`) |
| Test baseline | 36/36 CTest tests pass (`build-b3-gcc`); branch builds add up to 38 (`README.md:48`) |
| Warning policy | `-Wall -Wextra -Wpedantic -Werror` (`CMakeLists.txt:32`) |
| Package/install | Static libraries; `AK_ENABLE_INSTALL` (default OFF) exports only `agent_kernel` and `agent_kernel_foundation` under namespace `AK::` (`CMakeLists.txt:64-99`) |
| No Python package | No `pyproject.toml`, no Python sources in the authoritative tree |

### 3.2 Layered architecture (actual)

```text
Core Domain      : Session -> Workflow -> Task          (lifecycle STATE owner)
Runtime Layer    : Runtime / Scheduler / Executor / CapabilityResolver / EventBus
                   (execution AUTHORITY; requests transitions on Core objects)
Agent Layer      : Agent, Planner, Prompt, Model, Tool, Context, Memory, Foundation
Composition      : FirstWorkingAgentComposition (bounded StepCycle/Run loop)
```

Key points established from the source, not from directory names:

- **Core owns state; Runtime owns authority** (`docs/architecture/AK0030`,
  `AK0011`, `AK0016`). Runtime never owns Session/Workflow/Task.
- **Agent owns intelligence**; the Agent holds no Runtime type
  (`include/agent_kernel/agent/agent.hpp:18-23`).
- **Two capability vocabularies exist and must not be conflated**: the
  Tool-owned `ak::tool::CapabilityId` / `ToolCapability` (`tool/tool_identity.hpp`,
  `tool/tool_capability.hpp`) versus the Runtime execution capability name in
  `TaskExecutionDescriptor` resolved by `CapabilityResolver`
  (`runtime/include/capability_resolver.h`). The Agent-side bridge is
  `ak::agent::ModelAction::InvokeTool(ak::tool::CapabilityId, arguments)`
  (`include/agent_kernel/fwa/model_action.hpp:44-101`).
- **ModelResult is Model-owned; ModelAction is Agent-owned.** The only
  sanctioned conversion is the Agent-owned, deterministic
  `ak::model_to_runtime::InterpretModelResult(ModelResult) -> ModelAction`
  (`include/agent_kernel/model_to_runtime/model_result_interpreter.hpp`).
  `ModelResult::kFailure` is *not* an interpreter input and must terminate
  before any Runtime invocation.
- **Runtime execution surface** (`runtime/include/runtime.h`):
  `Run(ak::Session&)`, `Stop()`, `RegisterCapability(name, provider,
  ak::CapabilityInvoker)` (sanctioned production registration path),
  `GetInvocationResult(request_id)`, and component accessors.
  `ak::CapabilityInvoker = std::function<std::string(const std::string&)>`
  (`runtime/include/capability_binding.h:36-65`).
- **Agent↔Runtime production link is the least-finished area.** On `master`,
  `ak::agent::RuntimeInteractionPort` is contract-only, no target links
  `agent_kernel_runtime` into the Agent/FWA, and Runtime is one-shot
  (`Run` requires a `kCreated` Session). The concrete bridge
  (`RuntimePublicApiAdapter`) and the TASK 3.x compositions exist only on
  `agents/*` branches. Agent4NAO must treat this seam as a Stage 0 dependency
  risk (Section 19).

Agent4NAO must use these established boundaries rather than inventing parallel
Kernel concepts.

## 4. Agent-Kernel Dependency Strategy

Agent-Kernel is an external, single-authority **C++/CMake** dependency. It is
**not** a Python package; `pip install` of Agent-Kernel is not an available or
permitted mechanism, and the earlier `pip install -e ../agent-kernel_1`
instruction is withdrawn.

Candidate mechanisms, evaluated against the inspected build system:

| Mechanism | Fit | Notes |
|---|---|---|
| Pinned Git commit via CMake `FetchContent`/`ExternalProject` | Strong | Declarative, no vendoring, single source authority |
| Pinned Git submodule + `add_subdirectory` | Strong | Single authority, offline-friendly; adds a full checkout |
| `find_package(AgentKernel)` from installed artifacts | Partial | Export currently covers only `agent_kernel` + `agent_kernel_foundation` (`CMakeLists.txt:76-88`); full extension would modify Agent-Kernel (not authorized now) |
| Source copy / vendored tree | Forbidden | Violates single authority |
| Python package dependency (`pip`) | Not applicable | No Python package exists in the authoritative tree |

**Proposed (pending Stage 0):** consume an **immutable pinned Git commit** of
`agent-kernel` through CMake (`FetchContent` or submodule), and build
Agent4NAO's integration layer against the kernel's static library targets. If
Agent4NAO is implemented in Python (for ROS 2 `rclpy` / NAOqi ergonomics), a
thin Agent4NAO-owned C++ bridge library must be the only component that links
the kernel and exposes a narrow interface to Python. The exact commit,
mechanism, and language split are Stage 0 decisions and must be recorded with
evidence before reproducibility is claimed.

No source dependency, vendored tree, or modification of the Agent-Kernel
checkout is permitted. Agent4NAO may depend on its public C++ interfaces only.

## 5. Agent4NAO Responsibility Boundary

Agent4NAO may own:

- NAO-specific capability contracts and implementations
- NAO state and observation mapping
- ROS 2 nodes and transport mappings
- Gazebo and real-NAO adapters
- robot skills/actions owned by the Agent
- gait generation, evaluation, and optimization
- experiment and validation infrastructure

It must not own generic scheduling, context lifecycle, model inference,
prompt assembly, capability resolution semantics, or Kernel persistence.

## 6. ROS2 Boundary

ROS 2 belongs entirely below the Agent4NAO application boundary:

```text
Agent-Kernel -> Agent4NAO -> ROS 2 -> Gazebo / real NAO
```

Agent4NAO will define the mapping between Agent-owned capability invocations
and ROS 2 topics, services, or actions, plus the mapping from robot state to
observations. ROS 2 dependencies must not be added to Agent-Kernel. ROS 2 code
lives in Agent4NAO (`ros2/`, and the NAO capability adapters). No generic
"Robot Runtime", "Robot Abstraction Layer", or "Gateway" is introduced at
initialization.

## 7. Gazebo Boundary

Gazebo Harmonic is the first target for repeatable and safe experimentation.
Simulator launch, world, robot description, controller, and simulation
transport details remain outside Agent-Kernel and behind Agent4NAO's NAO
capability boundary.

## 8. Real NAO Boundary

Real NAO is a later execution target. Its adapter must implement the same
application-level capability contracts as far as practical, while keeping
hardware-specific transport and safety details in the Agent4NAO/ROS 2
boundary. No real-robot integration is initialized in this change.

## 9. NAO Capability Boundary

The initial capability set is:

```text
Stand | Walk | Stop | Observe
```

Each MVP capability is an Agent4NAO-owned capability with two distinct
bindings that must not be collapsed:

1. **Agent/Tool side** — the capability identity exposed to the Agent as
   `ak::tool::CapabilityId` and described by a Tool `CapabilityContract`.
   The Agent selects it through `ModelAction::InvokeTool`.
2. **Runtime execution side** — a concrete `ak::CapabilityInvoker` registered
   onto the Runtime through `Runtime::RegisterCapability(name, provider,
   invoker)` by Agent4NAO's integration bootstrap (never by the Agent, and
   never by a model). The Runtime `CapabilityResolver` resolves the task
   descriptor; the Executor invokes the invoker.

Agent4NAO validates and translates an Agent-owned action into the target
adapter. A model result is never treated as a ROS 2 command directly, and
`ModelResult -> ROS 2` is a forbidden shortcut.

## 10. Gait Capability Boundary

Gait is an Agent4NAO capability. It consumes gait parameters or a trajectory
request, produces a validated joint trajectory or evaluation result, and uses
the NAO capability/ROS 2 boundary for execution. It does not change
Agent-Kernel's generic model, planner, or runtime contracts.

## 11. Diffusion Gait Boundary

The future diffusion component is a research implementation inside Agent4NAO:

```text
Agent4NAO -> Gait capability -> Diffusion gait model
           -> joint trajectory -> ROS 2 -> Gazebo / real NAO
```

The initial scope is trajectory generation and optimization. End-to-end torque
policies, full reinforcement learning, vision-based locomotion, online
adaptive control, and complex sim-to-real learning are explicitly deferred.

## 12. Observation/Data Flow

```text
Agent decision / Agent-owned ModelAction (kToolInvoke)
        -> Agent4NAO NAO capability
        -> ROS 2 command
        -> Gazebo NAO (or real NAO)
        -> ROS 2 state
        -> Agent4NAO observation mapping
        -> Agent-Kernel Context update / next Agent step
```

This must respect the inspected Kernel seam: execution evidence is carried as
a Runtime/Agent-boundary value object (e.g. `ExecutionResult` and the
Agent-owned `RuntimeObservation`), and re-enters the Agent loop through the
Context contract, not by mutating Core object state directly. The exact
message schemas and event choices require Stage 1 design and review; this
document establishes only the ownership and direction of flow.

## 13. MVP

The MVP must demonstrate:

1. Agent requests `Stand`, `Walk`, `Stop`, or `Observe`.
2. Agent4NAO resolves and invokes the corresponding NAO capability.
3. ROS 2 carries the command.
4. Gazebo NAO executes it.
5. Robot state returns as an observation.
6. The observation can re-enter the Agent-Kernel loop.

Autonomous navigation, vision, SLAM, multi-agent behavior, and complex
planning are excluded from the MVP.

## 14. Non-Goals

- Reimplementing or redesigning Agent-Kernel
- Adding ROS 2 to Agent-Kernel
- Copying the Kernel source tree
- Building a complete robotics platform
- Real-robot deployment before the simulation loop works
- Premature generic robot abstractions
- Full reinforcement learning or sim-to-real training

## 15. Repository Structure

```text
Agent4NAO/
├── docs/       # architecture and decision records
├── src/        # Agent4NAO integration/source package
├── ros2/       # ROS 2 boundary and package assets
├── nao/        # NAO capability contracts and adapters
├── simulation/ # Gazebo Harmonic assets
├── gait/       # gait generation and optimization
├── tests/      # Agent4NAO tests
├── pyproject.toml
└── README.md
```

Because the authoritative Agent-Kernel is C++/CMake, the current Python
package skeleton (`pyproject.toml`, `src/agent4nao/`) is **not yet an
authorized build layout**. The final layout must follow the Stage 0 language
and dependency decision: a CMake-based Agent4NAO (or C++ bridge) may replace or
supplement the Python scaffold. Directories are retained only where each has
an explicit ownership boundary; Agent-Kernel source is not present.

## 16. Development Workflow

1. Review this boundary document and obtain implementation authorization.
2. Complete Stage 0: pin an immutable Agent-Kernel commit, select the
   Agent4NAO language/build split, and record the ROS 2 / Gazebo / OS
   toolchain versions.
3. Implement and test the Gazebo-first `Stand`, `Walk`, `Stop`, and `Observe`
   loop.
4. Validate capability-to-ROS 2 mappings independently from simulator assets.
5. Add gait trajectory experiments after the loop is repeatable.
6. Treat real NAO integration as a subsequent adapter milestone.

## 17. Independent Review Workflow

GitHub Copilot + GPT-5.6 are implementation agents. TRAE + GLM-5.2 perform
independent architecture and implementation reviews. Reviews must check:

- Agent-Kernel remains external and unmodified
- ModelResult is not bypassed into ROS 2
- Agent-owned actions and capability contracts are preserved
- ROS 2/Gazebo details stay out of Kernel modules
- MVP scope and safety boundaries remain intact

Review findings must be resolved or explicitly accepted before advancing a
milestone.

## 18. Architecture Do-Not-Reopen Rules

Unless concrete repository evidence or a reviewed requirement changes, do not
reopen:

- Agent-Kernel as the external/stable foundation
- the Agent4NAO-over-Kernel dependency direction
- ROS 2's placement in Agent4NAO
- Gazebo-first execution
- Agent ownership of ModelAction
- diffusion as a gait capability rather than a Kernel feature
- the forbidding of any direct `ModelResult -> ROS 2` path

These rules prevent accidental duplication and architecture drift; they do
not authorize implementation.

## 19. Open Questions

- Which immutable Agent-Kernel commit will be pinned for the first build?
- Which consumption mechanism (`FetchContent` vs. submodule vs. installed
  artifacts) is selected?
- Is Agent4NAO C++, Python, or a C++ bridge plus Python adapters? Which ROS 2
  client library and NAOqi binding follow from that?
- How is the currently unfinished Agent↔Runtime production seam
  (`RuntimePublicApiAdapter` on an `agents/*` branch, one-shot Runtime on
  `master`) handled? Does Agent4NAO depend on a kernel branch, or wait for
  Workstream R/C?
- Which ROS 2 distribution and Gazebo Harmonic release will be standardized?
- Which NAO simulation package and robot description are acceptable?
- Which ROS 2 topics/services/actions and observation schemas are required?
- What safety limits and acceptance criteria are required for `Walk`?
- Which joint trajectory representation will the first gait experiment use?

These questions are implementation-gating decisions, not reasons to modify
Agent-Kernel now.

## 20. Implementation Authorization Status

This initialization establishes boundaries and project structure only. It does
not authorize ROS 2 nodes, Gazebo worlds, real-robot control, or diffusion
implementation.

```text
Architecture Status: DRAFT / PROPOSED
Implementation Status: NOT AUTHORIZED
Agent-Kernel Modification: NOT AUTHORIZED
```
