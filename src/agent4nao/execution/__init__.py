"""Agent4NAO Phase 2 execution package.

Deterministic in-process simulation of the future NAO Execution Agent. No
NAOqi, ROS 2, socket/TLS, hardware, or Agent-Kernel dependency is present.
"""

from agent4nao.execution.clock import Clock, FakeClock
from agent4nao.execution.fake_agent import FakeNAOExecutionAgent

__all__ = ["Clock", "FakeClock", "FakeNAOExecutionAgent"]
