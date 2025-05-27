"""Test the LockService."""

import pytest

from core import factories
from wopi.services.lock import LockService

pytestmark = pytest.mark.django_db


def test_lock_service():
    """Test the lock service."""
    item = factories.ItemFactory()

    lock_service = LockService(item)
    assert lock_service.is_locked() is False

    lock_service.lock("1234567890")
    assert lock_service.is_locked()
    assert lock_service.get_lock() == "1234567890"
    assert lock_service.is_lock_valid("1234567890") is True
    assert lock_service.is_lock_valid("1234567891") is False

    lock_service.refresh_lock()

    lock_service.unlock()
    assert lock_service.is_locked() is False
    assert lock_service.get_lock() is None
