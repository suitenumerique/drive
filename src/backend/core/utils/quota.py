"""Format the quota returned by the entitlements backends."""

from django.utils.translation import gettext_lazy as _

from core.utils.sizes import format_size

# Key in the get_quota output, label, formatter of the value
QUOTA_FIELDS = (
    ("state", _("State"), str),
    ("reason", _("Reason"), str),
    ("error", _("Error"), str),
    ("usage", _("Usage"), format_size),
    ("limit", _("Limit"), format_size),
)


def quota_to_str(quota):
    """Return every field of a get_quota output as labelled lines."""
    if not quota:
        return str(_("No quota"))

    lines = [
        f"{label}: {formatter(quota[key])}"
        for key, label, formatter in QUOTA_FIELDS
        if key in quota
    ]
    if "usage" in quota and quota.get("limit"):
        lines.append(f"{_('Used')}: {quota['usage'] * 100 / quota['limit']:.0f} %")
    return "\n".join(lines)
