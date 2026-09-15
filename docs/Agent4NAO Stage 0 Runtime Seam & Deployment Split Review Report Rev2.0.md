# Agent4NAO Stage 0 Runtime Seam & Deployment Split Review Report Rev2.0

> Independent read-only review executed against the review prompt in
> `Agent4NAO Stage 0 Runtime Seam & Deployment Split Review Prompt Rev1.0.md`.
> Reviewer: TRAE + GLM-5.2.
> No Agent-Kernel source files were modified, created, or built.
> All evidence is from direct repository inspection on 2026-09-15.

## 1. Executive verdict

**NO-GO** for consuming the current Agent-Kernel state as an Agent4NAO
production/runtime dependency. The `RuntimePublicApiAdapter` and the full
TASK 3.x composition stack (integration → runtime-backed-agent →
model-to-runtime → agent-continuation) are present as production C++ source
on `master@5e29011`, but the dependency is not yet a complete
exported/installable artifact: `AK_ENABLE_INSTALL` exports only
`agent_kernel` and `agent_kernel_foundation`, omitting every runtime and
composition target. The Agent's own `RuntimeInteractionPort` member is a
value-owned contract-only base with no injection mechanism, so the Agent
itself cannot consume the adapter — the adapter is reachable only through
an external composition that is itself not wired into a production Agent
loop. The named `agents/task-d-local-model-integration` branch has zero
implementation delta. Candidate production-agent, provider, and
model-action files exist only as untracked files in the
`agents/project-documentation-review` worktree. No bridge, serialization,
watchdog, reconnect, ROS 2 package, or NAO safety evidence exists
anywhere in the repository.

Desktop-only local chat remains a feasible next milestone.

## 2. Repository evidence

| Ref/worktree | Commit | Relevant file/symbol | Status | Confidence |
|---|---|---|---|---|
| `master` | `5e290116c17e76fc5d95802eebc6f724668796ac` | `RuntimePublicApiAdapter` (`include/agent_kernel/runtime_integration/runtime_public_api_adapter.hpp`, `src/runtime_integration/runtime_public_api_adapter.cpp`) | Implemented production C++ source; CMake target `agent_kernel_runtime_integration` links `agent_kernel_runtime` privately | High — source and CMake inspected |
| `master` | `5e29011` | `RuntimeInteractionPort` (`include/agent_kernel/agent/runtime/runtime_interaction_port.hpp`) | Contract-only base with safe-default rejections; `IsContractOnly() == true` | High |
| `master` | `5e29011` | `Agent` (`include/agent_kernel/agent/agent.hpp:192`) | Agent owns `RuntimeInteractionPort runtime_port_` as a **value member**; no setter, no constructor parameter, no injection mechanism | High |
| `master` | `5e29011` | `RuntimeBackedExecutionComposition` (`include/agent_kernel/runtime_backed_agent/runtime_backed_execution_composition.hpp`) | Agent-owned bounded composition; takes `RuntimeInteractionPort&` reference (external injection point); one-shot synchronous step | High |
| `master` | `5e29011` | `Runtime` (`runtime/include/runtime.h`) | One-shot: `Run(Session&)` requires `kCreated` Session; `Stop()`, `RegisterCapability`, `GetInvocationResult` | High |
| `master` | `5e29011` | `CMakeLists.txt:64-99` (`AK_ENABLE_INSTALL`) | Install exports **only** `agent_kernel` and `agent_kernel_foundation`; omits `agent_kernel_runtime`, `agent_kernel_runtime_integration`, `agent_kernel_runtime_backed_agent`, `agent_kernel_model_to_runtime`, `agent_kernel_agent_continuation` | High |
| `master` | `5e29011` | `examples/ollama_minimal/*` | Example/demo: synchronous POSIX-socket HTTP client to OpenAI-compatible endpoint; not production; no cancellation/streaming/timeout beyond `poll()` | High |
| `master` | `5e29011` | `tests/ollama_minimal/*` | Fixture tests for the example provider | High |
| `master` | `5e29011` | `ModelAction` (`include/agent_kernel/fwa/model_action.hpp`) | Agent-owned immutable value: `kToolInvoke` / `kComplete` / `kInvalid`; `InvokeTool(CapabilityId, arguments)` | High |
| `agents/agent-development-feedback` | `41b954c03519a0d1489914e80e64292fb2217eda` | Same as baseline | No branch-specific delta | High |
| `agents/agent-kernel-ollama-minimal-experiment` | `41b954c` | Same as baseline | No branch-specific delta | High |
| `agents/project-documentation-review` | `41b954c` | **Untracked** files: `production_agent.hpp`, `production_agent.cpp`, `openai_compatible_model.hpp/.cpp`, `model_action.hpp/.cpp`, `model_action_parser.hpp/.cpp`, plus modified `CMakeLists.txt`, `src/CMakeLists.txt`, `src/model/CMakeLists.txt`, `tests/CMakeLists.txt`, `tests/model/CMakeLists.txt` | Uncommitted and non-authoritative; not on any branch ref | High — `git status` inspected |
| `agents/task-d-local-model-integration` | `41b954c` | Clean worktree; no untracked or modified files | Task-D claim absent; zero implementation delta | High — worktree inspected |
| `agents/task-e-preconditions-setup-commands` | `41b954c` | Same as baseline | No implementation delta | High |

### Branch ancestry

- `master` is exactly 1 commit ahead of `41b954c`.
- The `41b954c..master` diff is **exclusively** the Ollama experiment:
  `examples/ollama_minimal/*`, `tests/ollama_minimal/*`, and
  `third_party/nlohmann/json.hpp` (24,665 lines). No other source changes.
- All five `agents/*` branches point to the identical commit `41b954c`,
  which is the direct parent of `master`. None contains any
  branch-specific implementation.
- The `merge-base` of `master` and any `agents/*` branch is `41b954c`.

## 3. Agent↔Runtime seam findings

### 3.1 Contract port

`RuntimeInteractionPort` (`include/agent_kernel/agent/runtime/runtime_interaction_port.hpp`)
is a concrete base with safe-default virtual implementations:

- `Submit()` returns `kRejected` with `"contract-only port: submission is not implemented"`.
- `Observe()` returns `kFailure` with `"contract-only port: observation is not available"`.
- `IsContractOnly()` returns `true`; `ContractVersion()` returns `1`.
- The header includes **no Runtime header** — it depends only on
  `RuntimeInvocationRequest`, `RuntimeObservation`, and
  `RuntimeSubmissionResult` (all Agent-boundary value types).

### 3.2 Concrete adapter

`RuntimePublicApiAdapter` (`include/agent_kernel/runtime_integration/runtime_public_api_adapter.hpp`,
`src/runtime_integration/runtime_public_api_adapter.cpp`) is production
C++ source, not a mock or test-only code:

- `final` class inheriting `RuntimeInteractionPort`.
- Constructor takes `ak::runtime::Runtime&` (non-owning; Runtime must outlive adapter).
- `RegisterCapability(name, provider, invoker)` — adapter-owned bootstrap table.
- `Submit(request)`:
  1. Validates `capability_id` / `payload` non-blank → reject if invalid.
  2. Bootstraps capability onto Runtime via `Runtime::RegisterCapability`.
  3. Translates `RuntimeInvocationRequest` → `TaskExecutionDescriptor`
     (sole A1 identity translation: `capability_id → descriptor.capability.name`).
  4. Creates a one-shot `Session → Workflow → Task` graph.
  5. Calls `runtime_.Run(*session)` — **synchronous, blocking**.
  6. Returns terminal `RuntimeSubmissionResult` (completed/rejected/failed).
- `Observe(request_id)`:
  1. Retrieves per-invocation `ExecutionResult` via `runtime_.GetInvocationResult(id)`.
  2. Maps success → `RuntimeObservation{kSuccess, output}`.
  3. Maps failure → `RuntimeObservation{kFailure, reason}`.
- The header contains **no Runtime include** — only a forward declaration of
  `ak::runtime::Runtime`. The Runtime link is private to the `agent_kernel_runtime_integration`
  target (`PRIVATE agent_kernel_runtime` in CMakeLists.txt).

### 3.3 Critical seam gap: Agent port is non-injectable

The `Agent` class (`include/agent_kernel/agent/agent.hpp:192`) declares:

```cpp
RuntimeInteractionPort runtime_port_;
```

This is a **value member** of the base type, not a pointer or reference.
Consequences:

- The Agent always owns a contract-only base object — `Submit`/`Observe`
  always reject.
- There is **no constructor parameter**, **no setter**, and **no injection
  mechanism** to replace `runtime_port_` with a `RuntimePublicApiAdapter`.
- `RuntimePort()` returns `const RuntimeInteractionPort&`, so even the
  non-const `Submit`/`Observe` cannot be called through it.
- Object slicing would occur if any attempt were made to copy a derived
  adapter into the base member.

The `RuntimeBackedExecutionComposition` takes a separate
`RuntimeInteractionPort&` reference (constructor parameter), so the
adapter is injectable at the **composition** level — but the composition
is external to the Agent and is not wired into any production Agent run
loop on `master`.

### 3.4 Runtime is one-shot

`Runtime::Run(ak::Session&)` requires the Session to be in `kCreated` state.
After `Run`, the Session transitions to `kStopped`. Each `Submit` call in
the adapter creates a **fresh** Session → Workflow → Task, runs it, and
discards it. There is no persistent Runtime session, no async submission,
no callback, no streaming, and no cancellation path.

### 3.5 No cancellation, deadline, or streaming

- `Submit` is synchronous and blocking: it calls `runtime_.Run(*session)`
  inline and returns only after the Runtime finishes.
- `Observe` is synchronous: it calls `runtime_.GetInvocationResult(id)`.
- There is no timeout parameter, no deadline, no cancellation token, no
  async/future return type, and no streaming callback.
- The `RuntimeSubmissionResult` has only terminal statuses
  (`kCompleted`, `kRejected`, `kFailed`) — no `kAccepted` or `kRunning`
  intermediate state.

### 3.6 Seam verdict

The seam is **contract + production adapter + test-level composition**, not
a **production-ready Agent loop**. The adapter correctly implements the
sanctioned translation boundary and the Runtime Public API is the sole
link, but:

- the Agent cannot consume the adapter (non-injectable port);
- no FWA (First Working Agent) production loop composition exists on
  `master` that ties Agent + Model + Planner + Prompt + Runtime adapter
  into a running cycle;
- the API is synchronous and one-shot with no cancellation, deadline, or
  streaming — insufficient for a desktop chat application with
  in-flight-generation cancellation requirements;
- the install/export does not expose the adapter or composition targets.

**Recommendation:** Agent4NAO should consume only a reviewed immutable
C++ commit through a narrow Agent4NAO-owned C++ facade or a separate
process boundary. Do not bind Python directly to the unfinished target
topology. Do not depend on any `agents/*` branch.

## 4. Task-D production-agent findings

### 4.1 Named branch has no implementation

`agents/task-d-local-model-integration` at `41b954c` has a **clean worktree**
with zero untracked or modified files. No Task-D implementation files exist
on this branch. The branch is indistinguishable from the baseline.

### 4.2 Candidate code is untracked elsewhere

The `agents/project-documentation-review` worktree (also at `41b954c`)
contains **untracked** files:

| Path | Type |
|---|---|
| `include/agent_kernel/production_agent/production_agent.hpp` | Header |
| `include/agent_kernel/production_agent/production_agent_adapters.hpp` | Header |
| `include/agent_kernel/model_action/model_action.hpp` | Header |
| `include/agent_kernel/model_action/model_action_parser.hpp` | Header |
| `include/agent_kernel/model/openai_compatible_model.hpp` | Header |
| `src/production_agent/production_agent.cpp` | Source |
| `src/production_agent/CMakeLists.txt` | Build |
| `src/model_action/model_action.cpp` | Source |
| `src/model_action/model_action_parser.cpp` | Source |
| `src/model_action/json_object_validation.hpp` | Header |
| `src/model_action/CMakeLists.txt` | Build |
| `src/model/openai_compatible/openai_compatible_model.cpp` | Source |
| `src/model/openai_compatible/CMakeLists.txt` | Build |
| `tests/production_agent/production_agent_test.cpp` | Test |
| `tests/production_agent/production_agent_provider_test.cpp` | Test |
| `tests/production_agent/production_agent_local_model_live_smoke_test.cpp` | Live test |
| `tests/model_action/model_action_test.cpp` | Test |
| `tests/model/openai_compatible_model_test.cpp` | Test |
| `tests/model/openai_compatible_model_live_smoke_test.cpp` | Live test |
| Modified `CMakeLists.txt`, `src/CMakeLists.txt`, `src/model/CMakeLists.txt`, `tests/CMakeLists.txt`, `tests/model/CMakeLists.txt` | Modified (not committed) |

These files are **not on any branch ref**. They are uncommitted working-tree
state in a non-authoritative worktree. They cannot serve as a dependency.

### 4.3 Composition direction

Based on the file names and the existing `master` composition chain
(TASK 3.1 → 3.2 → 3.3 → 3.4 → 3.5), the proposed production-agent path is
directionally correct:

```text
ModelResult -> ModelActionParser -> ModelAction (kToolInvoke)
             -> RuntimeBackedExecutionComposition
             -> RuntimeInteractionPort (RuntimePublicApiAdapter)
             -> Runtime -> capability invoker -> ExecutionResult
             -> RuntimeObservation -> Context update -> terminal
```

However, the candidate code:

- is not committed to any branch;
- does not compose the established `Agent`, `Planner`, concrete
  `RuntimePublicApiAdapter`, or real `Tool` implementation (it likely uses
  fake/test doubles);
- introduces a separate `model_action` namespace parallel to the existing
  `ak::agent::ModelAction` (`include/agent_kernel/fwa/model_action.hpp`)
  on `master`, risking a duplication of the Agent-owned action boundary;
- lacks bounded prompt/context sizes and cancellation;
- has not been built or tested in this review.

**Conclusion:** documented/in-progress workspace code, not a buildable
production dependency.

## 5. Recommended language/build split

| Component | Recommendation | Rationale |
|---|---|---|
| Desktop Agent4NAO | Python 3.12/3.14 for UX, local-model integration, conversation orchestration; explicit typed action authorization | ROS 2 `rclpy` and local-model ergonomics favor Python; action authorization must be Agent-owned, not model-owned |
| Agent-Kernel | C++20/CMake desktop-only dependency, pinned by immutable commit (`master@5e29011` candidate pending build/export evidence) | The authoritative tree is C++20/CMake with no Python package; `FetchContent` or submodule is the strongest mechanism |
| Agent-Kernel bridge | Thin Agent4NAO-owned C++ facade or **process boundary** linking only `agent_kernel_runtime_integration` (or a narrower subset) | The target topology is unfinished; a process boundary is safer than direct Python binding for Stage A |
| ROS 2/Gazebo | Python 3.12 / ROS 2 Jazzy simulation process; never on NAO | ROS 2 is for Gazebo simulation only; must not cross into Kernel or NAO |
| NAO Execution Agent | Python 2.7 + NAOqi-native, bounded and deterministic | NAO V6 runs NAOqi OS 2.8 / Python 2.7; no ROS 2 runtime available |
| Bridge protocol | Version-neutral JSON envelopes over TLS-wrapped TCP; validate Python 2.7 `ssl` stdlib cipher/certificate support on the NAO device | JSON is language-neutral; TLS-wrapped TCP is viable if NAO `ssl` supports adequate ciphers |

The pre-shared token should be an application-level authenticated field
**inside** TLS, not a substitute for transport protection. Mutual TLS
should be evaluated for Stage C.

## 6. Stage 0 decisions

| Decision | State | Owner | Evidence still required |
|---|---|---|---|
| NAO V6 / NAOqi 2.8 / Python 2.7 | Decided/documented | Project lead | Device version capture; Python `ssl` cipher/certificate capability test on NAO |
| Ollama + Qwen2.5-Instruct 7B Q4_K_M | Decided/documented | Project lead | Exact tag/hash; VRAM/RAM verification; context limit; local endpoint smoke test |
| Desktop OS / Python 3.14.6 | Decided/documented | Project lead | Confirmed on device |
| ROS 2 Jazzy / Python 3.12 | Decided/documented | Project lead | Confirmed on device |
| NAOqi not installed on desktop | Decided/documented | Project lead | Confirmed |
| Transport: versioned JSON over TLS-wrapped TCP | Decided/documented | Project lead | Schema; idempotency/TTL/cancel/heartbeat/backpressure tests |
| Authentication: TLS + pre-shared token | Decided/documented | Project lead | Token rotation procedure; mutual TLS evaluation |
| Kernel dependency commit/mechanism | **Blocked** | Project lead + reviewer | Independent CMake/CTest build of `master@5e29011`; export/install decision for runtime + composition targets; reproducible build evidence |
| Runtime seam selection | **Blocked** | Project lead + reviewer | Export/install decision; build/CTest logs; API compatibility review; Agent port injection design decision |
| Desktop bridge shape | **Blocked** | Project lead | C++ facade vs process boundary; failure model; cancellation path |
| JSON/TLS schema and limits | Proposed | Project lead | Schema document; idempotency/TTL/cancel/heartbeat/backpressure tests |
| ROS 2 simulation package | **Missing** | OpenCode + DeepSeek | Package, launch files, Gazebo evidence, common observation mapping |
| NAO watchdog / operator safety gate | **Missing** | OpenCode + DeepSeek | Device test evidence; supervised physical-stop procedure; watchdog implementation |
| Desktop chat service | **Missing** | OpenCode + DeepSeek | Provider-neutral adapter with cancellation, bounded history, timeout, fake-model tests |

## 7. Architecture violations or risks

| Severity | Finding | Exact location | Consequence | Recommended containment |
|---|---|---|---|---|
| **Blocker** | Task-D branch (`agents/task-d-local-model-integration`) has zero implementation; candidate production-agent code is untracked in a different worktree | `agents/task-d-local-model-integration@41b954c` (clean); untracked files in `agents/project-documentation-review` worktree | No branch dependency is available; workspace code is non-authoritative and could be lost | Commit coherent work on the correct branch; provide build/CTest/export evidence before any dependency pin |
| **Blocker** | Agent's `RuntimeInteractionPort` is a non-injectable value member | `include/agent_kernel/agent/agent.hpp:192` | The Agent cannot consume `RuntimePublicApiAdapter` through its own port; the composition path is the only integration point but is not wired into a production Agent loop | Decide whether to (a) change Agent to hold a `unique_ptr<RuntimeInteractionPort>` or reference, or (b) use the external composition as the integration point and document it explicitly. Either requires a Kernel change or an Agent4NAO-owned wrapper. |
| **Major** | Install/export omits all runtime and composition targets | `CMakeLists.txt:76` — `install(TARGETS agent_kernel agent_kernel_foundation ...)` | Agent4NAO cannot `find_package(AgentKernel)` and link the adapter or composition; a broader export would require a Kernel modification (not authorized) | Either extend `AK_ENABLE_INSTALL` to export the full target set (Kernel change request) or use `FetchContent`/submodule with `add_subdirectory` to build in-tree |
| **Major** | All `agents/*` branches are at the same commit `41b954c` with no delta | `git rev-parse agents/*` → all `41b954c03519a0d1489914e80e64292fb2217eda` | No branch contains any implementation; the branch naming implies work that does not exist in git history | Abandon the branch-per-task convention if no work is committed; or commit the work to the named branches |
| **Major** | No bridge, serialization, watchdog, reconnect, or ROS 2 implementation exists anywhere | Repository-wide search: no `.cpp`, `.hpp`, or `.py` file implements bridge/transport/TLS/TCP socket server/ROS 2/Gazebo/NAOqi | The entire desktop-to-NAO bridge is unbuilt; Stage C/D deliverables have no precedent | Treat bridge as a new audited Stage B/C deliverable; do not infer precedent from the Ollama HTTP client |
| **Major** | Master Ollama code is only a blocking example without cancellation, bounded production conversation, or streaming | `examples/ollama_minimal/ollama_model.cpp` (POSIX socket HTTP client, `poll()`-based) | Cannot serve as a production local-model adapter; no in-flight generation cancellation | Build a provider-neutral desktop chat service with fake-model tests, cancellation, bounded history, timeout normalization |
| **Major** | Candidate production-agent introduces a parallel `model_action` namespace | Untracked: `include/agent_kernel/model_action/model_action.hpp` vs. existing `include/agent_kernel/fwa/model_action.hpp` | Risk of duplicating the Agent-owned action boundary; two `ModelAction` types could cause architecture drift | Resolve before committing: either reuse the existing `ak::agent::ModelAction` or document why a second type is needed |
| Minor | `RuntimePublicApiAdapter` is synchronous and one-shot | `src/runtime_integration/runtime_public_api_adapter.cpp:166` (`runtime_.Run(*session)`) | Physical lifecycle, cancellation, deadlines, and arbitration must live elsewhere (NAO Execution Agent) | Keep the adapter as a synchronous translation boundary; add a desktop-side async wrapper if needed |
| Minor | Architecture documentation states the adapter exists only on `agents/*` branches; `master` already contains it | `Agent4NAO Architecture & Project Boundary Rev1.0.md` §3.2, §19 | The inventory misleads: it understates `master` readiness and overstates branch value | Correct the inventory before pinning a dependency |
| Note | `agent-kernel_1` (Python skeleton) still exists in the workspace alongside the authoritative C++ tree | `/home/liu/workspace/Agentic_Program/AgentRuntimeKernel/agent-kernel_1/` | Could confuse tooling or reviewers into using the wrong tree | Document that `agent-kernel_1` is non-authoritative and should be ignored or archived |

## 8. Recommended next sequence

1. **Desktop-only local chat** — Implement a provider-neutral desktop chat
   service in Python with:
   - conversation session create/terminate
   - local model adapter (Ollama HTTP client with cancellation via
     `HTTPConnection` timeout or `requests` with `ConnectionError` handling)
   - deterministic fake model for tests
   - bounded conversation history (cap on stored turns/characters)
   - timeout and unavailable-provider error normalization
   - cancellation of in-flight generation
   - structured logging without leaking secrets (API keys, tokens)
   
   Do not enable tools or robot actions. Gate: user can complete a local
   conversation with the robot disconnected.

2. **Runtime seam inventory and decision** — Complete:
   - independent CMake/CTest build of `master@5e29011` (36/38 tests expected)
   - export/install gap analysis (which targets Agent4NAO needs vs. what
     `AK_ENABLE_INSTALL` provides)
   - decision: `FetchContent` + `add_subdirectory` (build in-tree) vs.
     installed artifacts (requires Kernel export extension)
   - decision: C++ facade vs. process boundary for the Python ↔ C++ bridge
   - Agent port injection design (value member → pointer/reference)
   
   Pin `master@5e29011` only after this evidence is reviewed.

3. **Typed action simulator** — Define `Stand`, `Walk`, `Stop`, `Observe`
   typed action schemas with:
   - Agent-owned `ModelAction` (reuse `ak::agent::ModelAction` from
     `include/agent_kernel/fwa/model_action.hpp`)
   - fake NAO Execution Agent
   - command/result/event protocol envelopes (versioned JSON)
   - malformed, stale, duplicate, and cancelled command tests

4. **Read-only NAO bridge** — Implement:
   - authenticated TLS session (TLS + pre-shared token)
   - heartbeat/reconnect
   - health and observation events
   - NAO-side command validation
   - read-only `Observe`
   
   Gate: desktop can connect to NAO and receive health/observation data
   without actuator commands.

5. **Supervised actuator access** — Add in the order:
   1. `Stop` (emergency stop must be first and always available)
   2. `Stand`
   3. constrained `Walk`
   
   Only after watchdog implementation and physical safety review by
   TRAE + GLM-5.2.

## 9. Explicit non-recommendations

- **Do not copy Agent-Kernel to NAO.** The NAO Execution Agent is Python 2.7
  + NAOqi-native, not a second Kernel.
- **Do not install ROS 2 on NAO V6.** NAO V6 has no ROS 2 runtime; the ROS 2
  path is the Gazebo simulation path only.
- **Do not install NAOqi on the desktop.** The desktop does not run NAOqi;
  the bridge protocol is the sole desktop-to-NAO path.
- **Do not permit direct model-to-NAOqi execution.** A model response is
  never evidence that a physical operation succeeded; every physical effect
  must go through Agent-owned `ModelAction` → capability → bridge → NAO
  Execution Agent → NAOqi.
- **Do not enable real actuator access before the safety gate.** Physical
  testing is not authorized until watchdog, connection-loss stop, and
  operator procedure are implemented and reviewed.
- **Do not depend on any `agents/*` branch.** All branches are at the same
  baseline commit with zero implementation delta.
- **Do not treat untracked worktree files as a dependency.** The candidate
  production-agent code in `agents/project-documentation-review` is
  non-authoritative and could be lost.
- **Do not bind Python directly to the unfinished C++ target topology.**
  Use a narrow facade or process boundary until the export/install gap is
  resolved.

## 10. Final authorization statement

```text
Architecture Status: DRAFT / PROPOSED
Implementation Status: STAGE A PLANNING ONLY
NAO Actuator Access: NOT AUTHORIZED
Agent-Kernel Modification: NOT AUTHORIZED
```

---

## Appendix: Inspection method

| Step | Method |
|---|---|
| Git state | `git log`, `git branch -a`, `git rev-parse`, `git merge-base`, `git diff --stat`, `git worktree list`, `git status --short --untracked-files=all` on `master` and all `agents/*` worktrees |
| Seam source | Direct `Read` of `runtime_public_api_adapter.hpp/.cpp`, `runtime_interaction_port.hpp`, `runtime_invocation_request.hpp`, `runtime_observation.hpp`, `runtime_submission_result.hpp`, `runtime.h`, `agent.hpp` |
| Build targets | Direct `Read` of `CMakeLists.txt` (root), `src/CMakeLists.txt`, `src/runtime_integration/CMakeLists.txt`, `src/runtime_backed_agent/CMakeLists.txt`, `src/model_to_runtime/CMakeLists.txt`, `src/agent_continuation/CMakeLists.txt`, `runtime/CMakeLists.txt` |
| Ollama experiment | Direct `Read` of `examples/ollama_minimal/ollama_model.hpp/.cpp`, `chat_demo.hpp` |
| ModelAction | Direct `Read` of `include/agent_kernel/fwa/model_action.hpp` |
| Bridge/transport/ROS 2 | `Grep` for `bridge|gateway|transport|TLS|TCP|socket|serializ|ROS|ros2|rclpy|gazebo|naoqi` across all `.cpp/.hpp/.h/.py/.cmake/.txt` files |
| Task-D candidate | `git status` on `agents/task-d-local-model-integration` and `agents/project-documentation-review` worktrees |
| Agent4NAO docs | Direct `Read` of all 6 documents in `Agent4NAO/docs/` |
| Build/test | **Not executed** — this is a read-only review; no CMake configure, build, or CTest was run |
