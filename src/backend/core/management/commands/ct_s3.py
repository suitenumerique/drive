"""Management command to run CT-S3 (S3 contract tests) and write artifacts."""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand

from core.ct_s3.constants import PROFILE_SEAWEEDFS_S3
from core.ct_s3.runner import dumps_json, render_human_report, run_ct_s3
from core.ct_s3.types import RunnerOptions


class Command(BaseCommand):
    """Run CT-S3 checks and write deterministic artifacts."""

    help = "Run CT-S3 (S3 contract tests) and write deterministic artifacts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--profile",
            default=PROFILE_SEAWEEDFS_S3,
            help="Provider profile id (default: seaweedfs-s3).",
        )
        parser.add_argument(
            "--out-dir",
            default="_bmad-output/implementation-artifacts/ct-s3",
            help="Output directory root for CT-S3 artifacts.",
        )
        parser.add_argument(
            "--run-id",
            default=None,
            help="Optional run id override (default: UTC timestamp).",
        )
        parser.add_argument(
            "--strict-range-206",
            action="store_true",
            help="Fail CT-S3-006 unless Range GET returns 206.",
        )
        parser.add_argument(
            "--http-timeout-s",
            type=float,
            default=10.0,
            help="HTTP timeout (seconds) for raw signature checks.",
        )

    def handle(self, *args, **options):
        runner_options = RunnerOptions(
            strict_range_206=bool(options["strict_range_206"]),
            http_timeout_s=float(options["http_timeout_s"]),
        )
        report = run_ct_s3(
            profile_id=str(options["profile"]),
            run_id=options.get("run_id"),
            options=runner_options,
        )

        out_root = Path(str(options["out_dir"]))
        run_dir = out_root / f"{report['run_id']}-{options['profile']}"
        run_dir.mkdir(parents=True, exist_ok=True)

        (run_dir / "report.md").write_text(
            render_human_report(report), encoding="utf-8"
        )
        (run_dir / "report.json").write_text(dumps_json(report), encoding="utf-8")
        (out_root / "latest.txt").write_text(
            str(run_dir.relative_to(out_root)) + "\n", encoding="utf-8"
        )

        if report["overall_ok"]:
            self.stdout.write(self.style.SUCCESS("CT-S3: PASS"))
        else:
            self.stderr.write(self.style.ERROR("CT-S3: FAIL"))
            raise SystemExit(1)
