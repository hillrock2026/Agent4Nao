# Agent4NAO Product Definition & Capability Roadmap Rev1.0

## 1. Product definition

Agent4NAO is a desktop-first embodied-agent software system for NAO V6. It
combines desktop computation and local-model conversation with a constrained
NAO-side execution agent and native NAOqi control.

It is not:

- a second general-purpose Agent-Kernel;
- an LLM-to-motor command pipeline;
- a ROS 2 installation for NAO V6;
- a complete autonomous robotics platform;
- a gait-research-only repository.

Its product value is the controlled path from human conversation to useful,
observable, and eventually safe robot behavior:

```text
User
  -> desktop conversation
  -> Agent interpretation
  -> typed capability/action
  -> NAO Execution Agent
  -> NAOqi
  -> sensors/actuators
  -> observation
  -> desktop Agent context and conversation
```

The first two product pillars are:

1. **Conversation:** a user can talk with Agent4NAO through a desktop local
   model, even when the robot is disconnected.
2. **Movement:** a reproducible and evaluated NAO gait can be generated,
   executed, and improved, first in simulation and later on the real robot.

Other capabilities are extension surfaces, not first-release commitments.

## 2. Deployment model

### Desktop

The desktop runs:

- Agent4NAO;
- Agent-Kernel as an external desktop dependency;
- local model runtime: Ollama + Qwen2.5-Instruct 7B Q4_K_M;
- conversation and high-level Agent decisions;
- model/provider adapter;
- high-level task and capability orchestration;
- real-NAO network client;
- ROS 2/Gazebo simulation path.

### NAO V6

The robot runs:

- Python 2.7;
- NAOqi 2.8;
- a small NAO Execution Agent;
- watchdog and safety handling;
- local resource arbitration;
- versioned command/event endpoint;
- native NAOqi access to sensors, actuators, balance, and speech.

NAO V6 does not run ROS 2. The real-robot path is therefore not a ROS 2
path:

```text
Desktop Agent4NAO -> TLS JSON bridge -> NAO Execution Agent -> NAOqi
```

ROS 2 is reserved for the Gazebo simulation target.

## 3. NAO V6 physical capability inventory

The following inventory is the product-level starting point and must be
confirmed against the target NAO V6 unit and NAOqi 2.8 API before hardware
authorization.

### 3.1 Sensors

| Sensor group | Approximate hardware | Product use |
|---|---|---|
| Cameras | Two head cameras | Later vision, operator observation, environment perception |
| Microphones | Four-microphone array | User speech input and sound direction |
| Inertial unit | Accelerometer and gyroscope | Balance, fall detection, motion evaluation |
| Foot force | Foot pressure/FSR sensors | Contact, support distribution, gait evaluation |
| Foot bumpers | Tactile collision sensors | Contact and safety stop |
| Head tactile | Multiple head touch zones | User interaction and simple commands |
| Hand tactile | Hand touch sensors | Interaction and contact feedback |
| Sonar | Forward obstacle sensing | Later obstacle awareness |
| Joint feedback | Position and actuator state | Motion verification and safety |
| Battery/health | Power and device state | Runtime supervision and safe shutdown |

### 3.2 Actuators and outputs

| Actuator/output | Product use |
|---|---|
| 25-joint body | Posture, gait, gestures, manipulation primitives |
| Speakers | Speech and alerts |
| Head/ear/eye/chest LEDs | State, attention, emotion, operator feedback |
| NAOqi motion/balance services | Low-level safe motion and posture control |

The initial product must not expose all physical capabilities as unrestricted
Agent tools. Each capability needs a typed schema, safety policy, timeout,
resource ownership, and observation/result mapping.

## 4. Product capability layers

### Layer A — Conversation and interaction

Capabilities:

- text conversation;
- speech input/output integration later;
- session memory bounded by desktop policy;
- user confirmation for physical actions;
- status reporting and error explanation.

### Layer B — Observation and safety

Capabilities:

- robot connection and health;
- battery and system state;
- posture/joint state summary;
- IMU/balance/fall state;
- foot contact and pressure summary;
- tactile and bumper events;
- emergency stop;
- operator-visible execution status.

### Layer C — Motion primitives

Capabilities:

- stop;
- stiffness release;
- stand;
- sit/posture transition;
- constrained walk command;
- head/LED/speech expression.

### Layer D — Gait

Capabilities:

- trajectory representation;
- deterministic baseline gait;
- simulation evaluation;
- gait parameter optimization;
- diffusion-based trajectory generation;
- supervised real-robot evaluation.

### Layer E — Future extensions

Potential later capabilities:

- vision-assisted perception;
- obstacle awareness;
- gesture and social interaction;
- navigation;
- object interaction;
- multimodal memory;
- learning from demonstrations.

These are intentionally not part of the first two milestones.

## 5. Capability priority

### Priority P0 — Required foundation

- desktop local-model conversation;
- desktop/NAO connection health;
- typed command/event protocol;
- NAO-side watchdog;
- emergency stop;
- observation envelope;
- fake NAO Execution Agent;
- deterministic test and audit path.

### Priority P1 — First product milestone: conversation

- text chat with Ollama/Qwen;
- bounded context;
- model timeout/cancellation;
- provider failure handling;
- user confirmation before robot actions;
- disconnected-robot operation;
- optional NAO health observation in conversation.

The P1 acceptance statement is:

> A user can converse with Agent4NAO on the desktop using the local model,
> receive reliable responses, and see a clear robot-unavailable state without
> any unsafe hardware side effect.

### Priority P2 — Second product milestone: gait

- Gazebo NAO target;
- deterministic trajectory interface;
- stand/stop safety primitives;
- gait evaluation metrics;
- baseline gait;
- parameter optimization;
- experiment recording;
- only later diffusion-based optimization.

The P2 acceptance statement is:

> A configured gait trajectory can be evaluated repeatably in Gazebo, compared
> against a baseline, and rejected when it violates safety or validity limits.

### Priority P3 — Supervised real-robot execution

- read-only NAO bridge;
- stop and safety operations;
- stand;
- restricted walking;
- real-robot gait evaluation;
- operator procedure and rollback.

### Priority P4 — Extension capabilities

- speech-first interaction;
- vision;
- navigation;
- manipulation;
- social behavior;
- multimodal learning.

## 6. Implementation sequence

### Phase 0 — Product and hardware confirmation

Deliver:

- confirm NAO V6 sensor/actuator inventory on the actual unit;
- map each desired capability to NAOqi APIs;
- record unavailable or firmware-dependent APIs;
- select common observation schemas for Gazebo and real NAO;
- define safety ownership and physical operator procedure.

No actuator implementation is authorized until this phase records evidence.

### Phase 1 — Desktop conversation product

Deliver:

- provider-neutral local model adapter;
- Ollama/Qwen configuration;
- desktop conversation session;
- bounded context and message history;
- timeout/cancellation;
- deterministic fake model;
- logs and runbook;
- no physical tools enabled by default.

This phase must not wait for the unfinished Agent↔Runtime seam if it can
operate behind a temporary Agent4NAO-owned desktop boundary. The seam decision
must remain recorded as a separate dependency risk.

### Phase 2 — Action and observation simulation

Deliver:

- typed ModelAction;
- `Observe`, `Stop`, `Stand`, and constrained `Walk` schemas;
- Fake Execution Agent;
- command/result/event envelopes;
- invalid, stale, duplicate, timeout, and cancellation tests;
- user confirmation policy.

### Phase 3 — Read-only real-NAO integration

Deliver:

- TLS/token session;
- heartbeat and reconnect;
- health and observation events;
- battery/posture/fall/contact summaries;
- no actuator commands.

### Phase 4 — Safe motion primitives

Enable capabilities in this order:

```text
Stop -> stiffness release -> Stand -> constrained Walk
```

Each capability requires independent safety evidence. The model never receives
authority to bypass the NAO-side validator, watchdog, or resource arbiter.

### Phase 5 — Gait baseline and optimization

Deliver:

- common trajectory contract;
- deterministic baseline;
- Gazebo evaluation;
- metrics and experiment storage;
- parameter optimization;
- sim-to-real comparison plan.

### Phase 6 — Diffusion gait

Add diffusion only as a trajectory-generation/optimization component behind the
gait capability. It must not become a direct torque or actuator policy without
a new architecture review.

## 7. Sensor-to-capability roadmap

| Sensor | First use | Later use |
|---|---|---|
| Joint feedback | Verify commands and posture | Closed-loop gait analysis |
| IMU | Fall/balance safety | Gait stability metrics |
| Foot FSR | Contact and support check | Trajectory optimization reward |
| Foot bumpers | Emergency stop trigger | Contact-aware behavior |
| Battery/health | Availability and shutdown | Long-running experiment management |
| Head/hand tactile | Simple user confirmation | Social interaction |
| Microphones | Later speech input | Sound localization |
| Cameras | Deferred | Vision and environment perception |
| Sonar | Deferred | Obstacle awareness/navigation |

This ordering deliberately uses low-bandwidth, safety-relevant signals before
high-cost vision and open-ended autonomy.

## 8. Product-level non-goals

- Put Agent-Kernel on NAO V6.
- Put ROS 2 on NAO V6.
- Install NAOqi on the desktop.
- Let model text directly invoke NAOqi.
- Build navigation before conversation and gait foundations.
- Optimize gait before a deterministic baseline exists.
- Add vision, SLAM, reinforcement learning, or multi-agent behavior to the
  first release.
- Treat every NAO sensor as a first-class tool immediately.

## 9. Definition of success

Agent4NAO v0 is successful when:

1. A desktop user can hold a reliable local-model conversation.
2. The robot can be disconnected without breaking conversation.
3. A typed action cannot bypass Agent authorization.
4. NAO-side watchdog and stop behavior are deterministic.
5. Observations return through a versioned bridge.
6. A deterministic gait can be evaluated repeatedly in Gazebo.
7. Every later capability has a clear extension boundary and does not require
   redesigning the product core.

## 10. Authorization

This document defines the product and capability roadmap. It does not
authorize physical actuator access.

```text
Product Status: DEFINED FOR DISCUSSION
First Milestone: DESKTOP LOCAL-MODEL CONVERSATION
Second Milestone: GAZEBO-FIRST GAIT BASELINE AND OPTIMIZATION
NAO Actuator Access: NOT AUTHORIZED
Agent-Kernel Modification: NOT AUTHORIZED
```
