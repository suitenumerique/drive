#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_pr_body_from_event(event_path: Path) -> str | None:
    try:
        payload = json.loads(event_path.read_text(encoding="utf-8"))
    except OSError:
        return None
    except json.JSONDecodeError:
        return None

    pr = payload.get("pull_request")
    if not isinstance(pr, dict):
        return None
    body = pr.get("body")
    if not isinstance(body, str):
        return None
    return body


_STORY_FILE_RE = re.compile(
    r"(?P<path>_bmad-output/implementation-artifacts/(?!prompts/)[^s)]+.md)"
)
_FP_RE = re.compile(r"BMAD-FP-BP:\\s*(?P<fp>sha256:[0-9a-f]{64})")


def _extract_story_file_path(pr_body: str) -> str | None:
    m = _STORY_FILE_RE.search(pr_body)
    if not m:
        return None
    return m.group("path")


def _extract_fp(pr_body: str) -> str | None:
    m = _FP_RE.search(pr_body)
    if not m:
        return None
    return m.group("fp")


def _print_fail(failure_class: str, next_action_hint: str) -> int:
    print(f"failure_class={failure_class}")
    print(f"next_action_hint={next_action_hint}")
    return 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="strict-mirror-check",
        description="Verify BMAD strict mirror fingerprint in PR body (B+ subset).",
    )
    parser.add_argument(
        "--event-path",
        help="Path to a GitHub Actions event JSON (for pull_request).",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Print the expected BMAD-FP-BP line for the story file referenced in the event/body.",
    )
    args = parser.parse_args(argv)

    repo = _repo_root()

    body = None
    if args.event_path:
        body = _load_pr_body_from_event(Path(args.event_path))
    else:
        body = sys.stdin.read()

    if not body:
        return _print_fail(
            "strict_mirror.pr_body.missing",
            "Ensure the pull_request event body is available to the checker.",
        )

    story_rel = _extract_story_file_path(body)
    if not story_rel:
        # Non-BMAD PR: strict mirror enforcement applies only when a work item is
        # mirrored into a GitHub issue/PR with a BMAD story reference.
        print("ok=true skipped=true")
        return 0

    story_path = repo / story_rel
    if not story_path.exists():
        return _print_fail(
            "strict_mirror.story_file.not_found",
            "Ensure the referenced BMAD story artifact exists in the repo and "
            "matches the PR body path.",
        )

    sys.path.insert(0, str(repo / "src" / "backend"))
    try:
        # pylint: disable=import-error
        from core.utils.strict_mirror import compute_bmad_fingerprint_bp_from_markdown
    except Exception:  # pragma: no cover
        return _print_fail(
            "strict_mirror.import_failed",
            "Ensure src/backend is present and core.utils.strict_mirror is importable.",
        )

    try:
        fp_expected = compute_bmad_fingerprint_bp_from_markdown(
            story_path.read_text(encoding="utf-8")
        )
    except OSError:
        return _print_fail(
            "strict_mirror.fingerprint.compute_failed",
            "Ensure the BMAD story file is readable in the checked-out workspace.",
        )

    if args.print:
        print(f"BMAD-FP-BP: {fp_expected}")
        return 0

    fp_actual = _extract_fp(body)
    if not fp_actual:
        return _print_fail(
            "strict_mirror.fingerprint.missing",
            "Add `BMAD-FP-BP: <sha256:...>` to the PR body. "
            "BMAD local artifacts/registry are the source of truth.",
        )

    if fp_actual != fp_expected:
        return _print_fail(
            "strict_mirror.fingerprint.mismatch",
            "Update the PR body fingerprint to match BMAD artifacts. "
            "Hint: run `python3 bin/strict_mirror_check.py --event-path "
            "$GITHUB_EVENT_PATH --print` in CI, or recompute locally from the story file.",
        )

    print("ok=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
