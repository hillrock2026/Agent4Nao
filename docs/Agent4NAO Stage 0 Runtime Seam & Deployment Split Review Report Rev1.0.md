# Agent4NAO Stage 0 Runtime Seam & Deployment Split Review Report Rev1.0

> Independent read-only review executed against the review prompt in
> `Agent4NAO Stage 0 Runtime Seam & Deployment Split Review Prompt Rev1.0.md`.
> No source files were modified.

## 1. Executive verdict

**NO-GO** for consuming the current Agent-Kernel state as an Agent4NAO
production/runtime dependency. The C++20/CMake Runtime seam is present on
`master`, but the dependency is not yet a complete exported/installable
artifact and was not independently built during this read-only review. The
named Task-D branch has no Task-D implementation commit. No NAO bridge,
protocol implementation, ROS 2 package, or NAO safety evidence is currently
available.

Desktop-only local chat remains a feasible next milestone.

## 2. Repository evidence

| Ref/worktree | Commit | Evidence | Status |
|---|---|---|---|
| `master` | `5e290116c17e76fc5d95802eebc6f724668796ac` | `RuntimePublicApiAdapter`, runtime-backed/model-to-runtime composition | Implemented source and CMake targets |
| `master` | `5e29011` | `examples/ollama_minimal/*`, `tests/ollama_minimal/*` | Example/demo and fixture test, not production chat |
| `agents/agent-development-feedback` | `41b954c03519a0d1489914e80e64292fb2217eda` | Same baseline | No branch-specific delta |
| `agents/agent-kernel-ollama-minimal-experiment` | `41b954c03519a0d1489914e80e64292fb2217eda` | Same baseline | No branch-specific delta |
| `agents/project-documentation-review` | `41b954c03519a0d1489914e80e64292fb2217eda` | Untracked production-agent/provider/model-action files | Uncommitted and non-authoritative |
| `agents/task-d-local-model-integration` | `41b954c03519a0d1489914e80e64292fb2217eda` | No Task-D implementation files in ref | Task-D claim absent |
| `agents/task-e-preconditions-setup-commands` | `41b954c03519a0d1489914e80e64292fb2217eda` | Documentation-only dirty state | No implementation delta |

## 3. Agent↔Runtime seam

- `RuntimeInteractionPort` is a contract whose default operations reject
  submission or return failure observations.
- A concrete `RuntimePublicApiAdapter` exists in `master` and the listed
  branches at:
  - `include/agent_kernel/runtime_integration/runtime_public_api_adapter.hpp`
  - `src/runtime_integration/runtime_public_api_adapter.cpp`
- It is production C++ source rather than a mock. It registers capabilities,
  runs Runtime, and maps invocation results.
- It requires C++20/CMake and Runtime headers/libraries.
- Its current API is synchronous and does not provide cancellation, deadline,
  streaming, or remote transport semantics.
- Existing source tests cover related areas, but this review did not run a
  build or CTest.
- Installation/export is incomplete: default install/export does not expose
  the runtime/integration/composition targets required by Agent4NAO.

**Recommendation:** consume only a reviewed immutable C++ commit through a
narrow Agent4NAO-owned C++ facade or separate process. Do not bind Python
directly to the unfinished target topology.

## 4. Task-D production-agent status

The named `agents/task-d-local-model-integration` ref contains no Task-D
implementation. A different dirty worktree contains untracked proposed
production-agent, OpenAI-compatible provider, and structured model-action
files.

The proposed composition is directionally correct:

```text
ModelResult -> ParseModelAction -> capability validation
             -> RuntimeInteractionPort -> RuntimeObservation
```

However, it is not an immutable branch dependency, does not compose the
established `Agent`, `Planner`, concrete `RuntimePublicApiAdapter`, or real
Tool implementation, and its tests use fake Runtime and ToolRegistry
components. It also lacks bounded prompt/context sizes and cancellation.

**Conclusion:** documented/in-progress workspace code, not a buildable
production dependency.

## 5. Recommended language/build split

| Component | Recommendation |
|---|---|
| Desktop Agent4NAO | Python for UX, local-model integration, and orchestration; explicit typed action authorization |
| Agent-Kernel | C++20/CMake desktop-only dependency, pinned by immutable commit |
| ROS 2/Gazebo | Python 3.12 / ROS 2 Jazzy simulation process; never on NAO |
| NAO Execution Agent | Python 2.7 + NAOqi-native, bounded and deterministic |
| Bridge | Version-neutral JSON envelopes over TLS-wrapped TCP; validate TLS/cipher/certificate support on NAO |

The pre-shared token should be an application-level authenticated field
inside TLS, not a substitute for transport protection.

## 6. Stage 0 decisions

| Decision | State | Evidence still required |
|---|---|---|
| NAO V6 / NAOqi 2.8 / Python 2.7 | Decided/documented | Device version and Python/SSL capability capture |
| Ollama + Qwen2.5-Instruct 7B Q4_K_M | Decided/documented | Exact tag/hash, RAM/VRAM, context limit, local endpoint smoke test |
| Kernel dependency commit/mechanism | Blocked | Immutable reviewed commit and reproducible build |
| Runtime seam selection | Blocked | Export/install decision, build/CTest logs, API compatibility review |
| Desktop bridge shape | Blocked | C++ facade vs process boundary and failure model |
| JSON/TLS schema and limits | Proposed | Schema plus idempotency/TTL/cancel/heartbeat/backpressure tests |
| ROS 2 simulation package | Missing | Package, launch files, Gazebo evidence, common observation mapping |
| NAO watchdog/operator safety gate | Missing | Device test evidence and supervised physical-stop procedure |

## 7. Findings and containment

| Severity | Finding | Containment |
|---|---|---|
| Blocker | Task-D branch has no implementation commit; candidate code is untracked elsewhere | Commit coherent work on the correct branch and provide build/CTest/export evidence |
| Major | Architecture documentation misstates adapter availability as agents-only; `master` already contains it | Correct the inventory before pinning a dependency |
| Major | No bridge, serialization, watchdog, reconnect, or ROS 2 implementation exists | Treat bridge as a new audited Stage B/C deliverable |
| Major | Master Ollama code is only a blocking example without cancellation or bounded production conversation behavior | Build a provider-neutral desktop chat service with fake-model tests |
| Major | Proposed ProductionAgent lacks context/prompt bounds and real adapter integration | Add explicit bounds and test against the real adapter after immutable submission |
| Note | RuntimePublicApiAdapter is synchronous and one-shot | Keep physical lifecycle, cancellation, deadlines, and arbitration in NAO Execution Agent |

## 8. Recommended next sequence

1. Implement desktop-only local chat with cancellation, bounded history,
   timeout/error normalization, redacted logs, and deterministic fake-model
   tests. Do not enable tools.
2. Complete the Runtime seam inventory and decide whether to pin
   `master@5e29011` only after independent CMake/CTest/export evidence.
3. Define typed `Stand`, `Walk`, `Stop`, and `Observe` actions with a fake
   Execution Agent.
4. Implement a read-only NAO bridge with versioned envelopes, TLS/token
   authentication, heartbeat, TTL, idempotency, reconnect, bounded queues,
   audit IDs, and `Observe`.
5. Add supervised actuator access in the order `Stop`, `Stand`, constrained
   `Walk`, only after watchdog and physical safety review.

## 9. Explicit non-recommendations

- Do not copy Agent-Kernel to NAO.
- Do not install ROS 2 on NAO V6.
- Do not install NAOqi on the desktop.
- Do not permit direct model-to-NAOqi execution.
- Do not enable real actuator access before the safety gate.

## 10. Authorization

```text
Architecture Status: DRAFT / PROPOSED
Implementation Status: STAGE A PLANNING ONLY
NAO Actuator Access: NOT AUTHORIZED
Agent-Kernel Modification: NOT AUTHORIZED
```
