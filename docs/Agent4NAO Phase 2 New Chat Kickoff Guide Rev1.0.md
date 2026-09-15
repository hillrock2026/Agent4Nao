# Agent4NAO Phase 2 New Chat Kickoff Guide Rev1.0

> 将本文件内容作为新 Chat 的首条指导发送给 OpenCode + DeepSeek。

## 1. 角色

你是 OpenCode + DeepSeek，负责实现 Agent4NAO Phase 2：

```text
Typed Action and Observation Simulation
```

项目负责人负责架构、范围、风险和阶段授权。TRAE + GLM-5.2 负责独立
评审代码和文档。你负责实现和测试，但不得自行扩大范围。

## 2. 已完成基线

Agent4NAO Phase 1 已经通过 TRAE + GLM-5.2 最终评审：

```text
Phase 1 Status: ACCEPTED
Desktop Conversation: ACCEPTED
```

Phase 1 已实现：

- 桌面本地模型对话；
- provider-neutral `ModelProvider`；
- Ollama/Qwen 配置；
- Fake Model；
- bounded history/context；
- timeout/cancellation；
- structured logging；
- CLI；
- 51/51 测试通过；
- 无 Agent-Kernel、ROS 2、NAOqi 或机器人动作路径。

Phase 1 的主要文档：

1. `docs/Agent4NAO Product Definition & Capability Roadmap Rev1.0.md`
2. `docs/Agent4NAO Phase 1 Accepted & Phase 2 Execution Plan Rev1.0.md`
3. `docs/Agent4NAO Phase 1 Desktop Conversation Runbook.md`
4. `docs/Agent4NAO Architecture & Project Boundary Rev1.0.md`
5. `README.md`
6. `pyproject.toml`

开始工作前必须阅读这些文档以及现有 `src/agent4nao` 和 `tests`。

## 3. Phase 2 目标

Phase 2 不是连接真实 NAO，而是证明桌面端的 Agent 授权边界：

```text
User message
  -> ModelResult
  -> explicit Agent authorization
  -> typed Agent4NAO action
  -> Fake NAO Execution Agent
  -> typed result/observation
  -> desktop session/event state
```

核心不变量：

```text
ModelResult != Typed Action
Free-form assistant text != executable action
Typed Action = explicitly authorized Agent-owned value
Fake Execution Agent != real NAO
```

## 4. 当前授权边界

本 Chat 只授权桌面端 Phase 2 仿真实现：

```text
Phase 2 implementation: AUTHORIZED ONLY FOR DESKTOP SIMULATION
```

明确禁止：

- 连接 NAO V6；
- 编写 Python 2.7；
- 编写 NAOqi；
- 编写 ROS 2 或 `rclpy`；
- 编写 Gazebo；
- 编写 TLS/network bridge；
- 写入真实执行器；
- 访问真实传感器；
- 实现真实 watchdog；
- 实现步态生成或优化；
- 修改、复制、fork Agent-Kernel；
- 修复 `RuntimePublicApiAdapter`；
- 引入 Agent-Kernel 依赖；
- 创建第二个 Kernel；
- 创建未经批准的 `ak::agent::ModelAction` 平行实现；
- 让模型输出直接触发 action。

## 5. Action contract 归属

由于 Agent-Kernel 的 Agent↔Runtime seam 尚未解决，本阶段使用明确归属
Agent4NAO 的临时 action contract。

建议放置在实际边界包中，例如：

```text
src/agent4nao/action/
src/agent4nao/execution/
```

名称和文档必须明确：

- 这是 Agent4NAO Phase 2 simulation contract；
- 不是 Agent-Kernel `ModelAction`；
- 不是 NAOqi 命令；
- 不是网络协议最终版本；
- 后续可映射到 NAO Execution Agent，但当前不执行真实机器人。

## 6. 初始模拟能力

只实现四个模拟 capability：

```text
Observe
Stop
Stand
Walk
```

其中 `Walk` 必须是受约束的 typed request，不允许任意自由文本或任意
字典直接通过。

这些能力只能由 Fake NAO Execution Agent 模拟，不得调用任何外部服务。

## 7. Request schema

每个 action request 至少包含：

- schema/protocol version；
- request id；
- session id；
- originating turn/action id；
- capability name；
- typed parameters；
- creation timestamp；
- deadline/TTL；
- priority；
- idempotency key。

需要定义：

- 必填字段；
- 字段类型；
- 默认值；
- 合法范围；
- 未知字段策略；
- schema version 不兼容策略；
- 序列化/反序列化行为。

## 8. Result and observation schema

每个 action result 至少包含：

- request id；
- status；
- error category/reason；
- start timestamp；
- completion timestamp；
- duration；
- result payload；
- observation summary。

允许的状态：

```text
accepted
running
completed
rejected
expired
cancelled
failed
```

所有结果都必须可关联到原始 request。未知 request、重复 request、过期
request 和 schema 不兼容必须产生明确结果，而不是静默忽略。

## 9. Fake NAO Execution Agent

实现一个进程内、确定性的 Fake Execution Agent，支持：

- 接受请求；
- 执行中；
- 完成；
- 拒绝；
- 过期；
- 取消；
- 失败；
- 重复/幂等请求；
- target unavailable。

它不能导入或依赖：

- `naoqi`；
- `rclpy`；
- ROS 2；
- socket/TLS；
- Python 2.7；
- Agent-Kernel；
- 硬件驱动。

## 10. 安全语义模拟

模拟未来 NAO Execution Agent 的约束：

- 参数校验；
- stale/expired request rejection；
- duplicate/idempotency；
- cancellation；
- resource conflict；
- bounded queue/backpressure；
- unavailable target；
- emergency stop priority。

必须保证：

```text
Stop priority > Walk/Stand priority
```

但不要声称这已经是 NAO 的真实安全实现。

## 11. 与 Phase 1 对话集成

只增加明确的仿真边界，保持原有纯文本对话可用。

必须区分：

```text
assistant text
proposed action
authorized action
fake execution result
observation
rejection/failure explanation
```

Fake Execution Agent 不存在时：

- 普通对话仍然工作；
- action 请求必须得到明确的 unavailable/rejected 结果；
- 不得产生假成功；
- 不得直接访问任何硬件。

Phase 2 不要求实现通用自然语言 tool calling。可先使用显式、可测试的
授权路径验证架构不变量。

## 12. 必须新增的测试

至少包括：

1. 合法 action schema；
2. 非法 action schema；
3. 自由文本不会执行；
4. 必须显式授权；
5. `Observe` result；
6. `Stop` 高于运动请求；
7. stale/expired request；
8. duplicate/idempotency；
9. cancellation；
10. resource conflict；
11. target unavailable；
12. bounded queue；
13. result/observation correlation；
14. schema version rejection；
15. 无 ROS 2/NAOqi/network imports；
16. target 不存在时对话仍可用；
17. action duration 和 terminal event；
18. 重复运行结果确定。

测试必须不依赖：

- Ollama；
- NAO；
- 网络；
- ROS 2；
- GPU；
- Agent-Kernel。

## 13. 实施顺序

按以下顺序推进，不要一次性编写所有功能：

### Step 1 — 先写 Phase 2 schema 设计

先提交或报告：

- request/result/observation 类型；
- 状态机；
- validation 规则；
- idempotency 规则；
- priority 规则；
- action contract 归属；
- 与未来 NAO bridge 的兼容性假设。

等待项目负责人确认后再实现。

### Step 2 — 实现 schema 和 Fake Execution Agent

先不接对话和模型，完成纯单元测试。

### Step 3 — 实现 authorization boundary

证明：

```text
ModelResult 不能直接变成 executable action
```

### Step 4 — 实现 safety simulation

加入 TTL、cancel、duplicate、resource conflict、Stop priority 和 queue
语义。

### Step 5 — 接入 Phase 1 conversation

保持普通文本对话不受影响，并补充 action/result/observation 状态。

### Step 6 — 完善文档、测试和交付报告

准备 TRAE + GLM-5.2 独立评审。

## 14. 完成标准

Phase 2 只有在以下条件全部满足时才算完成：

- action/result/observation schema 有版本和校验；
- action contract 明确归 Agent4NAO 所有；
- 自由文本无法直接执行；
- 显式授权是必要条件；
- Fake Execution Agent 确定性可重复；
- Stop 优先级、取消和过期请求可验证；
- duplicate/resource conflict 可验证；
- result/observation 能关联原始 request；
- 无硬件、网络、ROS 2、NAOqi 或 Agent-Kernel 依赖；
- 全部测试从 clean checkout 通过；
- 文档与实现一致；
- 未声称已经实现真实 NAO 安全能力。

## 15. Handoff 给 TRAE + GLM-5.2

交付评审前必须提供：

1. commit id；
2. changed-file list；
3. schema 文档；
4. 状态机和安全语义说明；
5. ModelResult 到 typed action 的完整路径；
6. exact test command/output；
7. 无真实执行路径的证据；
8. 已知限制；
9. 后续 NAO bridge 的兼容性假设。

评审重点：

- action ownership；
- schema invariants；
- free-form text 是否可能执行；
- stale/duplicate/cancel；
- Stop priority；
- resource semantics；
- result/observation correlation；
- scope boundary；
- 可复现性。

## 16. 当前状态

```text
Phase 1 Status: ACCEPTED
Phase 2 Status: AUTHORIZED FOR DESKTOP SIMULATION ONLY
Phase 3 Read-only NAO Bridge: NOT AUTHORIZED
NAO Actuator Access: NOT AUTHORIZED
ROS 2 Integration: NOT AUTHORIZED
NAOqi Integration: NOT AUTHORIZED
Agent-Kernel Modification: NOT AUTHORIZED
```

开始时先输出 Phase 2 schema 设计和实施分解，不要直接修改代码。
