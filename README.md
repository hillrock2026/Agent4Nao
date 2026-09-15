# Agent4NAO

Agent4NAO is the NAO embodied-agent application layer built on top of the
existing Agent-Kernel project. It owns NAO capabilities, ROS 2 integration,
Gazebo Harmonic integration, and gait research; it does not replace or copy
Agent-Kernel.

## Current status

**Phase 1 (desktop local-model conversation) is implemented.** A user can run a
bounded desktop conversation with a local Ollama model through the Agent4NAO
package (`src/agent4nao`), with a deterministic fake model for tests.

**Phase 2 (typed action and observation simulation) is implemented.** The
Agent4NAO-owned action contract (`src/agent4nao/action`) and a deterministic
Fake NAO Execution Agent (`src/agent4nao/execution`) prove the authorization
boundary (`ModelResult != typed action`) without any real NAO, ROS 2, NAOqi,
network, or Agent-Kernel dependency. `ActionSession` composes the Phase 1
conversation with an optional execution target.

No robot, ROS 2, NAOqi, or actuator code is present in any phase.

The authoritative boundary document is
[`docs/Agent4NAO Architecture & Project Boundary Rev1.0.md`](docs/Agent4NAO%20Architecture%20%26%20Project%20Boundary%20Rev1.0.md);
the Phase 2 schema reference is
[`docs/Agent4NAO Phase 2 Schema & Execution Simulation Rev1.0.md`](docs/Agent4NAO%20Phase%202%20Schema%20%26%20Execution%20Simulation%20Rev1.0.md);
the initialization decision is recorded in
[`docs/Agent4NAO Project Initialization Decision Record Rev1.0.md`](docs/Agent4NAO%20Project%20Initialization%20Decision%20Record%20Rev1.0.md).

## Phase 1 — desktop local conversation

```bash
python3 -m pip install -e .        # or: PYTHONPATH=src python3 -m agent4nao
ollama pull qwen2.5:7b-instruct-q4_K_M
agent4nao-chat                     # interactive; /exit to quit
```

See [`docs/Agent4NAO Phase 1 Desktop Conversation Runbook.md`](docs/Agent4NAO%20Phase%201%20Desktop%20Conversation%20Runbook.md)
for setup, configuration, test, and timeout/cancellation semantics.

## Phase 2 — typed action and observation simulation

```text
ModelResult -> explicit authorization -> typed ActionRequest
  -> Fake NAO Execution Agent -> ActionResult/Observation
```

The simulation capabilities are `Observe`, `Stop`, `Stand`, and constrained
`Walk`. Free-form model text never executes; `ActionSession.authorize` is the
only execution path. See the Phase 2 schema reference for the full contract.

```python
from agent4nao.conversation import ActionSession
from agent4nao.execution import FakeNAOExecutionAgent
from agent4nao.model.fake import FakeModelProvider

# The fake model is scripted to emit a strict proposal JSON. Free-form text
# (e.g. "walk forward") would parse to proposal=None and never execute.
model = FakeModelProvider(fixed_response='{"capability": "observe", "parameters": {}}')
session = ActionSession(model, execution_agent=FakeNAOExecutionAgent())

turn = session.send("what do you observe?")   # parses the model output only
assert turn.proposal is not None              # a ProposedAction, not yet authorized
assert turn.result is None                    # send() never executes

outcome = session.authorize(turn.proposal)    # explicit authorization -> execution
assert outcome.result.status.value == "completed"
assert outcome.observation.summary["battery_pct"] == 87
```

Without an execution agent, `authorize` still builds the typed request but
returns an explicit rejection (`status` `"rejected"`, `error_category`
`"target_unavailable"`) — it never fabricates a success or observation.

Run the tests (no Ollama, network, or GPU required):

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
```

## Later loops

```text
Agent-Kernel -> Agent4NAO capability -> ROS 2 -> Gazebo NAO
                                             ^          |
                                             +-- observation
```

The first robot capability set is intentionally limited to `Stand`, `Walk`,
`Stop`, and `Observe`; it is not implemented in Phase 1.

## Development prerequisite

Agent-Kernel is an external dependency. Do not copy its source into this
repository. The authoritative Agent-Kernel is the **C++20 / CMake** project at
`../agent-kernel` (remote `git@github.com:hillrock2026/Agent-Kernel.git`),
built with GCC 13 + GTest and verified at 36/36 CTest tests. It is not a
Python package; `pip install` does not apply.

The implementation phase must consume Agent-Kernel from a pinned, immutable
Git commit through CMake (`FetchContent`, a submodule, or installed artifacts)
before reproducible builds are claimed. The exact mechanism and the Agent4NAO
language/build split are Stage 0 decisions recorded in
[`docs/Agent4NAO Project Initialization Decision Record Rev1.0.md`](docs/Agent4NAO%20Project%20Initialization%20Decision%20Record%20Rev1.0.md).

# Agent4Nao

