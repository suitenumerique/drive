"""Module to manage item title uniqueness."""

import re
from os.path import splitext


def _extract_number_from_title(title):
    """Extract the numeric suffix from a title with the given base."""
    base, _ = splitext(title)
    try:
        return int(base.rsplit("_", 1)[-1])
    except (ValueError, IndexError):
        return 0


def _get_next_available_number(queryset, base_title, ext):
    """Get the next available number for a duplicate title."""
    escaped_base = re.escape(base_title)
    escaped_ext = re.escape(ext) if ext else ""
    title_regex = rf"^{escaped_base}_\d+{escaped_ext}$"

    # Get all numbered versions (no ordering needed since we iterate through all)
    # Ordering is not made using order_by nor python list sorting function because
    # the result is not what we expect. For example file_1.txt, file_2.txt, file_10.txt
    # will be sorted as file_1.txt, file_10.txt, file_2.txt.
    existing_titles = queryset.filter_non_deleted(title__regex=title_regex).values_list(
        "title", flat=True
    )

    if not existing_titles:
        return "01"

    # Extract numbers and find the maximum
    max_number = max(_extract_number_from_title(title) for title in existing_titles)

    return f"{max_number + 1}".zfill(2)


def manage_unique_title(queryset, title):
    """Manage the unique title in the same path."""
    # Return original title if it doesn't exist
    if not queryset.filter_non_deleted(title=title).exists():
        return title

    # Handle duplicate by adding numeric suffix
    base_title, ext = splitext(title)
    next_number = _get_next_available_number(queryset, base_title, ext)
    return f"{base_title}_{next_number}{ext}"
