"""Tests for BMAD story path extraction from PR bodies."""

from __future__ import annotations

from core.utils.strict_mirror import extract_story_file_path_from_pr_body


def test_extract_story_file_path_matches_bmad_story_files():
    """Story files under _bmad-output/implementation-artifacts must be detected."""
    body = "Story file: _bmad-output/implementation-artifacts/10-1-example.md"
    assert extract_story_file_path_from_pr_body(body) == (
        "_bmad-output/implementation-artifacts/10-1-example.md"
    )


def test_extract_story_file_path_ignores_prompt_files():
    """Prompt files under .../prompts/ must not be treated as story files."""
    body = "Prompt: _bmad-output/implementation-artifacts/prompts/10.1-dev.md"
    assert extract_story_file_path_from_pr_body(body) is None
