"""Tests for strict_mirror_check story path extraction."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_checker_module():
    repo_root = Path(__file__).resolve().parents[4]
    checker_path = repo_root / "bin" / "strict_mirror_check.py"
    spec = importlib.util.spec_from_file_location("strict_mirror_check", checker_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_extract_story_file_path_matches_bmad_story_files():
    checker = _load_checker_module()
    body = "Story file: _bmad-output/implementation-artifacts/10-1-example.md"
    assert checker._extract_story_file_path(body) == (
        "_bmad-output/implementation-artifacts/10-1-example.md"
    )


def test_extract_story_file_path_ignores_prompt_files():
    checker = _load_checker_module()
    body = "Prompt: _bmad-output/implementation-artifacts/prompts/10.1-dev.md"
    assert checker._extract_story_file_path(body) is None
