"""Unit tests for version-bound resource reuse across credential rotation."""

import pytest

from core.utils.rotating_resource import RotatingResource, RotatingResourceError


def test_rotating_resource_reuses_when_version_unchanged():
    """Same credential version reuses the pooled resource."""

    state = {"password": "pw1", "version": "v1"}
    created: list[dict] = []

    def credentials_provider():
        return {"password": state["password"]}, state["version"]

    def factory(credentials):
        created.append(credentials)
        return {"session_for": credentials["password"]}

    pool = RotatingResource(credentials_provider=credentials_provider, factory=factory)

    a = pool.get()
    b = pool.get()
    assert a is b
    assert created == [{"password": "pw1"}]


def test_rotating_resource_creates_new_resource_after_rotation():
    """A new version yields a new resource and avoids stale reuse."""

    state = {"password": "pw1", "version": "v1"}
    created: list[dict] = []

    def credentials_provider():
        return {"password": state["password"]}, state["version"]

    def factory(credentials):
        created.append(credentials)
        return {"session_for": credentials["password"]}

    pool = RotatingResource(credentials_provider=credentials_provider, factory=factory)

    first = pool.get()
    state["password"] = "pw2"
    state["version"] = "v2"
    second = pool.get()

    assert first is not second
    assert created == [{"password": "pw1"}, {"password": "pw2"}]


def test_rotating_resource_factory_failure_is_no_leak():
    """Factory failures are wrapped without leaking sensitive credentials."""

    state = {"password": "pw1", "version": "v1"}

    def credentials_provider():
        return {"password": state["password"]}, state["version"]

    def factory(credentials):
        raise ValueError(f"bad password={credentials['password']}")

    pool = RotatingResource(credentials_provider=credentials_provider, factory=factory)

    with pytest.raises(RotatingResourceError) as excinfo:
        pool.get()

    err = excinfo.value
    assert err.failure_class == "mount.session.init_failed"
    assert "pw1" not in str(err)

