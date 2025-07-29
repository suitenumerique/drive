"""Module to manage item title uniqueness."""

from os.path import splitext

from django.db import models


def _get_non_deleted_filter():
    """Return a Q object for filtering non-deleted items."""
    return models.Q(
        models.Q(deleted_at__isnull=True) | models.Q(ancestors_deleted_at__isnull=True)
    )


def _is_item_title_existing(queryset, title):
    """Check if the title is unique in the same path."""
    return queryset.filter(title=title).filter(_get_non_deleted_filter()).exists()


def _extract_number_from_title(title):
    """Extract the numeric suffix from a title with the given base."""
    base, _ = splitext(title)
    try:
        return int(base.split("_")[-1])
    except (ValueError, IndexError):
        return 0


def _build_numbered_title_regex(base_title, ext):
    """Build a regex pattern to match numbered versions of a title."""
    escaped_base = base_title.replace("(", r"\(").replace(")", r"\)")
    pattern = rf"^{escaped_base}_\d+"
    if ext:
        escaped_ext = ext.replace(".", r"\.")
        pattern += rf"{escaped_ext}$"
    else:
        pattern += r"$"
    return pattern


def _get_next_available_number(queryset, base_title, ext):
    """Get the next available number for a duplicate title."""
    title_regex = _build_numbered_title_regex(base_title, ext)

    # Get all numbered versions (no ordering needed since we iterate through all)
    # Ordering is not made using order_by nor python list sorting function because
    # the result is not what we expect. For example file_1.txt, file_2.txt, file_10.txt
    # will be sorted as file_1.txt, file_10.txt, file_2.txt.
    existing_titles = (
        queryset.filter(title__regex=title_regex)
        .filter(_get_non_deleted_filter())
        .values_list("title", flat=True)
    )

    if not existing_titles:
        return 1

    # Extract numbers and find the maximum
    max_number = 0
    for title in existing_titles:
        number = _extract_number_from_title(title)
        max_number = max(max_number, number)

    return max_number + 1


def manage_unique_title(queryset, title):
    """Manage the unique title in the same path."""
    # Return original title if it doesn't exist
    if not _is_item_title_existing(queryset, title):
        return title

    # Handle duplicate by adding numeric suffix
    base_title, ext = splitext(title)
    next_number = _get_next_available_number(queryset, base_title, ext)
    return f"{base_title}_{next_number}{ext}"
