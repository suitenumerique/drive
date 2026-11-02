"""Test the `profile_endpoints` management command"""

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

import pytest

pytestmark = pytest.mark.django_db


def test_commands_profile_endpoints():
    """The command should call each endpoint and report timings, queries and plans."""
    # Forcing instead of overriding DEBUG: the URL configuration loaded by the first
    # request would otherwise include the debug toolbar, absent from test settings.
    call_command(
        "create_perf_dataset",
        "--force",
        "--users=30",
        "--items=500",
        "--accesses=60",
        "--link-traces=10",
    )
    stdout = StringIO()

    call_command(
        "profile_endpoints", "--force", "--repeat=1", "--explain", "--no-jit", stdout=stdout
    )

    output = stdout.getvalue()
    headers = [line for line in output.splitlines() if "/api/" in line]
    assert all("[200]" in header for header in headers)
    for label in [
        "list",
        "recents",
        "favorites",
        "trashbin",
        "children",
        "users trigram",
        "users levenshtein",
        "contacts",
    ]:
        assert any(header.startswith(label) for header in headers)
    assert "queries" in output
    assert "EXPLAIN of the slowest query" in output
    assert "Execution Time" in output


def test_commands_profile_endpoints_unknown_user():
    """The command should fail clearly when the user does not exist."""
    with pytest.raises(CommandError, match="No user found"):
        call_command("profile_endpoints", "--force", "--email=unknown@example.com")


@override_settings(DEBUG=False)
def test_commands_profile_endpoints_requires_debug():
    """The command should refuse to run outside of debug mode without --force."""
    with pytest.raises(CommandError, match="not meant to be used in production"):
        call_command("profile_endpoints")
