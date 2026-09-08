"""Verify benchmark isolation, cleanup and command options."""

import json

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection

import pytest

from core.services.benchmark import Benchmark


def test_benchmark_rejects_invalid_reps():
    """Invalid input must fail before touching the database."""
    with pytest.raises(CommandError, match="at least 2"):
        call_command("benchmark", reps=1)


def test_benchmark_preserves_existing_output(tmp_path):
    """An existing baseline must never be replaced."""
    output = tmp_path / "baseline.json"
    output.write_text("baseline", encoding="utf-8")
    with pytest.raises(CommandError, match="already exists"):
        call_command("benchmark", output=output)
    assert output.read_text(encoding="utf-8") == "baseline"


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("mode", ["pghero", "historical"])
def test_benchmark_smoke(mode, tmp_path):
    """Exercise each protocol and preserve the caller's database."""
    original_name = connection.settings_dict["NAME"]
    with connection.cursor() as cursor:
        cursor.execute("SELECT datname FROM pg_database WHERE datname LIKE 'drive_bench_%'")
        before = set(cursor.fetchall())
    output = tmp_path / "result.json"
    call_command("benchmark", mode=mode, reps=2, restrictions=True, output=output)
    assert connection.settings_dict["NAME"] == original_name
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database()")
        assert cursor.fetchone()[0] == original_name
        cursor.execute("SELECT datname FROM pg_database WHERE datname LIKE 'drive_bench_%'")
        assert set(cursor.fetchall()) == before
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["mode"] == mode
    assert len(result["scenarios"]) == (9 if mode == "pghero" else 7)
    assert result["config"]["reps"] == 2


@pytest.mark.django_db(transaction=True)
def test_benchmark_cleans_up_after_failure(monkeypatch, tmp_path):
    """A workload error still drops its database and restores the original name."""
    original_name = connection.settings_dict["NAME"]
    temporary_names = []

    def fail(_self):
        temporary_names.append(connection.settings_dict["NAME"])
        assert temporary_names[0] != original_name
        raise RuntimeError("benchmark failed")

    monkeypatch.setattr(Benchmark, "run", fail)
    with pytest.raises(RuntimeError, match="benchmark failed"):
        call_command("benchmark", output=tmp_path / "result.json")
    assert connection.settings_dict["NAME"] == original_name
    with connection.cursor() as cursor:
        cursor.execute("SELECT datname FROM pg_database WHERE datname = %s", temporary_names)
        assert cursor.fetchall() == []
