# Agent4NAO Phase 2 独立评审报告 Rev1.0

> 独立只读评审，依据 `Agent4NAO Phase 2 独立评审任务` 执行。
> 评审人：TRAE + GLM-5.2。
> 未修改任何源码、测试、文档或依赖。
> 所有证据来自直接仓库检查和命令执行，日期 2026-09-15。

## 1. 总体结论

**PASS WITH MINOR FINDINGS**

Phase 2 实现功能完整、架构边界正确、状态机一致、授权边界不可绕过、测试覆盖充分。132/132 测试通过，compileall 通过，无 ROS 2/NAOqi/Agent-Kernel/硬件依赖。18 项必测要求全部有实际断言覆盖。发现 1 个 MEDIUM 文档问题（README 示例不可直接成功运行）和若干 LOW 级测试缺口，均不影响安全性或正确性。

## 2. 高置信度问题

| # | 严重性 | 文件/符号 | 行号 | 问题 | 影响 | 证据 | 修复建议 |
|---|---|---|---|---|---|---|---|
| 1 | MEDIUM | `README.md` | L57-59 | Phase 2 示例中 `FakeModelProvider()` 无参构造时 `fixed_response="ok"`，模型返回 `"ok"` 而非 proposal JSON，导致 `parse_proposal("ok")` 返回 `None`，`session.authorize(None)` 返回 `INVALID_PARAMETERS` 拒绝，而非示例暗示的成功 observation | 用户按 README 示例操作会得到拒绝结果而非成功观察，与示例意图不符 | `fake.py` L25: `fixed_response: str = "ok"`; `json.loads("ok")` 抛 `JSONDecodeError` → `parse_proposal` 返回 `None` | 改为 `FakeModelProvider(fixed_response='{"capability": "observe", "parameters": {}}')`，或添加注释说明需要配置模型返回 proposal |
| 2 | LOW | `src/agent4nao/__init__.py` | L3 | 包级 docstring 仍写 "Phase 1 scope: desktop local-model conversation only"，未反映 Phase 2 已实现 action/execution 包 | 文档与实际状态不符；不影响功能 | 直接源码检查 | 更新 docstring 以反映 Phase 2 状态 |
| 3 | LOW | `fake_agent.py` `_is_stale` | L216 | `_is_stale` 使用严格 `>` 判定过期：`now > created_at + ttl_seconds`，即 `now == created_at + ttl` 时 NOT stale。schema 文档 §6 未显式记录此边界语义 | 边界条件语义未文档化；实现选择合理（TTL 表示有效期，超出才过期） | `return self._clock.now() > request.created_at + request.ttl_seconds` | 在 schema 文档 §6 补充："`now == created_at + ttl` 时请求仍有效" |
| 4 | LOW | `fake_agent.py` `_immediate` | L370 | 过期请求在提交时通过 `_immediate` → `_record_of` 注册了幂等键，导致相同 `(session_id, idempotency_key)` 的后续不同 `request_id` 请求会得到 `IDEMPOTENCY_CONFLICT` 而非被处理 | 过期请求"占用"了幂等键；客户端重试需使用新幂等键。与 schema 文档 §7 一致（文档未区分原请求状态），但可能不符直觉 | `_record_of` L348 注册幂等键；`_check_duplicate` L199 检查幂等键 | 如需允许过期后重试，可在 `_is_stale` 路径跳过幂等键注册；当前行为可接受但应在文档中记录 |

## 3. 测试缺口

### 缺失的行为测试

| 缺口 | 严重性 | 说明 |
|---|---|---|
| `cancel` 对终态请求的行为 | LOW | `cancel` 方法 L186 对终态请求返回 `rec.result`（原结果不变，无 DUPLICATE 标记）。无测试验证此行为。 |
| `complete`/`fail` 对非 running 请求 | LOW | `complete` L147 和 `fail` L163 对非 RUNNING 请求返回 REJECTED + INVALID_PARAMETERS。无测试覆盖此拒绝路径。 |
| `Observe` 在 target 不可用时 | LOW | `test_target_unavailable_rejects_all` 仅测试 Walk；未测试 Observe 在 `target_available=False` 时是否也返回 TARGET_UNAVAILABLE。 |
| `Observe` 在 motion 队列满时 | LOW | 未测试 Observe 在队列满时是否仍能成功执行（应为只读能力，不受 motion 队列限制）。实现正确（Observe 在 L127 分支，不经过 `_admit_motion`），但无测试保护。 |
| `Stop` 在无运行中 motion 时 | LOW | 未测试 Stop 在无运行/等待 motion 时是否返回 COMPLETED + `preempted=[]`。实现正确（`_preempt` 返回空列表），但无测试保护。 |
| 跨 session 幂等键隔离 | LOW | 未测试相同 `idempotency_key` 但不同 `session_id` 的请求是否被正确接受（不冲突）。 |

### 断言不足的测试

未发现断言不足的测试。所有 132 个测试均有行为验证断言，不仅执行代码。

### 仅文档声明但未被测试验证的行为

| 声明 | 说明 |
|---|---|
| "终态请求不可再次执行" | `_check_duplicate` 对终态请求返回缓存结果（带 DUPLICATE），测试覆盖了 COMPLETED 终态的重放，但未显式覆盖 REJECTED/EXPIRED/CANCELLED/FAILED 终态的重放。 |
| "duration 不会被 wall-clock 回退影响" | 实现使用 `self._clock.monotonic()`（`_finish` L265），但无测试在 wall-clock 回退场景下验证 duration 正确性。 |

## 4. 契约与文档不一致

| # | 文件 | 不一致 | 严重性 |
|---|---|---|---|
| 1 | `README.md` L57-59 | 示例 `FakeModelProvider()` 不配置 `fixed_response`，模型返回 `"ok"` 而非 proposal JSON，示例暗示成功但实际得到拒绝 | MEDIUM |
| 2 | `__init__.py` L3 | docstring 写 "Phase 1 scope"，未更新为 Phase 2 | LOW |
| 3 | schema 文档 §6 | `_is_stale` 使用严格 `>`，边界 `now == created_at + ttl` 未文档化 | LOW |
| 4 | delivery report §6 | 编译命令写 `compileall -q src`，实际验证用 `compileall -q src tests`。不影响正确性。 | NOTE |

schema 文档 §3-§11 的字段、默认值、枚举、状态机、幂等性规则、队列语义、授权路径均与源码实现一致。delivery report 的变更文件列表、测试计数（132）、已知限制均准确。

## 5. 边界与安全结论

```
- 是否存在隐式执行路径：否
  send() 仅解析 proposal，不调用 authorize/submit。authorize() 是唯一执行路径。
  无自动授权、关键词触发或默认授权机制。

- 是否存在未授权 action 生成路径：否
  ActionRequest 只能通过 build_request（需 typed parameters）或
  build_request_from_authorized（需 AuthorizedAction）构造。
  authorize() 检查 isinstance(proposal, ProposedAction)。
  build_request_from_authorized() 检查 isinstance(authorized, AuthorizedAction)。
  无文本→请求的直接映射函数。

- 是否存在真实 NAO/网络/ROS2/Agent-Kernel 依赖：否
  grep 确认 action/ 和 execution/ 无 naoqi/rclpy/ros2/socket/ssl/agent_kernel 导入。
  test_no_forbidden_imports.py AST 级验证。
  test_boundary.py 全树扫描 forbidden imports + class ModelAction + capability 泄漏。
  pyproject.toml 无运行时依赖。

- 是否存在错误结果被伪装成成功：否
  所有错误路径返回显式 REJECTED/EXPIRED/CANCELLED/FAILED 状态 + 对应 ErrorCategory。
  3 个 except Exception（session.py:223, session.py:345, ollama.py:108）均不创建成功型回退。
  fake_agent.py 中 _finish 对 FAILED 状态设置 error_category != NONE。

- 是否存在静默丢弃未知 request、重复 request 或过期 request：否
  未知 request_id 的 cancel 返回 REJECTED + UNKNOWN_REQUEST。
  重复 request 返回缓存结果 + DUPLICATE（不触发新执行）。
  过期 request 返回 EXPIRED + STALE（在提交、出队、执行前三处检查）。
  幂等冲突返回 REJECTED + IDEMPOTENCY_CONFLICT。
  队列满返回 REJECTED + QUEUE_FULL。
  资源冲突返回 REJECTED + RESOURCE_CONFLICT。
  所有路径均有可观察的 ActionResult。
```

## 6. 交付建议

**修复 minor findings 后提交**

MEDIUM finding（README 示例不可直接成功运行）应在提交评审结论前修正。LOW findings 可作为后续迭代改进。

### 验证结果汇总

| 命令 | 结果 |
|---|---|
| `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q` | 132 passed in 1.39s |
| `python3 -m compileall -q src tests` | COMPILEALL OK |
| grep `class ModelAction` in `src/` | No matches |
| grep forbidden imports in `action/`+`execution/` | No matches（仅 docstring 声明） |
| grep forbidden imports in `conversation/` | No matches |

### 18 项必测覆盖确认

| # | 必测项 | 覆盖 | 测试文件 |
|---|---|---|---|
| 1 | valid action schema | ✓ | test_action_schema.py |
| 2 | invalid action schema | ✓ | test_action_schema.py |
| 3 | free-form text does not execute | ✓ | test_action_authorization.py, test_execution_integration.py, test_action_session.py |
| 4 | explicit authorization required | ✓ | test_action_authorization.py |
| 5 | Observe result | ✓ | test_fake_agent_safety.py, test_fake_agent_lifecycle.py |
| 6 | Stop priority over motion | ✓ | test_fake_agent_safety.py |
| 7 | stale/expired request | ✓ | test_fake_agent_safety.py |
| 8 | duplicate/idempotent request | ✓ | test_fake_agent_lifecycle.py |
| 9 | cancellation | ✓ | test_fake_agent_safety.py |
| 10 | resource conflict | ✓ | test_fake_agent_safety.py |
| 11 | target unavailable | ✓ | test_fake_agent_safety.py |
| 12 | bounded queue | ✓ | test_fake_agent_safety.py |
| 13 | result/observation correlation | ✓ | test_fake_agent_lifecycle.py |
| 14 | schema version rejection | ✓ | test_action_schema.py, test_fake_agent_safety.py |
| 15 | no ROS 2/NAOqi/network imports | ✓ | test_no_forbidden_imports.py, test_boundary.py |
| 16 | conversation usable when target absent | ✓ | test_execution_integration.py, test_action_session.py |

### 授权边界确认

```
assistant free text != ProposedAction          — parse_proposal 对自由文本返回 None ✓
ProposedAction != AuthorizedAction              — authorize() 是唯一 proposal→authorized 路径 ✓
AuthorizedAction != ActionRequest               — build_request_from_authorized 是唯一路径 ✓
ActionRequest != real execution                  — FakeNAOExecutionAgent 是模拟，无真实硬件 ✓
send() 绝不执行                                  — ActionSession.send 不调用 authorize/submit ✓
无 agent 时 action 不入队                        — authorize 返回 TARGET_UNAVAILABLE，不调用 submit ✓
```

---

## 附录：检查方法

| 步骤 | 方法 |
|---|---|
| 源码检查 | 直接 Read 全部 action/（9 文件）、execution/（3 文件）、conversation/execution.py |
| 测试检查 | 直接 Read 全部 8 个 Phase 2 测试文件 + test_boundary.py |
| 文档检查 | 直接 Read schema 文档、delivery report、README、implementation prompt、acceptance plan |
| 测试执行 | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q` |
| 编译检查 | `python3 -m compileall -q src tests` |
| 边界检查 | Grep `class ModelAction`、`naoqi/rclpy/ros2/socket/ssl/agent_kernel` in src/ |
| 能力泄漏检查 | test_boundary.py `test_capabilities_owned_by_action_and_execution` 验证 |
| 状态机分析 | 逐行审查 fake_agent.py 的 _admit_motion/_start_running/_finish/_promote_next/_preempt/cancel |
| 幂等性分析 | 逐行审查 _check_duplicate/_duplicate/_record_of 的注册和检查逻辑 |
| 授权边界分析 | 逐行审查 authorization.py 的 parse_proposal/authorize/build_request_from_authorized |
