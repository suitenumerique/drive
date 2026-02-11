"""Refs-only secret resolution helpers (deterministic, no-leak)."""

from __future__ import annotations

import os

from configurations import values


class SecretRefValue(values.Value):
    """
    Interpret secrets from environment variables using *references only*.

    Resolution order:
    - `{NAME}_FILE` (read file contents), else
    - `{NAME}_ENV` (name of env var holding the secret), else
    - default.

    Direct secret material in `{NAME}` is rejected to prevent accidental leaks
    into manifests/configmaps.
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

        if (os.environ.get(full_environ_name) or "").strip():
            raise ValueError(
                f"Invalid {full_environ_name} configuration. "
                "failure_class=config.secret.direct_value_forbidden "
                f"next_action_hint=Do not set {full_environ_name!r} directly; "
                f"use {full_environ_name_file!r} or {full_environ_name_env!r} instead."
            )

        file_ref = (os.environ.get(full_environ_name_file) or "").strip()
        if file_ref:
            if not os.path.exists(file_ref):
                raise ValueError(
                    f"Invalid {full_environ_name} configuration. "
                    "failure_class=config.secret.file_missing "
                    f"next_action_hint=Ensure {full_environ_name_file!r} points to an existing file."
                )
            try:
                with open(file_ref, encoding="utf-8") as file:
                    value = self.to_python(file.read().removesuffix("\n"))
            except (OSError, PermissionError) as err:
                raise ValueError(
                    f"Invalid {full_environ_name} configuration. "
                    "failure_class=config.secret.file_unreadable "
                    f"next_action_hint=Ensure {full_environ_name_file!r} is readable by the process."
                ) from err
            self.value = value
            return value

        env_ref = (os.environ.get(full_environ_name_env) or "").strip()
        if env_ref:
            ref_value = (os.environ.get(env_ref) or "").strip()
            if not ref_value:
                raise ValueError(
                    f"Invalid {full_environ_name} configuration. "
                    "failure_class=config.secret.env_ref_missing "
                    f"next_action_hint=Ensure {full_environ_name_env!r} references a set env var."
                )
            value = self.to_python(ref_value)
            self.value = value
            return value

        if self.environ_required:
            raise ValueError(
                f"Value {name!r} is required to be set as the "
                f"environment variable {full_environ_name_file!r} or {full_environ_name_env!r}"
            )

        self.value = value
        return value
