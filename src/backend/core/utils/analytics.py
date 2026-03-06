"""
PostHog utilities
"""

from django.conf import settings

import posthog


def posthog_capture(event_name, user, properties, **kwargs):
    """Capture an event with PostHog."""
    if settings.POSTHOG_KEY:
        properties = properties.copy()
        item = kwargs.get("item")
        if item:
            properties["item_id"] = item.id
            properties["item_title"] = item.title
            properties["item_size"] = item.size
            properties["item_mimetype"] = item.mimetype
            properties["item_type"] = item.type
        posthog.capture(event_name, distinct_id=user.email if user else None, properties=properties)
