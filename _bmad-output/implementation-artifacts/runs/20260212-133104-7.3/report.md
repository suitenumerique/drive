# Story 7.3 — Mount browse (deterministic ordering + pagination)

Implemented a contract-level mount browse endpoint to list mount children with:

- Deterministic ordering (folder-first, then casefolded name, then path tie-breaker)
- Limit/offset pagination (`limit`, `offset`)
- Virtual entry identifiers via `(mount_id, normalized_path)`
- Per-entry `abilities.children_list` to support capability-driven Explorer rendering

## Evidence

- Gates runner report: `run-report.md` / `run-report.json`
- Commands: `commands.log`
- Files changed: `files-changed.txt`

