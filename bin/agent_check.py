#!/usr/bin/env python3

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Literal

Result = Literal["pass", "fail"]


CATALOG_VERSION = "v1"


@dataclasses.dataclass(frozen=True)
class GateDef:
    gate_id: str
    description: str


@dataclasses.dataclass(frozen=True)
class GateResult:
    gate_id: str
    result: Result
    duration_ms: int
    failure_class: str | None = None
    next_action_hint: str | None = None

    def to_json(self) -> dict:
        return {
            "gate_id": self.gate_id,
            "result": self.result,
            "duration_ms": self.duration_ms,
            "failure_class": self.failure_class,
            "next_action_hint": self.next_action_hint,
        }


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _utc_run_id(tag: str | None) -> str:
    base = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
    if not tag:
        return base
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", tag).strip("-")
    return f"{base}-{safe}" if safe else base


def _run(cmd: list[str], *, cwd: Path) -> tuple[int, int]:
    start = time.perf_counter()
    proc = subprocess.run(cmd, cwd=str(cwd), check=False)
    duration_ms = int((time.perf_counter() - start) * 1000)
    return proc.returncode, duration_ms


def _git_output(args: list[str], *, cwd: Path) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout


def _detect_diff_base(cwd: Path) -> str:
    for candidate in ("origin/main", "upstream/main", "main"):
        if _git_output(["rev-parse", "--verify", candidate], cwd=cwd).strip():
            return candidate
    return "main"


def _infer_gates_from_diff(paths: Iterable[str]) -> list[str]:
    selected: set[str] = set()
    for p in paths:
        if p.startswith("src/backend/") or p.startswith("bin/"):
            selected.add("backend.lint")
        if p.startswith("src/backend/"):
            selected.add("backend.tests")
        if p.startswith("src/frontend/"):
            selected.add("frontend.lint")
        if p.startswith("docs/") or p.startswith("_bmad-output/"):
            selected.add("docs.consistency")
    if any(p.startswith("_bmad-output/") for p in paths):
        selected.add("no_leak.scan_bmad_output")
    return sorted(selected)


def _gate_catalog() -> list[GateDef]:
    return [
        GateDef("backend.lint", "Backend lint (ruff/pylint via make lint)"),
        GateDef("backend.tests", "Backend tests (pytest via make test-back)"),
        GateDef("frontend.lint", "Frontend lint (yarn lint via make frontend-lint)"),
        GateDef("docs.consistency", "Docs/text consistency checks (no trailing spaces)"),
        GateDef("no_leak.scan_bmad_output", "No-leak scan over _bmad-output text artifacts"),
        GateDef("s3.contracts.seaweedfs", "CT-S3 contract tests (SeaweedFS baseline profile)"),
        GateDef("mount.integration", "Mounts integration gate (placeholder)"),
    ]


def _gate_ids() -> set[str]:
    return {g.gate_id for g in _gate_catalog()}


def _check_docs_consistency(
    repo: Path, run_dir: Path, files_changed: list[str]
) -> tuple[Result, str | None, str | None]:
    targets: list[Path] = []
    for rel in sorted({p for p in files_changed if p.startswith(("docs/", "_bmad-output/"))}):
        p = repo / rel
        if not p.exists() or not p.is_file():
            continue
        if p.suffix not in (".md", ".json", ".txt"):
            continue
        targets.append(p)

    bad: list[str] = []
    for p in targets:
        try:
            data = p.read_bytes()
        except OSError:
            continue

        if b"\r\n" in data:
            bad.append(f"{p.relative_to(repo).as_posix()}:crlf")
            continue

        if data and not data.endswith(b"\n"):
            bad.append(f"{p.relative_to(repo).as_posix()}:no-final-newline")
            continue

        for idx, line in enumerate(data.splitlines(), start=1):
            if line.rstrip(b" \t") != line:
                bad.append(f"{p.relative_to(repo).as_posix()}:{idx}:trailing-space")
                break

    evidence_path = run_dir / "gates" / "docs.consistency.evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(
            {
                "checked_file_count": len(targets),
                "issue_count": len(bad),
                "issues": bad[:200],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    if bad:
        return (
            "fail",
            "gate.docs.consistency_failed",
            "Remove trailing whitespace/CRLF and ensure final newlines.",
        )
    return ("pass", None, None)


_NO_LEAK_PATTERNS: list[tuple[str, re.Pattern[bytes]]] = [
    ("aws_access_key_id", re.compile(rb"\bAKIA[0-9A-Z]{16}\b")),
    (
        "aws_secret_access_key_value",
        re.compile(rb"\bAWS_SECRET_ACCESS_KEY\b\s*[:=]\s*[A-Za-z0-9/+=]{40}\b"),
    ),
    ("private_key_pem", re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("sigv4_auth", re.compile(rb"AWS4-HMAC-SHA256")),
    ("bearer_token", re.compile(rb"\bBearer [A-Za-z0-9._-]{20,}\b")),
]


def _scan_no_leak_bmad_output(repo: Path, run_dir: Path) -> tuple[Result, str | None, str | None]:
    root = repo / "_bmad-output"
    if not root.exists():
        return ("pass", None, None)

    matches: list[dict] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix not in (".md", ".json", ".txt", ".yml", ".yaml"):
            continue

        try:
            data = p.read_bytes()
        except OSError:
            continue

        for pid, pat in _NO_LEAK_PATTERNS:
            for m in pat.finditer(data):
                digest = hashlib.sha256(m.group(0)).hexdigest()[:16]
                matches.append(
                    {
                        "pattern_id": pid,
                        "path": p.relative_to(repo).as_posix(),
                        "match_sha256_16": digest,
                    }
                )

    evidence_path = run_dir / "gates" / "no_leak.scan_bmad_output.evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(
            {"match_count": len(matches), "matches": matches},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    if matches:
        return (
            "fail",
            "no_leak.scan.match_found",
            "Remove/redact secrets from _bmad-output and re-run the gate.",
        )
    return ("pass", None, None)


def _execute_gate(gate_id: str, repo: Path, run_dir: Path, files_changed: list[str]) -> GateResult:
    if gate_id == "backend.lint":
        code, dur = _run(["make", "lint"], cwd=repo)
        if code == 0:
            return GateResult(gate_id, "pass", dur)
        return GateResult(
            gate_id,
            "fail",
            dur,
            "gate.backend.lint_failed",
            "Run `make lint` and fix reported lint errors.",
        )

    if gate_id == "backend.tests":
        code, dur = _run(["make", "test-back"], cwd=repo)
        if code == 0:
            return GateResult(gate_id, "pass", dur)
        return GateResult(
            gate_id,
            "fail",
            dur,
            "gate.backend.tests_failed",
            "Run `make test-back` and fix failing tests.",
        )

    if gate_id == "frontend.lint":
        code, dur = _run(["make", "frontend-lint"], cwd=repo)
        if code == 0:
            return GateResult(gate_id, "pass", dur)
        return GateResult(
            gate_id,
            "fail",
            dur,
            "gate.frontend.lint_failed",
            "Run `make frontend-lint` and fix reported lint errors.",
        )

    if gate_id == "docs.consistency":
        start = time.perf_counter()
        res, fc, nah = _check_docs_consistency(repo, run_dir, files_changed)
        dur = int((time.perf_counter() - start) * 1000)
        return GateResult(gate_id, res, dur, fc, nah)

    if gate_id == "no_leak.scan_bmad_output":
        start = time.perf_counter()
        res, fc, nah = _scan_no_leak_bmad_output(repo, run_dir)
        dur = int((time.perf_counter() - start) * 1000)
        return GateResult(gate_id, res, dur, fc, nah)

    if gate_id == "s3.contracts.seaweedfs":
        code, dur = _run(["./bin/ct_s3", "--profile", "seaweedfs-s3"], cwd=repo)
        if code == 0:
            return GateResult(gate_id, "pass", dur)
        return GateResult(
            gate_id,
            "fail",
            dur,
            "s3.contracts.failed",
            "Inspect CT-S3 artifacts under `_bmad-output/implementation-artifacts/ct-s3/`.",
        )

    if gate_id == "mount.integration":
        start = time.perf_counter()
        dur = int((time.perf_counter() - start) * 1000)
        return GateResult(
            gate_id,
            "fail",
            dur,
            "mount.integration.not_implemented",
            "Implement mounts integration checks before enabling this gate.",
        )

    return GateResult(
        gate_id,
        "fail",
        0,
        "gate.catalog.invalid",
        "Unknown gate_id; run `bin/agent-check.sh --list-gates`.",
    )


def _command_summaries(gate_id: str) -> list[str]:
    if gate_id == "backend.lint":
        return ["make lint"]
    if gate_id == "backend.tests":
        return ["make test-back"]
    if gate_id == "frontend.lint":
        return ["make frontend-lint"]
    if gate_id == "docs.consistency":
        return ["docs.consistency (check changed docs/_bmad-output text files)"]
    if gate_id == "no_leak.scan_bmad_output":
        return ["no_leak.scan_bmad_output (scan _bmad-output text artifacts)"]
    if gate_id == "s3.contracts.seaweedfs":
        return ["./bin/ct_s3 --profile seaweedfs-s3"]
    if gate_id == "mount.integration":
        return ["mount.integration (not implemented)"]
    return ["(unknown)"]


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="agent-check",
        description="Deterministic gates runner keyed by stable gate_id.",
    )
    parser.add_argument("--gate", action="append", default=[], help="Gate ID to execute (repeatable).")
    parser.add_argument("--list-gates", action="store_true", help="List available gate IDs and exit.")
    parser.add_argument("--preflight", action="store_true", help="Resolve gates but do not execute them.")
    parser.add_argument("--quick", action="store_true", help="Never 'skip all' (keeps at least one gate).")
    parser.add_argument("--tag", help="Optional run folder suffix (e.g. '12.1').")
    parser.add_argument("--diff-base", help="Git ref to diff against for gate inference.")
    args = parser.parse_args(argv)

    repo = _repo_root()

    if args.list_gates:
        for g in _gate_catalog():
            print(f"{g.gate_id}\t{g.description}")
        return 0

    known = _gate_ids()

    requested_gates: list[str] = list(args.gate)
    if requested_gates:
        selected = requested_gates
    else:
        diff_base = args.diff_base or _detect_diff_base(repo)
        changed = [
            p.strip()
            for p in _git_output(["diff", "--name-only", f"{diff_base}...HEAD"], cwd=repo).splitlines()
            if p.strip()
        ]
        selected = _infer_gates_from_diff(changed)
        if args.quick and not selected:
            selected = ["backend.lint"]

    selected = [g.strip() for g in selected if g.strip()]
    unknown = sorted({g for g in selected if g not in known})
    if unknown:
        print("Unknown gate_id(s):", ", ".join(unknown), file=sys.stderr)
        print("Hint: run `bin/agent-check.sh --list-gates`.", file=sys.stderr)
        return 2

    if args.preflight:
        print("Selected gates:")
        for g in selected:
            print(f"- {g}")
        return 0

    run_id = _utc_run_id(args.tag)
    impl = repo / "_bmad-output" / "implementation-artifacts"
    run_dir = impl / "runs" / run_id
    (run_dir / "gates").mkdir(parents=True, exist_ok=True)

    diff_base = args.diff_base or _detect_diff_base(repo)
    files_changed = sorted(
        p.strip()
        for p in _git_output(["diff", "--name-only", f"{diff_base}...HEAD"], cwd=repo).splitlines()
        if p.strip()
    )
    _write_text(run_dir / "files-changed.txt", "\n".join(files_changed) + ("\n" if files_changed else ""))

    cmd_lines: list[str] = []
    gate_results: list[GateResult] = []

    for gate_id in selected:
        cmd_lines.append(f"gate_id={gate_id}\n")
        for cmd in _command_summaries(gate_id):
            cmd_lines.append(f"cmd={cmd}\n")
        r = _execute_gate(gate_id, repo, run_dir, files_changed)
        gate_results.append(r)
        cmd_lines.append(f"result={r.result} duration_ms={r.duration_ms}\n\n")

    _write_text(run_dir / "commands.log", "".join(cmd_lines))

    gate_results_sorted = sorted(gate_results, key=lambda r: r.gate_id)
    overall: Result = "pass" if all(r.result == "pass" for r in gate_results_sorted) else "fail"

    gate_results_payload = [r.to_json() for r in gate_results_sorted]
    _write_text(
        run_dir / "gates" / "gate-results.json",
        json.dumps(gate_results_payload, indent=2) + "\n",
    )

    run_report = {
        "catalog_version": CATALOG_VERSION,
        "result": overall,
        "requested_gates": requested_gates if requested_gates else None,
        "selected_gates": selected,
        "git_head": _git_output(["rev-parse", "HEAD"], cwd=repo).strip() or None,
        "diff_base": diff_base,
        "gate_results": gate_results_payload,
    }
    _write_text(run_dir / "run-report.json", json.dumps(run_report, indent=2, sort_keys=True) + "\n")

    md_lines = [f"# Gates run — {run_id}", "", f"- result: **{overall.upper()}**", ""]
    for r in gate_results_sorted:
        md_lines.append(f"- `{r.gate_id}`: **{r.result.upper()}** ({r.duration_ms}ms)")
        if r.result != "pass":
            md_lines.append(f"  - failure_class: `{r.failure_class}`")
            md_lines.append(f"  - next_action_hint: {r.next_action_hint}")
    _write_text(run_dir / "run-report.md", "\n".join(md_lines) + "\n")

    gates_lines = [f"# Gates — run {run_id}", "", "## gates", ""]
    for r in gate_results_sorted:
        gates_lines.append(f"- `{r.gate_id}`: {r.result.upper()}")
    _write_text(run_dir / "gates.md", "\n".join(gates_lines) + "\n")

    latest_ptr = impl / "latest.txt"
    latest_ptr.write_text(
        str(Path("_bmad-output/implementation-artifacts/runs") / run_id) + "\n",
        encoding="utf-8",
    )

    print(f"Run folder: {run_dir.relative_to(repo)}")
    print(f"Result: {overall}")
    return 0 if overall == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
