"""Project boundary guarantees: no ROS 2, NAOqi, or robot-execution code."""

import re
from pathlib import Path

PACKAGE_ROOT = Path(__file__).parents[1] / "src" / "agent4nao"

FORBIDDEN_IMPORT_PATTERNS = [
    r"\bimport\s+ros2\b",
    r"\bimport\s+rclpy\b",
    r"\bimport\s+rclcpp\b",
    r"\bfrom\s+ros2\b",
    r"\bfrom\s+rclpy\b",
    r"\bimport\s+naoqi\b",
    r"\bfrom\s+naoqi\b",
    r"\bimport\s+rospy\b",
    r"\bimport\s+qi\b",
    r"\bimport\s+actionlib\b",
]

FORBIDDEN_DIRS = {"ros2", "naoqi", "runtime", "gateway", "robot", "kernel_lite",
                  "kernel-lite", "actuator", "hardware"}

MODEL_ACTION_DEFINITION = re.compile(r"\bclass\s+ModelAction\b")

CAPABILITY_NAMES = ("Stand", "Walk", "Stop", "Observe")


def _py_files() -> list[Path]:
    return sorted(PACKAGE_ROOT.rglob("*.py"))


def test_phase1_has_no_forbidden_imports() -> None:
    for path in _py_files():
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_IMPORT_PATTERNS:
            assert re.search(pattern, text) is None, (
                f"{path.relative_to(PACKAGE_ROOT)} contains forbidden import "
                f"matching {pattern!r}")


def test_phase1_has_no_forbidden_subpackages() -> None:
    existing = {p.name for p in PACKAGE_ROOT.iterdir() if p.is_dir()}
    overlap = existing & FORBIDDEN_DIRS
    assert not overlap, f"forbidden subpackages present: {overlap}"


def test_phase1_defines_no_model_action() -> None:
    # Phase 2 must not define a parallel ak::agent::ModelAction. Referencing the
    # name in a disclaimer is allowed; defining the class is not.
    for path in _py_files():
        text = path.read_text(encoding="utf-8")
        assert MODEL_ACTION_DEFINITION.search(text) is None, (
            f"{path.relative_to(PACKAGE_ROOT)} must not define ModelAction")


def test_capabilities_owned_by_action_and_execution() -> None:
    # Phase 2 simulated capabilities (Stand/Walk/Stop/Observe) live only under
    # the action/execution packages; conversation/model/config stay free of them.
    for path in _py_files():
        rel = path.relative_to(PACKAGE_ROOT)
        in_boundary = rel.parts[0] in ("action", "execution")
        text = path.read_text(encoding="utf-8")
        for word in CAPABILITY_NAMES:
            if word in text:
                assert in_boundary, (
                    f"{rel} references capability {word!r} outside action/execution")
