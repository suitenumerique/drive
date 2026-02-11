"""Refs-only secret resolution helpers (deterministic, no-leak)."""

from __future__ import annotations

import os

from configurations import values


class SecretRefValue(values.Value):
    """
    Interpret secrets from environment variables using *references only*.

    The resolved value is, in order of priority:
    - the contents of the file referenced by `{NAME}_FILE` (if set), else
    - the contents of the env var named by `{NAME}_ENV` (if set), else
    - the default value.

    Direct secret material in `{NAME}` is rejected to prevent accidental leaks
    into manifests/configmaps. This keeps the configuration refs-only.
    """

    file_suffix = "FILE"
    env_suffix = "ENV"

    def setup(self, name):
        value = self.default

        if not self.environ:
            self.value = value
            return value

        full_environ_name = self.full_environ_name(name)
        full_environ_name_file = f"{full_environ_name}_{self.file_suffix}"
        full_environ_name_env = f"{full_environ_name}_{self.env_suffix}"

        if full_environ_name in os.environ:
            raise ValueError(
                f"Invalid {full_environ_name} configuration. "
                "failure_class=config.secret.direct_value_forbidden "
                f"next_action_hint=Do not set {full_environ_name!r} directly; "
                f"use {full_environ_name_file!r} or {full_environ_name_env!r} instead."
            )

        if (
            full_environ_name_file in os.environ
            and os.environ[full_environ_name_file].strip()
        ):
            filename = os.environ[full_environ_name_file].strip()
            if not os.path.exists(filename):
                raise ValueError(
                    f"Invalid {full_environ_name} configuration. "
                    "failure_class=config.secret.file_missing "
                    f"next_action_hint=Ensure {full_environ_name_file!r} points to an existing file."
                )
            try:
                with open(filename, encoding="utf-8") as file:
                    value = self.to_python(file.read().removesuffix("\n"))
            except (OSError, PermissionError) as err:
                raise ValueError(
                    f"Invalid {full_environ_name} configuration. "
                    "failure_class=config.secret.file_unreadable "
                    f"next_action_hint=Ensure {full_environ_name_file!r} is readable by the process."
                ) from err

        elif (
            full_environ_name_env in os.environ
            and os.environ[full_environ_name_env].strip()
        ):
            ref_name = os.environ[full_environ_name_env].strip()
            ref_value = os.environ.get(ref_name, "").strip()
            if not ref_value:
                raise ValueError(
                    f"Invalid {full_environ_name} configuration. "
                    "failure_class=config.secret.env_ref_missing "
                    f"next_action_hint=Ensure {full_environ_name_env!r} references a set env var."
                )
            value = self.to_python(ref_value)

        elif self.environ_required:
            raise ValueError(
                f"Value {name!r} is required to be set as the "
                f"environment variable {full_environ_name_file!r} or {full_environ_name_env!r}"
            )

        self.value = value
        return value
