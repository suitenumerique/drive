"""Forced-conversion policy for WOPI legacy formats."""

from django.conf import settings


def _normalize(value):
    return value.lower() if isinstance(value, str) else value


def target_extension_for(source_extension):
    """Return the converted extension for a legacy source extension.

    Item.extension preserves filename case (REPORT.DOC -> "DOC"), so the
    lookup must be case-insensitive.
    """
    if not source_extension:
        return None

    return settings.WOPI_LEGACY_CONVERSION_TARGETS.get(source_extension.lower())


def is_forced_conversion(item, client_options):
    """Return True when the active WOPI client forces a server-side conversion.

    The decision is product policy, not discovery-derived: a client is allowed
    to advertise an "edit" action for a legacy format and still require the
    Drive backend to convert it first.
    """
    if not client_options:
        return False

    extension = _normalize(item.extension)
    forced_extensions = {_normalize(e) for e in client_options.get("ForceConvertExtensions") or []}
    if extension and extension in forced_extensions:
        return True

    mimetype = _normalize(item.mimetype)
    forced_mimetypes = {_normalize(m) for m in client_options.get("ForceConvertMimetypes") or []}
    if mimetype and mimetype in forced_mimetypes:
        return True

    return False
