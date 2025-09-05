"""E2E utils."""

from core import factories, models


def get_or_create_e2e_user(email):
    """Get or create an E2E user."""
    user = models.User.objects.filter(email=email).first()
    if not user:
        user = factories.UserFactory(email=email, sub=None, language="en-us")
    return user
