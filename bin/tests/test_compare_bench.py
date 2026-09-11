"""Comparison contract tests, runnable without Django or PostgreSQL."""

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "compare_bench.py"
SPEC = importlib.util.spec_from_file_location("compare_bench", SCRIPT)
BENCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BENCH)


def sample():
    return {
        "mode": "historical", "protocol_version": "restricted_2-v1",
        "postgres": "test", "python": "test", "cache_backend": "test",
        "config": {**dict.fromkeys(BENCH.CONFIG_KEYS, 10), "with_restrictions": False},
        "scenarios": {"children": {"ms_median": 100, "queries": 10}},
    }


class ComparisonTests(unittest.TestCase):
    def test_matching_protocol_and_percentage(self):
        before = sample()
        after = copy.deepcopy(before)
        after["scenarios"]["children"] = {"ms_median": 75, "queries": 5}
        report, uncertain = BENCH.report(before, after)
        self.assertFalse(uncertain)
        self.assertIn("-25.0%", report)
        self.assertIn("10 → 5", report)

    def test_minimum_column(self):
        before, after = sample(), sample()
        for data, median, minimum in ((before, 100, 90), (after, 80, 45)):
            data["scenarios"]["children"] = {
                "api": {"median_ms": median, "min_ms": minimum}, "sql_calls": 4,
            }
        report, _ = BENCH.report(before, after)
        self.assertIn("100.000 → 80.000", report)
        self.assertIn("90.000 → 45.000", report)
        self.assertIn("-50.0%", report)

    def test_legacy_is_provisional(self):
        legacy = sample()
        del legacy["protocol_version"]
        report, uncertain = BENCH.report(legacy, sample())
        self.assertTrue(uncertain)
        self.assertIn("PROVISIONAL", report)

    def test_different_dataset_and_protocol(self):
        after = sample()
        after["config"]["nb_children"] = 1000
        after["protocol_version"] = "other"
        mismatches, _ = BENCH.compatibility(sample(), after)
        self.assertTrue(any("nb_children" in entry for entry in mismatches))
        self.assertTrue(any("protocol_version" in entry for entry in mismatches))

    def test_different_response_and_instrumentation(self):
        before = sample()
        after = sample()
        before["scenarios"]["children"]["rows"] = 20
        after["scenarios"]["children"] = {
            "api": {"median_ms": 80}, "sql_calls": 4, "rows": 10,
        }
        mismatches, _ = BENCH.compatibility(before, after)
        self.assertTrue(any("instrumentation" in entry for entry in mismatches))
        self.assertTrue(any("rows" in entry for entry in mismatches))

    def test_zero_baseline(self):
        before = sample()
        before["scenarios"]["children"]["ms_median"] = 0
        self.assertIn("n/a", BENCH.report(before, sample())[0])

    def test_invalid_metrics(self):
        for duration in (-1, float("nan"), "100", True):
            with self.subTest(duration=duration), self.assertRaises(ValueError):
                BENCH.metrics({"ms_median": duration, "queries": 1})

    def test_cli_exit_statuses(self):
        with tempfile.TemporaryDirectory() as directory:
            a, b = Path(directory) / "a.json", Path(directory) / "b.json"
            a.write_text(json.dumps(sample()))
            b.write_text(json.dumps(sample()))
            def run():
                return subprocess.run(
                    [sys.executable, str(SCRIPT), str(a), str(b)],
                    capture_output=True, check=False,
                ).returncode
            self.assertEqual(run(), 0)
            changed = sample()
            changed["config"]["page_size"] = 200
            b.write_text(json.dumps(changed))
            self.assertEqual(run(), 1)
            b.write_text("invalid")
            self.assertEqual(run(), 2)


if __name__ == "__main__":
    unittest.main()
