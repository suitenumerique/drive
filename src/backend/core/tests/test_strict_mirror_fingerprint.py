"""
Unit tests for BMAD strict mirror fingerprinting (B+ subset).
"""

import pytest

from core.utils.strict_mirror import compute_bmad_fingerprint_bp_from_markdown

pytestmark = pytest.mark.django_db


def test_bp_fingerprint_excludes_dynamic_sections():
    """Status and Dev Agent Record changes must not affect the B+ fingerprint."""
    base = """# Story 1.2: Example

Status: in-progress

## Story

As a user, I want X so that Y.

## Acceptance Criteria

**Given** A
**When** B
**Then** C

## Dev Agent Record

### Completion Notes List

- Run folder: _bmad-output/implementation-artifacts/runs/20260101-000000-1.2/
"""

    changed = """# Story 1.2: Example

Status: done

## Story

As a user, I want X so that Y.

## Acceptance Criteria

**Given** A
**When** B
**Then** C

## Dev Agent Record

### Completion Notes List

- Run folder: _bmad-output/implementation-artifacts/runs/20260211-123456-1.2/
"""

    assert compute_bmad_fingerprint_bp_from_markdown(base) == (
        compute_bmad_fingerprint_bp_from_markdown(changed)
    )


def test_bp_fingerprint_changes_when_acceptance_criteria_changes():
    """Acceptance Criteria changes must change the B+ fingerprint."""
    a = """# Story 1.2: Example

## Story

As a user, I want X so that Y.

## Acceptance Criteria

**Given** A
**When** B
**Then** C
"""

    b = """# Story 1.2: Example

## Story

As a user, I want X so that Y.

## Acceptance Criteria

**Given** A
**When** B
**Then** D
"""

    assert compute_bmad_fingerprint_bp_from_markdown(a) != (
        compute_bmad_fingerprint_bp_from_markdown(b)
    )
