"""No ROS 2 / NAOqi / network / Agent-Kernel imports in Phase 2 modules."""

import ast
from pathlib import Path

FORBIDDEN_TOP_LEVEL = {
    "naoqi", "rclpy", "rcl", "rospy", "ros2", "socket", "ssl",
    "agent_kernel", "ak",
}


def _phase2_source_paths():
    root = Path(__file__).parents[1] / "src" / "agent4nao"
    for subdir in ("action", "execution"):
        yield from (root / subdir).glob("*.py")


def _imported_top_levels(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return {name.split(".")[0] for name in names}


def test_phase2_has_no_forbidden_imports() -> None:
    for path in _phase2_source_paths():
        for top in _imported_top_levels(path):
            assert top not in FORBIDDEN_TOP_LEVEL, (
                f"{path.name} imports forbidden module {top!r}")
