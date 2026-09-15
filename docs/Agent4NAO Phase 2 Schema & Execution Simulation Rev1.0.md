# Agent4NAO Phase 2 Schema & Execution Simulation Rev1.0

> Authoritative schema and semantics reference for Phase 2 (Typed Action and
> Observation Simulation). Companion to the delivery report
> `Agent4NAO Phase 2 Delivery Report Rev1.0.md`.

## 1. Goal and non-goals

Phase 2 proves the desktop Agent authorization boundary before any transport,
ROS 2, NAOqi, or actuator integration:

```text
User message -> ModelResult -> explicit Agent authorization
  -> typed Agent4NAO action -> Fake NAO Execution Agent
  -> typed result/observation -> desktop session/event state
```

Core invariants:

```text
ModelResult != Typed Action
Free-form assistant text != executable action
Typed Action = explicitly authorized Agent-owned value
Fake Execution Agent != real NAO
```

Non-goals: real NAO V6, Python 2.7, NAOqi, ROS 2 / `rclpy`, Gazebo, TLS/network
bridge, real actuators/sensors, real watchdog, gait, Agent-Kernel modification,
a parallel `ak::agent::ModelAction`, general natural-language tool calling, or
any direct model-output-to-action path.

## 2. Action contract ownership

The action contract is owned by Agent4NAO and lives at:

```text
src/agent4nao/action/       # schema, parameters, validation, authorization
src/agent4nao/execution/    # Fake NAO Execution Agent + clocks
```

It is explicitly **not** an Agent-Kernel `ModelAction`, a NAOqi command, or a
final network protocol. It is a desktop simulation contract that may later be
mapped to a real NAO Execution Agent, but never executes a real robot.

## 3. Request schema (`ActionRequest`)

Immutable (`frozen`) dataclass, validated in `__post_init__`. It cannot be
constructed in an invalid form; the sanctioned constructors are
`build_request` and `request_from_dict`.

| Field | Type | Rules |
|---|---|---|
| `schema_version` | `str` | must equal `"1.0"`, else `SchemaVersionError` |
| `request_id` | `str` (UUID) | strict UUID format |
| `session_id` | `str` (UUID) | strict UUID format |
| `turn_id` | `str` (UUID) | strict UUID format |
| `capability` | `Capability` | `observe/stop/stand/walk` |
| `parameters` | typed value object | must match `capability` |
| `created_at` | `float` | finite wall-clock epoch |
| `ttl_seconds` | `float` | `(0, TTL_MAX_SECONDS]` |
| `priority` | `Priority` | `EMERGENCY` iff `stop` |
| `idempotency_key` | `str` (UUID) | strict UUID format |

Constants: `SCHEMA_VERSION="1.0"`, `TTL_MAX_SECONDS=60.0`,
`DEFAULT_TTL_SECONDS=5.0`, `DEFAULT_QUEUE_CAPACITY=2`.

Validation is strict: unknown fields are rejected, `bool`/`NaN`/`inf` are
rejected for all numeric fields, and UUIDs must be canonical. Serialization
(`to_dict`/`to_json`) is deterministic and never exposes shared mutable nested
references.

## 4. Typed parameters

| Capability | Parameters | Constraints |
|---|---|---|
| `Observe` | `ObserveParameters(fields)` | `fields=None` -> full summary; subset restricted to `battery_pct`, `posture`, `fall_state`; unknown/duplicate fields rejected |
| `Stop` | `StopParameters()` | no parameters accepted |
| `Stand` | `StandParameters()` | no parameters accepted |
| `Walk` | `WalkParameters(distance_m, speed)` | `distance_m in (0, 1.0]`, `speed in (0, 0.5]`; arbitrary dicts rejected |

`Walk` is a constrained typed request; free text or arbitrary dictionaries
never pass.

## 5. Result and observation schema

`ActionResult` fields: `request_id`, `status`, `error_category`, `reason`,
`started_at`, `completed_at`, `duration_seconds`, `payload`, `observation`.
Every result is correlated to its request by `request_id`.

`Observation` fields: `request_id`, `observed_at`, `capability`, `summary`
(deterministic, canonical key order).

Allowed statuses:

```text
accepted | running | completed | rejected | expired | cancelled | failed
```

`ErrorCategory`: `none`, `invalid_parameters`, `schema_incompatible`,
`unknown_request`, `duplicate`, `idempotency_conflict`, `stale`, `cancelled`,
`target_unavailable`, `resource_conflict`, `queue_full`, `internal`.

## 6. State machine

Legal transitions:

```text
new        -> accepted
accepted   -> running | expired | cancelled | rejected
running    -> completed | cancelled | failed
```

Terminal states (cannot re-execute): `completed`, `rejected`, `expired`,
`cancelled`, `failed`.

Staleness (`now > created_at + ttl_seconds`) is checked at submission, at
dequeue, and before execution. The comparison is strict: when
`now == created_at + ttl_seconds` the request is still valid (not expired);
only `now > created_at + ttl_seconds` marks it expired.

## 7. Idempotency and duplication

- **Duplicate replay**: same `request_id` with identical content -> return the
  cached result with `status` = original status and `error_category=duplicate`
  (no new `duplicate` status is introduced). If the original is still
  `accepted`/`running`, the current state is returned with `duplicate`.
- **Idempotency conflict** (`idempotency_conflict`): same `request_id` with
  different content, or same `(session_id, idempotency_key)` with a different
  `request_id` -> explicit `rejected` result; the original request is never
  overwritten.
- The idempotency key is scoped by `(session_id, idempotency_key)`.

### Expired requests and idempotency

`expired` is a terminal state and still occupies its idempotency key. The key
cannot represent a new retry action:

- Re-submitting the **identical request** (same `request_id` and content)
  returns the cached `expired` result with `error_category=duplicate`; it is
  never executed a second time.
- Reusing the same `(session_id, idempotency_key)` with a **different
  `request_id`** is an `idempotency_conflict` (`rejected`), not a duplicate.
- A business retry must therefore issue a new `idempotency_key` and, per
  request semantics, a new `request_id`.

## 8. Priority, queue, and resource semantics

- `Stop` is `EMERGENCY`; all other capabilities are `NORMAL`. The constructor
  enforces `EMERGENCY` only for `stop`.
- `queue_capacity` counts **waiting** motion requests; the running motion is
  not counted. A second motion while one runs is queued (`accepted`).
- `queue_capacity == 0` and motion busy -> `resource_conflict`.
- Queue full -> `queue_full`.
- `Stop` preempts: the running motion and every queued motion each receive an
  explicit `cancelled` result; the queue is cleared.

This is a simulation of future NAO-side safety rules, not a claim of real NAO
safety.

## 9. Authorization boundary

```text
ModelResult.payload (free-form assistant text)
  -> parse_proposal(text) -> ProposedAction | None   (strict; free text -> None)
  -> authorize(proposed)  -> AuthorizedAction        (validates + types params)
  -> build_request_from_authorized -> ActionRequest
  -> FakeNAOExecutionAgent.submit -> ActionResult
```

There is no function that maps a `ModelResult` or arbitrary string directly to
an `ActionRequest`. `parse_proposal` is the only text-to-proposal path and
returns `None` for free text; `authorize` is the only path from proposal to a
validated typed action.

## 10. Fake NAO Execution Agent

In-process, deterministic, with injectable `Clock`/`FakeClock`. Supports
accept/run/complete/reject/expire/cancel/fail/duplicate/idempotency-conflict/
target-unavailable/bounded-queue/resource-conflict. It imports no `naoqi`,
`rclpy`, ROS 2, `socket`/`ssl`, Python 2.7, Agent-Kernel, or hardware driver.

Clocks: `now()` (wall-clock epoch) drives `created_at`/`started_at`/
`completed_at` and TTL; `monotonic()` drives `duration_seconds`. `FakeClock`
advances both together for deterministic tests.

## 11. Conversation integration

`ActionSession` composes a Phase 1 `ConversationSession` (unchanged) with an
optional execution agent:

- `send(text)` -> `ActionTurn`: pure text turn plus a strictly parsed
  `proposal`; it **never executes**.
- `authorize(proposal)` -> `ActionTurn`: explicit authorization builds the
  typed request and submits it.

When no execution agent is configured:

```text
ActionRequest 可以构建；
但不会发送到不存在的 Execution Agent；
不会进入执行队列；
不会被记录为 accepted/completed。
```

`authorize` still builds the typed request (proving the action is well-formed)
but returns an explicit `rejected`/`target_unavailable` result — no fake
success and no observation.

## 12. Known limitations

- Desktop simulation only; no real NAO, NAOqi, ROS 2, Gazebo, or network bridge.
- No general natural-language tool calling; authorization is explicit and
  programmatic.
- No real safety implementation; priority/queue/TTL semantics are simulations.
- No persistence or multi-process execution; the fake agent is in-process and
  single-threaded.

## 13. Future NAO bridge compatibility assumptions

- The versioned envelope (`schema_version`) maps to a future TLS JSON bridge.
- `priority`, `idempotency_key`, and `ttl_seconds` semantics carry through
  unchanged.
- `Observation` structure is extensible; the desktop contract and the NAO-side
  contract share names and semantics.
- These assumptions are recorded for future mapping, not implemented here.
