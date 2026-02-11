"""Tests for strict_mirror_check story path extraction."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_checker_module():
    """Load `bin/strict_mirror_check.py` as a Python module for unit tests."""
    repo_root = Path(__file__).resolve().parents[4]
    checker_path = repo_root / "bin" / "strict_mirror_check.py"
    spec = importlib.util.spec_from_file_location("strict_mirror_check", checker_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_extract_story_file_path_matches_bmad_story_files():
    """Story files under _bmad-output/implementation-artifacts must be detected."""
    checker = _load_checker_module()
    body = "Story file: _bmad-output/implementation-artifacts/10-1-example.md"
    # pylint: disable=protected-access
    assert checker._extract_story_file_path(body) == (
        "_bmad-output/implementation-artifacts/10-1-example.md"
    )


def test_extract_story_file_path_ignores_prompt_files():
    """Prompt files under .../prompts/ must not be treated as story files."""
    checker = _load_checker_module()
    body = "Prompt: _bmad-output/implementation-artifacts/prompts/10.1-dev.md"
    # pylint: disable=protected-access
    assert checker._extract_story_file_path(body) is None
