"""Strict mirror fingerprint helpers for BMAD artifacts.

The BMAD registry/artifacts are the source of truth. GitHub issues/PRs are a
strict mirror and include a fingerprint (B+) that must match the canonical
subset of the underlying story artifact.

B+ subset policy (v1):
- include story title, Story section, Acceptance Criteria section
- exclude dynamic fields (status, runs, timestamps, Dev Agent Record)
"""

from __future__ import annotations

import hashlib


def _strip_trailing_ws(lines: list[str]) -> list[str]:
    return [ln.rstrip() for ln in lines]


def _extract_section(lines: list[str], heading: str) -> list[str]:
    """
    Extract a markdown section by its exact '## <name>' heading.

    The returned block includes the heading line and continues until the next
    level-2 heading (or EOF). If the heading is missing, returns an empty list.
    """
    start = None
    for idx, ln in enumerate(lines):
        if ln.strip() == heading:
            start = idx
            break
    if start is None:
        return []

    block: list[str] = []
    for ln in lines[start:]:
        if block and ln.startswith("## "):
            break
        block.append(ln)
    return block


def compute_bmad_fingerprint_bp_from_markdown(markdown: str) -> str:
    """Compute the B+ fingerprint for a BMAD story artifact markdown string."""
    raw_lines = markdown.splitlines()
    lines = _strip_trailing_ws(raw_lines)

    title = ""
    for ln in lines:
        if ln.startswith("# "):
            title = ln.strip()
            break

    story = _extract_section(lines, "## Story")
    ac = _extract_section(lines, "## Acceptance Criteria")

    canonical_lines: list[str] = []
    if title:
        canonical_lines.append(title)
        canonical_lines.append("")
    canonical_lines.extend(story)
    canonical_lines.append("")
    canonical_lines.extend(ac)

    canonical_text = "\n".join(_strip_trailing_ws(canonical_lines)).strip() + "\n"
    digest = hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
