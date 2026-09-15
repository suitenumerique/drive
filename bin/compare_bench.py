#!/usr/bin/env python3
"""Compare benchmark JSON without Django: python3 bin/compare_bench.py before after.

Exit 0: compatible declared protocol/configuration; 1: incompatible or unknown;
2: invalid input. Missing legacy metadata never implies proven compatibility.
Percentages are descriptive changes in medians, not statistical significance.
"""

import argparse
import json
import math
from pathlib import Path

CONFIG_KEYS = (
    "reps", "page_size", "nb_children", "nb_subtrees", "subtree_depth",
    "nb_files", "restricted_every", "nb_redundant_users",
)


def metrics(stats):
    """Normalize historical and PgHero metrics without relabeling SQL as API time."""
    if "api" in stats:
        duration, calls = stats["api"]["median_ms"], stats["sql_calls"]
        minimum = stats["api"].get("min_ms")
    else:
        duration, calls = stats["ms_median"], stats["queries"]
        minimum = stats.get("ms_min")
    for value in (duration, calls) + ((minimum,) if minimum is not None else ()):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Metrics must be numeric")
        if not math.isfinite(value) or value < 0:
            raise ValueError("Metrics must be finite and nonnegative")
    return duration, calls, minimum


def change(before, after):
    """Percentage change, or n/a without a positive baseline or a value."""
    if not before or after is None:
        return "n/a"
    return f"{(after / before - 1) * 100:+.1f}%"


def load(path):
    """Validate relevant fields before comparing."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("scenarios"), dict):
        raise ValueError("Expected an object with a scenarios mapping")
    if not data["scenarios"]:
        raise ValueError("No benchmark scenarios")
    for stats in data["scenarios"].values():
        metrics(stats)
    if not isinstance(data.get("config", {}), dict):
        raise ValueError("config must be an object")
    return data


def compatibility(before, after):
    """Return hard mismatches separately from unverified conditions."""
    mismatches, unknown = [], []
    for key in ("mode", "protocol_version", "postgres", "python", "cache_backend"):
        left, right = before.get(key), after.get(key)
        if left is None or right is None:
            unknown.append(f"{key}: metadata missing")
        elif left != right:
            mismatches.append(f"{key}: {left!r} -> {right!r}")
    left_config, right_config = before.get("config", {}), after.get("config", {})
    for key in CONFIG_KEYS:
        left, right = left_config.get(key), right_config.get(key)
        if left is None or right is None:
            unknown.append(f"config.{key}: missing")
        elif left != right:
            mismatches.append(f"config.{key}: {left} -> {right}")
    left = left_config.get("with_restrictions", before.get("has_restricted"))
    right = right_config.get("with_restrictions", after.get("has_restricted"))
    if left is None or right is None:
        unknown.append("restriction setting missing")
    elif left != right:
        mismatches.append(f"restrictions: {left} -> {right}")
    if left or right:
        # Early big archives predate this explicit sample-size knob.
        a, b = left_config.get("nb_abilities_sample"), right_config.get("nb_abilities_sample")
        if a is None or b is None:
            unknown.append("config.nb_abilities_sample: missing")
        elif a != b:
            mismatches.append(f"config.nb_abilities_sample: {a} -> {b}")
    for key in ("dataset_items", "dataset_accesses"):
        a, b = before.get(key), after.get(key)
        if a is not None and b is not None and a != b:
            mismatches.append(f"{key}: {a} -> {b}")
    if set(before["scenarios"]) != set(after["scenarios"]):
        mismatches.append("scenario sets differ (only common names are displayed)")
    for name in before["scenarios"].keys() & after["scenarios"].keys():
        a, b = before["scenarios"][name], after["scenarios"][name]
        if ("api" in a) != ("api" in b):
            mismatches.append(f"{name}: different timing instrumentation")
        for key in ("rows", "count"):
            if key in a and key in b and a[key] != b[key]:
                mismatches.append(f"{name}.{key}: {a[key]} -> {b[key]}")
    for name in before.get("extra", {}).keys() & after.get("extra", {}).keys():
        if before["extra"][name] != after["extra"][name]:
            mismatches.append(f"extra.{name}: result sizes differ")
    return mismatches, unknown


def report(before, after):
    """Build a Markdown report, including non-comparable results as observations."""
    mismatches, unknown = compatibility(before, after)
    status = "INCOMPATIBLE" if mismatches else "PROVISIONAL" if unknown else "COMPATIBLE"
    lines = [f"Comparison: {status}", ""]
    for label, data in (("Before", before), ("After", after)):
        source = data.get("source", {})
        lines.append(f"{label}: commit={source.get('commit') or 'unknown'}, "
                     f"tracked_dirty={source.get('tracked_dirty', 'unknown')}")
    lines.extend(["", *[f"- {note}" for note in mismatches + unknown], ""])
    if mismatches or unknown:
        lines.append("Descriptive values only; these are not validated performance gains.")
    lines.extend(["", "| Scenario | Median before → after | Change | Min before → after | Change "
                  "| Calls before → after |", "|---|---:|---:|---:|---:|---:|"])
    for name in sorted(before["scenarios"].keys() & after["scenarios"].keys()):
        a, ac, amin = metrics(before["scenarios"][name])
        b, bc, bmin = metrics(after["scenarios"][name])
        minimum = f"{amin:.3f} → {bmin:.3f}" if amin is not None and bmin is not None else "n/a"
        lines.append(f"| {name} | {a:.3f} → {b:.3f} | {change(a, b)} | {minimum} "
                     f"| {change(amin, bmin)} | {ac} → {bc} |")
    lines.extend(["", "Negative duration changes mean faster runs. SQL call counts are not timings.",
                  "The minimum resists load spikes on the machine better than the median.",
                  "Matching metadata does not control machine load or prove statistical significance."])
    return "\n".join(lines), bool(mismatches or unknown)


def main():
    """Print comparison and return an automation-friendly status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args()
    try:
        rendered, uncertain = report(load(args.before), load(args.after))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    print(rendered)
    return int(uncertain)


if __name__ == "__main__":
    raise SystemExit(main())
