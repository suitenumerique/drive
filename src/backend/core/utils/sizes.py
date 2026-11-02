"""Format byte sizes like the frontend formatSize helper."""

SIZE_UNITS = ("B", "KB", "MB", "GB", "TB", "PB")


def format_size(size):
    """Format a size in bytes with decimal units, like the frontend formatSize."""
    converted = size
    unit_index = 0
    while converted >= 1000 and unit_index < len(SIZE_UNITS) - 1:
        converted /= 1000
        unit_index += 1

    if converted < 10:
        number = f"{converted:.2f}"
    elif converted < 100:
        number = f"{converted:.1f}"
    else:
        # Math.round rounds halves up where Python round() rounds them to even
        number = str(int(converted + 0.5))
    return f"{number} {SIZE_UNITS[unit_index]}"
