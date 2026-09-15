"""Boundary smoke tests for the initialized project."""

from pathlib import Path


def test_agent4nao_package_is_independent_of_kernel_source_tree() -> None:
    project_root = Path(__file__).parents[1]
    assert not (project_root / "kernel").exists()
    assert (project_root / "src" / "agent4nao").is_dir()
