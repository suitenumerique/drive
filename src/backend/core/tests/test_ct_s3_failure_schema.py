from dataclasses import asdict

from core.ct_s3 import constants
from core.ct_s3.types import CheckResult


def test_ct_s3_check_result_schema_includes_failure_fields() -> None:
    result = CheckResult(
        check_id="CT-S3-TEST",
        audience=constants.AUDIENCE_INTERNAL_PROXY,
        ok=True,
        title="schema smoke",
        evidence={"status_code": 200},
    )

    payload = asdict(result)

    assert payload["audience"] == "INTERNAL_PROXY"
    assert "failure_class" in payload
    assert payload["failure_class"] is None
    assert "next_action_hint" in payload
    assert payload["next_action_hint"] is None
    assert isinstance(payload["evidence"], dict)


def test_ct_s3_check_result_schema_failure_fields_are_strings_on_failure() -> None:
    result = CheckResult(
        check_id="CT-S3-TEST-FAIL",
        audience=constants.AUDIENCE_EXTERNAL_BROWSER,
        ok=False,
        title="schema smoke (fail)",
        failure_class="s3.config.missing_env",
        next_action_hint="Set the required environment variables.",
        evidence={"status_code": 403},
    )

    payload = asdict(result)

    assert payload["audience"] == "EXTERNAL_BROWSER"
    assert payload["failure_class"] == "s3.config.missing_env"
    assert payload["next_action_hint"] == "Set the required environment variables."
